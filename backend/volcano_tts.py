"""TTS façade used by the /tts endpoint.

Backends
--------
- ``edge`` (default): edge-tts over HTTPS. Free, stable, fast for short
  museum narration. This is the production default because extensive
  benchmarking shows the Volcano V3 bidirection WebSocket path in this
  codebase is not reliably functional — it was silently falling back to
  edge-tts on every request, paying a 2-3s penalty per call.
- ``volcano``: Volcano Engine V3 bidirection WebSocket. Kept for future
  work but opt-in; the real-world Resource ID / event-shape mapping
  still needs validation against the live service.
- ``auto``: try Volcano first, fall back to Edge on any failure. Useful
  once Volcano is fully debugged; not recommended today because each
  Volcano failure adds 2-3s before fallback.

Tuning
------
- ``VOICE_TTS_BACKEND``       - edge (default) | volcano | auto
- ``VOICE_TTS_CACHE_SIZE``    - LRU entries, default 256
- ``VOICE_TTS_MAX_CONCURRENCY`` - upper bound on simultaneous external
  calls, default 8. Prevents a burst of requests from exhausting the
  fallback provider's free tier.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import time
import uuid
from collections import OrderedDict
from typing import Tuple

from voice_metrics import metrics

logger = logging.getLogger("voice.tts")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BACKEND = os.getenv("VOICE_TTS_BACKEND", "edge").lower()
CACHE_SIZE = int(os.getenv("VOICE_TTS_CACHE_SIZE", "256"))
MAX_CONCURRENCY = int(os.getenv("VOICE_TTS_MAX_CONCURRENCY", "8"))
TEXT_LIMIT = 2000  # Hard cap to avoid huge synthesis jobs blocking the pool

# Volcano V3 bidirectional TTS
_VOLCANO_WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
_VOLCANO_APP_KEY = os.getenv("VOLCANO_APP_KEY", "1724131082")
_VOLCANO_RESOURCE_ID = os.getenv("VOLCANO_TTS_RESOURCE_ID", "seed-tts-2.0")
_VOLCANO_VOICE_MAP = {
    "zh": "zh_female_vv_uranus_bigtts",
    "en": "en_female_vv_stella_bigtts",
}

# Edge TTS voices
_EDGE_VOICE_MAP = {
    "zh": "zh-CN-YunxiNeural",
    "en": "en-US-GuyNeural",
}

_semaphore = asyncio.Semaphore(MAX_CONCURRENCY)
_cache: "OrderedDict[Tuple[str, str, str], dict]" = OrderedDict()
_cache_lock = asyncio.Lock()


def _cache_key(text: str, language: str, backend: str) -> Tuple[str, str, str]:
    return (backend, language, text)


async def _cache_get(key):
    async with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key]
    return None


async def _cache_put(key, value):
    async with _cache_lock:
        _cache[key] = value
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)


# ---------------------------------------------------------------------------
# Edge TTS (default backend)
# ---------------------------------------------------------------------------
async def _edge_synthesize(text: str, language: str) -> dict:
    import edge_tts  # local import so the module still loads if edge-tts is absent

    voice = _EDGE_VOICE_MAP.get(language, _EDGE_VOICE_MAP["zh"])
    comm = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in comm.stream():
        if chunk.get("type") == "audio":
            audio.extend(chunk["data"])
    if not audio:
        raise RuntimeError("edge-tts returned no audio")
    return {
        "audio": base64.b64encode(bytes(audio)).decode(),
        "format": "mp3",
        "backend": "edge",
    }


# ---------------------------------------------------------------------------
# Volcano V3 bidirectional TTS (opt-in)
# ---------------------------------------------------------------------------
async def _volcano_synthesize(text: str, language: str) -> dict:
    access_token = os.getenv("VOLCANO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("VOLCANO_ACCESS_TOKEN not set")

    import websockets

    voice = _VOLCANO_VOICE_MAP.get(language, _VOLCANO_VOICE_MAP["zh"])
    connect_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    headers = {
        "X-Api-App-Key": _VOLCANO_APP_KEY,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": _VOLCANO_RESOURCE_ID,
        "X-Api-Connect-Id": connect_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }

    audio_chunks: list[bytes] = []

    async def _expect_event(ws, expected: str, timeout: float = 5.0) -> dict:
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
            if isinstance(raw, (bytes, bytearray)):
                # Unexpected binary frame before the control event we asked
                # for — buffer it as audio and keep reading.
                audio_chunks.append(bytes(raw))
                continue
            try:
                data = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"non-JSON control frame: {exc}") from exc
            if data.get("event") == expected:
                return data
            if data.get("event", "").lower().endswith("failed"):
                raise RuntimeError(f"volcano error: {data}")

    try:
        async with websockets.connect(
            _VOLCANO_WS_URL, additional_headers=headers, open_timeout=5.0
        ) as ws:
            await ws.send(json.dumps({
                "event": "StartConnection",
                "header": {"connect_id": connect_id},
            }))
            await _expect_event(ws, "ConnectionStarted")

            await ws.send(json.dumps({
                "event": "StartSession",
                "header": {"connect_id": connect_id, "session_id": session_id},
                "payload": {
                    "voice": voice,
                    "audio_config": {"format": "mp3", "sample_rate": 24000},
                },
            }))
            await _expect_event(ws, "SessionStarted")

            await ws.send(json.dumps({
                "event": "TaskRequest",
                "header": {"connect_id": connect_id, "session_id": session_id},
                "payload": {"text": text, "operation": "submit"},
            }))

            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=10.0)
                if isinstance(msg, (bytes, bytearray)):
                    audio_chunks.append(bytes(msg))
                    continue
                try:
                    data = json.loads(msg)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                event = data.get("event", "")
                if event in ("TaskFinished", "SessionFinished"):
                    break
                if event.lower().endswith("failed"):
                    raise RuntimeError(f"volcano TTS failed: {data}")
                if event == "AudioData":
                    b64 = (data.get("payload") or {}).get("audio", "")
                    if b64:
                        audio_chunks.append(base64.b64decode(b64))
    except (asyncio.TimeoutError, Exception) as exc:
        raise RuntimeError(f"volcano TTS: {exc}") from exc

    if not audio_chunks:
        raise RuntimeError("volcano TTS returned no audio")

    return {
        "audio": base64.b64encode(b"".join(audio_chunks)).decode(),
        "format": "mp3",
        "backend": "volcano",
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
async def synthesize(text: str, language: str = "zh") -> dict:
    """Synthesize ``text`` in ``language`` and return {audio, format, backend}.

    Raises RuntimeError if all configured backends fail. Callers should
    map that to an HTTP 5xx; the frontend already has a browser-speech
    fallback of its own.
    """
    if not text or not text.strip():
        raise ValueError("text is empty")
    if len(text) > TEXT_LIMIT:
        text = text[:TEXT_LIMIT]

    language = language if language in ("zh", "en") else "zh"

    # Fast path: LRU cache.
    primary = "edge" if BACKEND == "edge" else "volcano" if BACKEND == "volcano" else "auto"
    key = _cache_key(text, language, primary)
    cached = await _cache_get(key)
    if cached is not None:
        metrics.record_cache(hit=True)
        return cached
    metrics.record_cache(hit=False)

    async with _semaphore:
        start = time.perf_counter()
        err: str | None = None
        result: dict | None = None

        try:
            if BACKEND == "edge":
                result = await _edge_synthesize(text, language)
            elif BACKEND == "volcano":
                result = await _volcano_synthesize(text, language)
            else:  # "auto"
                try:
                    result = await _volcano_synthesize(text, language)
                except Exception as exc:
                    logger.warning("volcano TTS failed, falling back to edge: %s", exc)
                    metrics.record("volcano", time.perf_counter() - start, str(exc))
                    start = time.perf_counter()
                    result = await _edge_synthesize(text, language)
        except Exception as exc:
            err = str(exc)
            logger.exception("TTS synthesis failed")
            raise
        finally:
            latency = time.perf_counter() - start
            backend_used = result.get("backend") if isinstance(result, dict) else BACKEND
            metrics.record(f"tts.{backend_used}", latency, err)

    await _cache_put(key, result)
    return result


def clear_cache() -> None:
    """Mostly for tests."""
    _cache.clear()
