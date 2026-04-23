import asyncio
import base64

import edge_tts

VOICE_MAP = {
    "zh": "zh-CN-YunxiNeural",
    "en": "en-US-GuyNeural",
}


async def synthesize(text: str, language: str = "zh") -> dict:
    voice = VOICE_MAP.get(language, VOICE_MAP["en"])
    communicate = edge_tts.Communicate(text, voice=voice)

    audio = b""
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio += chunk["data"]

    if not audio:
        raise RuntimeError("Edge TTS returned no audio")

    return {
        "audio": base64.b64encode(audio).decode(),
        "format": "mp3",
    }
