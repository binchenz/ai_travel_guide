import asyncio
import gzip
import json
import os
import uuid

import websockets

WS_URL = "wss://openspeech.bytedance.com/api/v3/sauc/bigmodel"
APP_KEY = "1724131082"
RESOURCE_ID = "volc.bigasr.sauc.duration"

# Binary protocol headers
_HDR_CONFIG = bytes(b"\x11\x10\x11\x00")  # full request, JSON, gzip
_HDR_AUDIO  = bytes(b"\x11\x20\x10\x00")  # audio chunk, no compress
_HDR_LAST   = bytes(b"\x11\x22\x10\x00")  # last audio chunk, no compress


def _pack_json(payload: dict) -> bytes:
    data = gzip.compress(json.dumps(payload).encode())
    return _HDR_CONFIG + len(data).to_bytes(4, "big") + data


def _pack_audio(pcm: bytes, is_last: bool) -> bytes:
    hdr = _HDR_LAST if is_last else _HDR_AUDIO
    return hdr + len(pcm).to_bytes(4, "big") + pcm


def _unpack(data: bytes):
    # Header: 4 bytes, sequence: 4 bytes, payload_size: 4 bytes, payload
    if len(data) < 12:
        return None
    payload_size = int.from_bytes(data[8:12], "big")
    payload = data[12 : 12 + payload_size]
    try:
        return json.loads(payload.decode("utf-8"))
    except Exception:
        return None


async def recognize(audio_base64: str, language: str = "zh") -> dict:
    import base64

    access_token = os.getenv("VOLCANO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("VOLCANO_ACCESS_TOKEN not set")

    pcm_bytes = base64.b64decode(audio_base64)
    # Strip WAV header if present (RIFF magic)
    if pcm_bytes[:4] == b"RIFF":
        pcm_bytes = pcm_bytes[44:]

    connect_id = str(uuid.uuid4())
    ws_headers = {
        "X-Api-App-Key": APP_KEY,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Connect-Id": connect_id,
    }

    final_text = ""

    async with websockets.connect(WS_URL, additional_headers=ws_headers) as ws:
        # 1. Send config
        config = {
            "user": {"uid": APP_KEY},
            "audio": {"format": "pcm", "sample_rate": 16000, "bits": 16, "channel": 1, "codec": "raw"},
            "request": {"model_name": "bigmodel", "enable_punc": True},
        }
        await ws.send(_pack_json(config))
        await asyncio.wait_for(ws.recv(), timeout=5)  # ack

        # 2. Send audio in 100ms chunks
        chunk_size = 3200  # 16000 Hz * 2 bytes * 0.1s
        chunks = [pcm_bytes[i : i + chunk_size] for i in range(0, len(pcm_bytes), chunk_size)]
        if not chunks:
            chunks = [b"\x00" * chunk_size]

        for i, chunk in enumerate(chunks):
            await ws.send(_pack_audio(chunk, is_last=(i == len(chunks) - 1)))

        # 3. Collect results until connection closes
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
                result = _unpack(msg)
                if result and "result" in result:
                    text = result["result"].get("text", "")
                    if text:
                        final_text = text
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                break

    return {"text": final_text, "language": language}
