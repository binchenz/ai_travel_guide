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
