# Volcano Engine TTS/ASR Integration Design

## Problem

Backend `/tts` and `/asr` endpoints return mock data. TTS returns a fake base64 string; ASR returns hardcoded "这是一段测试语音". Frontend already handles both services with browser fallback — only backend needs changes.

## Approach: V3 WebSocket TTS + V3 Flash HTTP ASR

User credentials (App ID: 1724131082, Access Token via env var) use the V3 API system with `X-Api-*` headers.

## TTS: V3 Bidirectional WebSocket

### Module: `backend/volcano_tts.py`

**Connection:**
- URL: `wss://openspeech.bytedance.com/api/v3/tts/bidirection`
- Headers:
  - `X-Api-App-Key: 1724131082`
  - `X-Api-Access-Key: {VOLCANO_ACCESS_TOKEN}`
  - `X-Api-Resource-Id: volc.tts_bidirection.bigtts`
  - `X-Api-Connect-Id: {uuid}`

**Protocol sequence:**
1. Connect with auth headers
2. Send `StartConnection` event → receive `ConnectionStarted`
3. Send `StartSession` event (voice, audio format params) → receive `SessionStarted`
4. Send `TaskRequest` event (text to synthesize) → receive audio chunks
5. Collect all audio binary data until `TaskFinished` or `SessionFinished`
6. Send `FinishSession` → receive `SessionFinished`
7. Send `FinishConnection` → close

**Voice mapping:**
- Chinese: `zh_male_M392_conversation_wvae_bigtts`
- English: `en_male_M394_conversation_wvae_bigtts`

**Output:** Collected audio bytes → base64 encode → return as JSON `{"audio": "...", "format": "mp3"}`

**Error handling:** 5-second timeout on WebSocket operations. On any failure, return HTTP 500 with error detail. Frontend already falls back to browser TTS.

### Endpoint change: `/tts` in `main.py`

Replace mock implementation (lines 439-495) with call to `volcano_tts.synthesize(text, language)`.

## ASR: V3 Flash HTTP API

### Module: `backend/volcano_asr.py`

**Endpoint:** `POST https://openspeech.bytedance.com/api/v3/auc/bigmodel/recognize/flash`

**Headers:**
- `X-Api-Key: 1724131082`
- `X-Api-Resource-Id: volc.bigasr.auc_turbo`
- `X-Api-Request-Id: {uuid}`
- `X-Api-Sequence: -1`

**Request body:**
```json
{
  "user": {"uid": "1724131082"},
  "audio": {"data": "<base64-encoded-audio>"},
  "request": {"model_name": "bigmodel"}
}
```

**Response:** `{"result": {"text": "recognized text", "utterances": [...]}}`

**Error handling:** httpx timeout of 10 seconds. On failure, return HTTP 500. Frontend shows error toast.

### Endpoint change: `/asr` in `main.py`

Replace mock implementation (lines 498-555) with call to `volcano_asr.recognize(audio_base64, language)`.

## Dependencies

Add to `requirements.txt`: `websockets>=12.0`

## Frontend

No changes needed. Existing call logic and browser TTS/ASR fallback are already in place.

## Files changed

| File | Change |
|------|--------|
| `backend/volcano_tts.py` | New — WebSocket TTS client |
| `backend/volcano_asr.py` | New — HTTP ASR client |
| `backend/main.py` | Replace mock `/tts` and `/asr` with real implementations |
| `backend/requirements.txt` | Add `websockets>=12.0` |
