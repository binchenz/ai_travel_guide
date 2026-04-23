"""API contract tests for /ontology/* and /exhibits/* endpoints.
Run: python test_api_ontology.py
"""
from __future__ import annotations
import asyncio, sys


async def _get(c, path):
    r = await c.get(path)
    assert r.status_code == 200, f"{path} -> {r.status_code}: {r.text}"
    return r.json()


async def run():
    from httpx import AsyncClient, ASGITransport
    from main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        halls = await _get(c, "/ontology/halls")
        assert any(h["id"] == "hall/bronze-gallery" for h in halls), "bronze-gallery missing"

        dynasties = await _get(c, "/ontology/dynasties")
        assert any(d["id"] == "dynasty/western-zhou" for d in dynasties), "western-zhou missing"

        persons = await _get(c, "/ontology/persons")
        assert any(p["id"] == "person/king-li-of-zhou" for p in persons), "king-li missing"

        wz_arts = await _get(c, "/ontology/dynasties/dynasty/western-zhou/artifacts")
        assert any(a["id"] == "artifact/da-ke-ding" for a in wz_arts), "da-ke-ding not in western-zhou"

        detail = await _get(c, "/exhibits/artifact/da-ke-ding")
        assert detail["hall"]["id"] == "hall/bronze-gallery"
        assert detail["dynasty"]["id"] == "dynasty/western-zhou"
        assert len(detail["persons"]) == 1

        missing = await c.get("/ontology/halls/hall/does-not-exist/artifacts")
        assert missing.status_code == 404, f"expected 404 got {missing.status_code}"

    print("PASS api contract")


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except AssertionError as e:
        print(f"FAIL: {e}")
        sys.exit(1)
