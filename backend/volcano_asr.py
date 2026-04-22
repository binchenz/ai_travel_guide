import httpx
import uuid
import os

ASR_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash"
APP_KEY = "1724131082"

async def recognize(audio_base64: str, language: str = "zh") -> dict:
    access_token = os.getenv("VOLCANO_ACCESS_TOKEN")
    if not access_token:
        raise RuntimeError("VOLCANO_ACCESS_TOKEN not set")

    headers = {
        "X-Api-Key": APP_KEY,
        "X-Api-Access-Key": access_token,
        "X-Api-Resource-Id": "volc.bigasr.auc_turbo",
        "X-Api-Request-Id": str(uuid.uuid4()),
        "X-Api-Sequence": "-1",
        "Content-Type": "application/json",
    }

    payload = {
        "user": {"uid": APP_KEY},
        "audio": {"data": audio_base64},
        "request": {"model_name": "bigmodel"},
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(ASR_URL, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    if data.get("code", 0) != 0:
        raise RuntimeError(f"ASR API error: {data.get('message', data)}")

    if "result" in data and "text" in data["result"]:
        return {"text": data["result"]["text"], "language": language}

    return {"text": "", "language": language}
