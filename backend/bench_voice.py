"""
Voice benchmark: measures real TTS/ASR performance (latency, success rate, fallback rate)
under single and concurrent load.

Run: python bench_voice.py [--concurrency N] [--runs N]
"""
import argparse
import asyncio
import base64
import os
import statistics
import struct
import sys
import time
from typing import Any, Awaitable, Callable

from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")


def make_silent_wav(seconds: float = 0.5, sample_rate: int = 16000) -> str:
    num_samples = int(sample_rate * seconds)
    data_size = num_samples * 2
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1, sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return base64.b64encode(header + b"\x00" * data_size).decode()


async def time_call(fn: Callable[..., Awaitable[Any]], *args, **kwargs):
    t0 = time.perf_counter()
    err = None
    result = None
    try:
        result = await fn(*args, **kwargs)
    except Exception as e:
        err = e
    dur = time.perf_counter() - t0
    return dur, result, err


async def run_batch(label: str, fn, args_list, concurrency: int):
    sem = asyncio.Semaphore(concurrency)

    async def bound(args):
        async with sem:
            return await time_call(fn, *args)

    t0 = time.perf_counter()
    results = await asyncio.gather(*[bound(a) for a in args_list])
    wall = time.perf_counter() - t0
    latencies = [r[0] for r in results]
    errors = [r[2] for r in results if r[2] is not None]
    successes = [r for r in results if r[2] is None]

    print(f"\n=== {label} (concurrency={concurrency}, runs={len(args_list)}) ===")
    print(f"  wall time:     {wall:.2f}s")
    print(f"  success rate:  {len(successes)}/{len(results)} ({100*len(successes)/len(results):.0f}%)")
    if latencies:
        print(f"  latency p50:   {statistics.median(latencies):.2f}s")
        print(f"  latency p95:   {sorted(latencies)[int(len(latencies)*0.95) - 1] if len(latencies) > 1 else latencies[0]:.2f}s")
        print(f"  latency max:   {max(latencies):.2f}s")
        print(f"  latency mean:  {statistics.mean(latencies):.2f}s")
    if errors:
        print(f"  errors ({len(errors)}):")
        for e in errors[:3]:
            print(f"    - {type(e).__name__}: {e}")
    return {
        "label": label,
        "wall": wall,
        "success_rate": len(successes) / len(results),
        "p50": statistics.median(latencies) if latencies else 0,
        "mean": statistics.mean(latencies) if latencies else 0,
        "max": max(latencies) if latencies else 0,
    }


async def bench_tts(runs: int, concurrency: int, label_suffix: str = ""):
    from volcano_tts import synthesize, clear_cache
    clear_cache()
    # Unique per-run text to defeat the cache so we measure backend cost.
    texts_zh = [
        "大克鼎是西周晚期青铜器中的杰出代表。",
        "上海博物馆珍藏了大量中国古代艺术品。",
        "青铜器馆展出了商周时期的礼器。",
        "明清瓷器展现了中国陶瓷艺术的巅峰。",
        "书法馆收藏了历代名家的墨宝。",
        "绘画馆以宋元书画最为珍贵。",
        "玉器馆展示古代玉雕精品。",
        "钱币馆汇集了历代货币。",
    ]
    texts_en = [
        "The Da Ke Ding is a bronze ritual vessel.",
        "Welcome to the Shanghai Museum.",
        "The jade collection spans several dynasties.",
        "The ceramic hall features Song porcelain.",
        "The painting gallery holds scrolls from the Yuan dynasty.",
        "Ancient coins trace the history of trade.",
        "Bronze vessels were used in ritual ceremonies.",
        "This calligraphy scroll dates from the Tang dynasty.",
    ]
    args_list = []
    for i in range(runs):
        if i % 2 == 0:
            args_list.append((texts_zh[i % len(texts_zh)], "zh"))
        else:
            args_list.append((texts_en[i % len(texts_en)], "en"))
    return await run_batch(f"TTS{label_suffix}", synthesize, args_list, concurrency)


async def bench_tts_cache(runs: int):
    """Measure cache-hit speed: first call populates, rest should be instant."""
    from volcano_tts import synthesize, clear_cache
    clear_cache()
    text = "上海博物馆大克鼎介绍"
    await synthesize(text, "zh")  # warm
    args_list = [(text, "zh") for _ in range(runs)]
    return await run_batch("TTS-cache-hit", synthesize, args_list, concurrency=runs)


async def bench_asr(runs: int, concurrency: int):
    from volcano_asr import recognize
    wav = make_silent_wav(0.5)
    args_list = [(wav, "zh") for _ in range(runs)]
    return await run_batch("ASR", recognize, args_list, concurrency)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=8)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--only", choices=["tts", "asr", "both"], default="both")
    args = parser.parse_args()

    if not os.getenv("VOLCANO_ACCESS_TOKEN"):
        print("WARN: VOLCANO_ACCESS_TOKEN not set")

    print(f"Runs per scenario: {args.runs}, concurrency: {args.concurrency}")

    results = []
    if args.only in ("tts", "both"):
        results.append(await bench_tts(args.runs, 1, " serial   "))
        results.append(await bench_tts(args.runs, args.concurrency, " concurrent"))
        results.append(await bench_tts_cache(args.runs))

    if args.only in ("asr", "both"):
        results.append(await bench_asr(args.runs, 1))
        results.append(await bench_asr(args.runs, args.concurrency))

    print("\n=== summary ===")
    for r in results:
        print(f"  {r['label']:30s} wall={r['wall']:.2f}s p50={r['p50']:.2f}s "
              f"max={r['max']:.2f}s success={100*r['success_rate']:.0f}%")


if __name__ == "__main__":
    asyncio.run(main())
