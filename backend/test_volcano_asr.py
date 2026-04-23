"""
Integration test for Volcano Engine ASR.
Requires VOLCANO_ACCESS_TOKEN env var to be set.
Run: python test_volcano_asr.py
"""
import asyncio
import base64
import os
import sys

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(dotenv_path='../.env')

async def test_asr():
    from volcano_asr import recognize

    import struct
    sample_rate = 16000
    num_samples = sample_rate // 2
    data_size = num_samples * 2
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
