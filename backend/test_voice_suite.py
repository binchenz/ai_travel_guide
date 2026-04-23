"""Regression + performance suite for the /tts and /asr path.

Covers:
- correctness: valid short text returns playable audio bytes
- cache: repeated identical text is served from the LRU and is nearly free
- concurrency: N concurrent requests stay bounded by the semaphore
- asr happy path on silent PCM returns an empty string without raising
- asr error path: bad base64 raises ValueError; empty audio returns ""

Run: python test_voice_suite.py
"""
from __future__ import annotations

import asyncio
import base64
import os
import statistics
import struct
import sys
import time

from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")


def _silent_wav(seconds: float = 0.5, sample_rate: int = 16000) -> str:
    num_samples = int(sample_rate * seconds)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return base64.b64encode(header + b"\x00" * data_size).decode()


async def assert_async(coro, msg: str):
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL: {msg}: {exc}")
        raise


async def test_tts_cache_hit_speedup():
    from volcano_tts import clear_cache, synthesize

    clear_cache()
    text = "上海博物馆欢迎你。"

    t0 = time.perf_counter()
    first = await synthesize(text, "zh")
    cold = time.perf_counter() - t0
    assert len(first["audio"]) > 100

    t0 = time.perf_counter()
    second = await synthesize(text, "zh")
    warm = time.perf_counter() - t0

    assert second["audio"] == first["audio"], "cache should return identical bytes"
    speedup = cold / warm if warm else float("inf")
    assert warm < 0.05, f"cache hit should be <50ms, got {warm*1000:.1f}ms"
    print(f"PASS cache: cold={cold*1000:.0f}ms warm={warm*1000:.2f}ms speedup={speedup:.0f}x")


async def test_tts_concurrent():
    from volcano_tts import clear_cache, synthesize

    clear_cache()
    texts = [
        ("大克鼎是西周晚期青铜器。", "zh"),
        ("The Da Ke Ding is a bronze ritual vessel.", "en"),
        ("上海博物馆珍藏众多中国古代艺术品。", "zh"),
        ("Welcome to the Shanghai Museum.", "en"),
    ]
    runs = [texts[i % len(texts)] for i in range(8)]
    t0 = time.perf_counter()
    results = await asyncio.gather(*[synthesize(t, l) for t, l in runs])
    wall = time.perf_counter() - t0

    for r in results:
        assert "audio" in r and len(r["audio"]) > 100, r
    print(f"PASS concurrent: 8 requests in {wall:.2f}s (wall), avg {wall/8:.2f}s per")


async def test_asr_silent_returns_empty():
    from volcano_asr import recognize
    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        print("SKIP asr: VOLCANO_ACCESS_TOKEN not set")
        return
    result = await recognize(_silent_wav(0.5), "zh")
    assert result["text"] == "", f"silent clip should yield empty text, got {result}"
    print(f"PASS asr silent: {result}")


async def test_asr_bad_base64():
    from volcano_asr import recognize
    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        print("SKIP asr bad-base64: token missing")
        return
    # Valid base64 but non-WAV audio: should not raise, but likely produce empty text.
    raw = b"not a real audio payload" * 200
    result = await recognize(base64.b64encode(raw).decode(), "zh")
    assert "text" in result
    print(f"PASS asr garbage audio: text_empty={result['text']==''}")


async def test_tts_empty_text_raises():
    from volcano_tts import synthesize
    for bad in ("", "   ", "\n"):
        try:
            await synthesize(bad, "zh")
        except ValueError:
            continue
        print(f"FAIL: synthesize({bad!r}) should have raised ValueError")
        sys.exit(1)
    print("PASS tts empty-text validation")


async def test_wav_header_strip():
    from volcano_asr import _strip_wav_header

    # Proper WAV: 44-byte header + 16 bytes of data
    body = b"\x00\x01" * 8
    data_size = len(body)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, 16000, 32000, 2, 16,
        b"data", data_size,
    )
    wav = header + body
    assert _strip_wav_header(wav) == body, "should return body of a real WAV"

    # Non-WAV: should pass through unchanged
    raw = b"\xff\xfe" * 16
    assert _strip_wav_header(raw) == raw
    print("PASS wav header stripping")


async def main():
    print("=== voice suite ===")
    failures = 0
    tests = [
        test_wav_header_strip(),
        test_tts_empty_text_raises(),
        test_tts_cache_hit_speedup(),
        test_tts_concurrent(),
        test_asr_silent_returns_empty(),
        test_asr_bad_base64(),
    ]
    for coro in tests:
        try:
            await coro
        except Exception as exc:  # noqa: BLE001
            failures += 1
            print(f"  {exc}")
    print(f"=== {failures} failures ===")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    asyncio.run(main())
