"""Volcano Engine ASR (SAUC bigmodel) client.

Notes on the prior implementation we replaced:
- All exceptions were swallowed into ``{"text": ""}``, so transport
  failures looked identical to "nothing recognized". We now surface
  errors as RuntimeError so the endpoint can respond with a useful
  status, while the degenerate-audio case still yields an empty string.
- The WAV header was assumed to be exactly 44 bytes. Real WAV files
  carry extensible ``fmt`` chunks and optional ``LIST``/``bext`` chunks.
  We now locate the ``data`` chunk explicitly.
- The recv timeout was fixed at 10s regardless of clip length. Very
  short clips could (rarely) time out waiting for a server response.
  We scale it with audio duration.
"""
from __future__ import annotations

import asyncio
import base64
import gzip
import json
import logging
import os
import time
import uuid

import websockets

from voice_metrics import metrics

logger = logging.getLogger("voice.asr")

WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
APP_KEY = os.getenv("VOLCANO_APP_KEY", "1724131082")
RESOURCE_ID = os.getenv("VOLCANO_ASR_RESOURCE_ID", "volc.bigasr.sauc.duration")

# Binary framing headers from the SAUC protocol.
_HDR_CONFIG = bytes(b"\x11\x10\x11\x00")
_HDR_AUDIO = bytes(b"\x11\x20\x10\x00")
_HDR_LAST = bytes(b"\x11\x22\x10\x00")

SAMPLE_RATE = 16000
BYTES_PER_SAMPLE = 2
CHUNK_MS = 100
CHUNK_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * CHUNK_MS // 1000  # 3200
MAX_AUDIO_BYTES = SAMPLE_RATE * BYTES_PER_SAMPLE * 60  # 60 seconds


def _pack_json(payload: dict) -> bytes:
    data = gzip.compress(json.dumps(payload).encode())
    return _HDR_CONFIG + len(data).to_bytes(4, "big") + data


def _pack_audio(pcm: bytes, is_last: bool) -> bytes:
    hdr = _HDR_LAST if is_last else _HDR_AUDIO
    return hdr + len(pcm).to_bytes(4, "big") + pcm


def _unpack(data: bytes) -> dict | None:
    if len(data) < 12:
        return None
    payload_size = int.from_bytes(data[8:12], "big")
    payload = data[12 : 12 + payload_size]
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


def _strip_wav_header(audio: bytes) -> bytes:
    """Return the raw PCM body of a WAV file, or the input unchanged."""
    if len(audio) < 12 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        return audio
    # Walk chunks after the RIFF header to find "data".
    i = 12
    while i + 8 <= len(audio):
        chunk_id = audio[i : i + 4]
        chunk_size = int.from_bytes(audio[i + 4 : i + 8], "little")
        if chunk_id == b"data":
            return audio[i + 8 : i + 8 + chunk_size]
        i += 8 + chunk_size
    # Fallback: legacy 44-byte assumption.
    return audio[44:]


async def recognize(audio_base64: str, language: str = "zh") -> dict:
    access_token = os.getenv("VOLCANO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("VOLCANO_ACCESS_TOKEN not set")

    try:
        raw = base64.b64decode(audio_base64, validate=False)
    except Exception as exc:
        raise ValueError(f"invalid base64 audio: {exc}") from exc

    pcm = _strip_wav_header(raw)
    if len(pcm) == 0:
        return {"text": "", "language": language}
    if len(pcm) > MAX_AUDIO_BYTES:
        logger.warning("ASR audio truncated from %d to %d bytes", len(pcm), MAX_AUDIO_BYTES)
        pcm = pcm[:MAX_AUDIO_BYTES]

    duration_s = len(pcm) / (SAMPLE_RATE * BYTES_PER_SAMPLE)
    # Timeout scales with length: 3s floor + 2× audio duration.
    recv_timeout = max(3.0, duration_s * 2.0 + 2.0)

    connect_id = str(uuid.uuid4())
    headers = {
        "X-Api-App-Key": APP_KEY,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Connect-Id": connect_id,
        "X-Api-Request-Id": str(uuid.uuid4()),
    }

    start = time.perf_counter()
    err: str | None = None
    final_text = ""

    try:
        async with websockets.connect(
            WS_URL, additional_headers=headers, open_timeout=5.0
        ) as ws:
            config = {
                "user": {"uid": APP_KEY},
                "audio": {
                    "format": "pcm",
                    "sample_rate": SAMPLE_RATE,
                    "bits": 16,
                    "channel": 1,
                    "codec": "raw",
                },
                "request": {"model_name": "bigmodel", "enable_punc": True},
            }
            await ws.send(_pack_json(config))
            await asyncio.wait_for(ws.recv(), timeout=5.0)

            total_chunks = max(1, (len(pcm) + CHUNK_BYTES - 1) // CHUNK_BYTES)
            for i in range(total_chunks):
                chunk = pcm[i * CHUNK_BYTES : (i + 1) * CHUNK_BYTES]
                if not chunk:
                    chunk = b"\x00" * CHUNK_BYTES
                await ws.send(_pack_audio(chunk, is_last=(i == total_chunks - 1)))

            while True:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=recv_timeout)
                except asyncio.TimeoutError:
                    break
                except websockets.exceptions.ConnectionClosed:
                    break
                result = _unpack(msg)
                if not result:
                    continue
                body = result.get("result") or {}
                text = body.get("text", "")
                if text:
                    final_text = text
                if body.get("is_final") is True:
                    break
    except (asyncio.TimeoutError, websockets.exceptions.WebSocketException) as exc:
        err = f"asr transport: {exc}"
        logger.warning(err)
        raise RuntimeError(err) from exc
    except Exception as exc:  # noqa: BLE001 — deliberately surface unexpected errors
        err = f"asr unexpected: {exc}"
        logger.exception("ASR failed")
        raise RuntimeError(err) from exc
    finally:
        metrics.record("asr.volcano", time.perf_counter() - start, err)

    return {"text": final_text, "language": language}
