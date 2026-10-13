"""`bill2quote doctor`: is everything needed to read a bill actually working?"""

from __future__ import annotations

import base64

import httpx
from PIL import Image

from .config import Config
from .ingest import to_png_bytes


def _tiny_image_b64() -> str:
    return base64.b64encode(to_png_bytes(Image.new("RGB", (64, 64), "white"))).decode()


def run(cfg: Config) -> list[tuple[bool, str]]:
    """Returns (ok, message) rows."""
    host = cfg.models["ollama_host"]
    rows: list[tuple[bool, str]] = []
    try:
        tags = httpx.get(f"{host}/api/tags", timeout=10).json()
        have = {m["name"] for m in tags.get("models", [])}
        rows.append((True, f"Ollama reachable at {host}"))
    except (httpx.HTTPError, ValueError) as e:
        return [(False, f"Ollama not reachable at {host}: {e}")]

    wanted = list(dict.fromkeys([cfg.models["extract"], *cfg.models["compare"]]))
    for m in wanted:
        present = m in have or f"{m}:latest" in have
        rows.append((present, f"model {m} {'is pulled' if present else 'is NOT pulled (ollama pull)'}"))

    m = cfg.models["extract"]
    if m in have or f"{m}:latest" in have:
        try:
            r = httpx.post(f"{host}/api/chat", timeout=180, json={
                "model": m, "stream": False, "think": False,
                "messages": [{"role": "user", "content": "Reply with the word ok.",
                              "images": [_tiny_image_b64()]}]})
            r.raise_for_status()
            rows.append((True, f"{m} accepts an image"))
        except httpx.HTTPError as e:
            rows.append((False, f"{m} rejected an image request: {e}"))

    try:
        import pypdfium2 as pdfium
        pdfium.PdfDocument.new()
        rows.append((True, "PDF rendering (pypdfium2) works"))
    except Exception as e:  # noqa: BLE001
        rows.append((False, f"PDF rendering failed: {e}"))
    return rows
