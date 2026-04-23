# Volcano Engine TTS/ASR Integration Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace mock TTS and ASR endpoints with real Volcano Engine V3 API integrations.

**Architecture:** ASR uses a simple HTTP POST to the V3 flash recognition endpoint. TTS uses a V3 bidirectional WebSocket connection with an event-based protocol. Both modules are standalone files imported by main.py.

**Tech Stack:** Python 3, FastAPI, websockets, httpx, asyncio

---

## File Structure

| File | Role |
|------|------|
| `backend/volcano_asr.py` | New — HTTP client for V3 flash ASR |
| `backend/volcano_tts.py` | New — WebSocket client for V3 bidirectional TTS |
| `backend/main.py` | Modify — replace mock `/tts` and `/asr` with real calls |
| `backend/requirements.txt` | Modify — add `websockets>=12.0` |
| `backend/test_volcano_asr.py` | New — ASR integration test |
| `backend/test_volcano_tts.py` | New — TTS integration test |

---

### Task 1: Add websockets dependency

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: Add websockets to requirements.txt**

```
websockets>=12.0
```

Append this line to the end of `backend/requirements.txt`.

- [ ] **Step 2: Install dependencies**

Run: `cd backend && pip install -r requirements.txt`
Expected: Successfully installed websockets

- [ ] **Step 3: Commit**

```bash
git add backend/requirements.txt
git commit -m "chore: add websockets dependency for Volcano Engine TTS"
```

---

### Task 2: Implement ASR module (volcano_asr.py)

**Files:**
- Create: `backend/volcano_asr.py`
- Create: `backend/test_volcano_asr.py`

- [ ] **Step 1: Write the ASR integration test**

Create `backend/test_volcano_asr.py`:

```python
"""
Integration test for Volcano Engine ASR.
Requires VOLCANO_ACCESS_TOKEN env var to be set.
Run: python test_volcano_asr.py
"""
import asyncio
import base64
import os
import sys

async def test_asr():
    from volcano_asr import recognize

    # Generate a short silent WAV file (valid audio, should return empty or short text)
    # 44-byte WAV header + 8000 bytes of silence = 0.5s of 16kHz mono PCM
    import struct
    sample_rate = 16000
    num_samples = sample_rate // 2  # 0.5 seconds
    data_size = num_samples * 2  # 16-bit = 2 bytes per sample
    wav_header = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', 36 + data_size, b'WAVE',
        b'fmt ', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b'data', data_size
    )
    wav_bytes = wav_header + b'\x00' * data_size
    audio_b64 = base64.b64encode(wav_bytes).decode()

    print("Testing ASR with silent WAV audio...")
    try:
        result = await recognize(audio_b64, "zh")
        print(f"SUCCESS: Got result: {result}")
        assert "text" in result, "Result must contain 'text' key"
        print("PASS: ASR module works correctly")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        print("SKIP: VOLCANO_ACCESS_TOKEN not set")
        sys.exit(0)
    asyncio.run(test_asr())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python test_volcano_asr.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'volcano_asr'`

- [ ] **Step 3: Implement volcano_asr.py**

Create `backend/volcano_asr.py`:

```python
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

    if "result" in data and "text" in data["result"]:
        return {"text": data["result"]["text"], "language": language}

    return {"text": "", "language": language}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python test_volcano_asr.py`
Expected: PASS (or SKIP if no token set)

- [ ] **Step 5: Commit**

```bash
git add backend/volcano_asr.py backend/test_volcano_asr.py
git commit -m "feat: implement Volcano Engine ASR flash HTTP client"
```

---

### Task 3: Implement TTS module (volcano_tts.py)

**Files:**
- Create: `backend/volcano_tts.py`
- Create: `backend/test_volcano_tts.py`

- [ ] **Step 1: Write the TTS integration test**

Create `backend/test_volcano_tts.py`:

```python
"""
Integration test for Volcano Engine TTS.
Requires VOLCANO_ACCESS_TOKEN env var to be set.
Run: python test_volcano_tts.py
"""
import asyncio
import base64
import os
import sys

async def test_tts():
    from volcano_tts import synthesize

    print("Testing TTS with Chinese text...")
    try:
        result = await synthesize("你好世界", "zh")
        print(f"SUCCESS: Got result with {len(result['audio'])} chars of base64 audio")
        assert "audio" in result, "Result must contain 'audio' key"
        assert len(result["audio"]) > 100, "Audio data should be substantial"
        # Verify it's valid base64
        audio_bytes = base64.b64decode(result["audio"])
        assert len(audio_bytes) > 0, "Decoded audio should not be empty"
        print(f"PASS: TTS returned {len(audio_bytes)} bytes of audio")
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    print("\nTesting TTS with English text...")
    try:
        result = await synthesize("Hello world", "en")
        assert "audio" in result
        audio_bytes = base64.b64decode(result["audio"])
        assert len(audio_bytes) > 0
        print(f"PASS: English TTS returned {len(audio_bytes)} bytes of audio")
    except Exception as e:
        print(f"FAIL: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        print("SKIP: VOLCANO_ACCESS_TOKEN not set")
        sys.exit(0)
    asyncio.run(test_tts())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python test_volcano_tts.py`
Expected: FAIL with `ModuleNotFoundError: No module named 'volcano_tts'`

- [ ] **Step 3: Implement volcano_tts.py**

Create `backend/volcano_tts.py`:

```python
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
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            if isinstance(msg, bytes):
                audio_chunks.append(msg)
                continue
            data = json.loads(msg)
            event = data.get("event", "")
            if event in ("TaskFinished", "SessionFinished", "ConnectionFinished"):
                break
            if event == "TaskFailed":
                raise RuntimeError(f"TTS task failed: {data}")
            # AudioData events may carry base64 audio in payload
            if event == "AudioData" and "payload" in data:
                audio_b64 = data["payload"].get("audio", "")
                if audio_b64:
                    audio_chunks.append(base64.b64decode(audio_b64))

        # 5. FinishSession
        await ws.send(json.dumps({
            "event": "FinishSession",
            "header": {
                "connect_id": connect_id,
                "session_id": session_id,
            },
        }))

        # 6. FinishConnection
        await ws.send(json.dumps({
            "event": "FinishConnection",
            "header": {"connect_id": connect_id},
        }))

    if not audio_chunks:
        raise RuntimeError("No audio data received from TTS service")

    audio_bytes = b"".join(audio_chunks)
    return {
        "audio": base64.b64encode(audio_bytes).decode(),
        "format": "mp3",
    }
```

**Important:** The V3 bidirectional WebSocket protocol event names and payload structure may differ from what's documented. If the test fails with unexpected responses, read the actual server response and adjust the event names/payload accordingly. Common variations:
- Event names might use snake_case (`start_connection`) instead of PascalCase (`StartConnection`)
- Audio might arrive as binary WebSocket frames or as base64 in JSON payloads
- The server might require different payload field names (e.g., `speaker` instead of `voice`)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python test_volcano_tts.py`
Expected: PASS with audio bytes > 0

If the test fails with a protocol error, read the server's actual response and adjust the event format in `volcano_tts.py`. The implementation above is based on the documented V3 protocol pattern — the server may expect slightly different field names or event sequences.

- [ ] **Step 5: Commit**

```bash
git add backend/volcano_tts.py backend/test_volcano_tts.py
git commit -m "feat: implement Volcano Engine TTS V3 WebSocket client"
```

---

### Task 4: Wire up main.py endpoints

**Files:**
- Modify: `backend/main.py:439-555`

- [ ] **Step 1: Replace the `/tts` endpoint**

Replace lines 439-495 of `backend/main.py` with:

```python
@app.post("/tts")
async def text_to_speech(request: Request):
    """Convert text to speech using Volcano Engine TTS V3"""
    from volcano_tts import synthesize

    body = await request.json()
    text = body.get("text")
    language = body.get("language", "zh")

    if not text:
        raise HTTPException(status_code=400, detail="Text parameter is required")

    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        raise HTTPException(status_code=500, detail="Volcano Engine credentials not configured")

    try:
        result = await synthesize(text, language)
        return result
    except Exception as e:
        print(f"TTS error: {e}")
        raise HTTPException(status_code=500, detail=f"TTS error: {str(e)}")
```

- [ ] **Step 2: Replace the `/asr` endpoint**

Replace lines 498-555 of `backend/main.py` with:

```python
@app.post("/asr")
async def speech_to_text(request: Request):
    """Convert speech to text using Volcano Engine ASR V3"""
    from volcano_asr import recognize

    body = await request.json()
    audio_data = body.get("audio")
    language = body.get("language", "zh")

    if not audio_data:
        raise HTTPException(status_code=400, detail="Audio data is required")

    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        raise HTTPException(status_code=500, detail="Volcano Engine credentials not configured")

    try:
        result = await recognize(audio_data, language)
        return result
    except Exception as e:
        print(f"ASR error: {e}")
        raise HTTPException(status_code=500, detail=f"ASR error: {str(e)}")
```

- [ ] **Step 3: Clean up unused imports in the replaced sections**

The old `/tts` and `/asr` endpoints had inline imports (`import httpx`, `import asyncio`, etc.). These are no longer needed in the endpoint functions since the logic moved to separate modules. Verify no other code in main.py depends on these inline imports (they don't — they were scoped inside the functions).

- [ ] **Step 4: Test the server starts without errors**

Run: `cd backend && python -c "from main import app; print('OK')"` 
Expected: `OK` (no import errors)

- [ ] **Step 5: Commit**

```bash
git add backend/main.py
git commit -m "feat: wire up real Volcano Engine TTS/ASR in endpoints"
```

---

### Task 5: End-to-end manual test

- [ ] **Step 1: Start the backend**

Tell the user to run: `cd backend && python main.py`

- [ ] **Step 2: Test TTS endpoint directly**

Run:
```bash
curl -X POST http://127.0.0.1:8080/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "你好，欢迎来到上海博物馆", "language": "zh"}'
```

Expected: JSON response with `"audio"` field containing a long base64 string and `"format": "mp3"`.

- [ ] **Step 3: Test ASR endpoint directly**

Run:
```bash
curl -X POST http://127.0.0.1:8080/asr \
  -H "Content-Type: application/json" \
  -d '{"audio": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=", "language": "zh"}'
```

Expected: JSON response with `"text"` field (may be empty for silent audio, but should not error).

- [ ] **Step 4: Test with frontend**

Tell the user to start the frontend (`cd frontend && npm run dev`) and:
1. Select an exhibit
2. Click the speaker icon on an assistant message → should hear real Volcano Engine audio
3. Click the microphone button, speak, and verify the text appears in the input field

- [ ] **Step 5: Commit any fixes**

If any adjustments were needed during testing, commit them:
```bash
git add -A
git commit -m "fix: adjust TTS/ASR integration based on testing"
```
