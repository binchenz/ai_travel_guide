import websockets
import asyncio
import json
import uuid
import base64
import os

WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
APP_KEY = "1724131082"
RESOURCE_ID = "volc.tts_bidirection.bigtts"

VOICE_MAP = {
    "zh": "zh_male_M392_conversation_wvae_bigtts",
    "en": "en_male_M394_conversation_wvae_bigtts",
}

async def synthesize(text: str, language: str = "zh") -> dict:
    access_token = os.getenv("VOLCANO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("VOLCANO_ACCESS_TOKEN not set")

    connect_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    voice = VOICE_MAP.get(language, VOICE_MAP["en"])

    headers = {
        "X-Api-App-Key": APP_KEY,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": RESOURCE_ID,
        "X-Api-Connect-Id": connect_id,
    }

    audio_chunks = []

    async with websockets.connect(WS_URL, additional_headers=headers) as ws:
        # 1. StartConnection
        await ws.send(json.dumps({
            "event": "StartConnection",
            "header": {"connect_id": connect_id},
        }))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if resp.get("event") != "ConnectionStarted":
            raise RuntimeError(f"Expected ConnectionStarted, got: {resp}")

        # 2. StartSession
        await ws.send(json.dumps({
            "event": "StartSession",
            "header": {
                "connect_id": connect_id,
                "session_id": session_id,
            },
            "payload": {
                "voice": voice,
                "audio_config": {
                    "format": "mp3",
                    "sample_rate": 24000,
                },
            },
        }))
        resp = json.loads(await asyncio.wait_for(ws.recv(), timeout=5))
        if resp.get("event") != "SessionStarted":
            raise RuntimeError(f"Expected SessionStarted, got: {resp}")

        # 3. TaskRequest
        await ws.send(json.dumps({
            "event": "TaskRequest",
            "header": {
                "connect_id": connect_id,
                "session_id": session_id,
            },
            "payload": {
                "text": text,
                "operation": "submit",
            },
        }))

        # 4. Receive audio chunks until task/session finishes
        while True:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=10)
            except asyncio.TimeoutError:
                raise RuntimeError("TTS audio stream timed out")
            if isinstance(msg, bytes):
                audio_chunks.append(msg)
                continue
            data = json.loads(msg)
            event = data.get("event", "")
            if event in ("TaskFinished", "SessionFinished", "ConnectionFinished"):
                break
            if event == "TaskFailed":
                raise RuntimeError(f"TTS task failed: {data}")
            if event == "AudioData" and "payload" in data:
                audio_b64 = data["payload"].get("audio", "")
                if audio_b64:
                    audio_chunks.append(base64.b64decode(audio_b64))

        # 5. FinishSession — sent after the receive loop because the V3 bidirectional
        # API requires the client to wait for the server to signal completion
        # (TaskFinished/SessionFinished) before tearing down the session.
        try:
            await ws.send(json.dumps({
                "event": "FinishSession",
                "header": {
                    "connect_id": connect_id,
                    "session_id": session_id,
                },
            }))
        except Exception as e:
            print(f"Warning: {e}")

        # 6. FinishConnection
        try:
            await ws.send(json.dumps({
                "event": "FinishConnection",
                "header": {"connect_id": connect_id},
            }))
        except Exception as e:
            print(f"Warning: {e}")

    if not audio_chunks:
        raise RuntimeError("No audio data received from TTS service")

    audio_bytes = b"".join(audio_chunks)
    return {
        "audio": base64.b64encode(audio_bytes).decode(),
        "format": "mp3",
    }
