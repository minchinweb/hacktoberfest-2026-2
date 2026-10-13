"""Read a bill with an Ollama vision model, schema-constrained (SPEC §11)."""

from __future__ import annotations

import base64
import time
from importlib import resources
from pathlib import Path

import httpx
from PIL import Image

from .ingest import to_png_bytes
from .schema import BillFacts, json_schema

PROMPT_VERSION = "extract_v1"
TIMEOUT = 600.0


def prompt_text() -> str:
    # Repo checkout first; fall back to a copy beside the package if installed elsewhere.
    for p in (Path(__file__).resolve().parents[2] / "prompts" / f"{PROMPT_VERSION}.md",
              Path("prompts") / f"{PROMPT_VERSION}.md"):
        if p.exists():
            return p.read_text(encoding="utf-8")
    return resources.files("bill2quote").joinpath(f"{PROMPT_VERSION}.md").read_text("utf-8")


class ExtractError(RuntimeError):
    pass


def extract(pages: list[Image.Image], model: str, host: str) -> tuple[BillFacts, dict]:
    """One request with all pages. Returns (facts, meta). Raises ExtractError on bad output."""
    images = [base64.b64encode(to_png_bytes(p)).decode() for p in pages]
    body = {
        "model": model,
        "stream": False,
        "think": False,
        "format": json_schema(),
        "options": {"temperature": 0},
        "messages": [{"role": "user", "content": prompt_text(), "images": images}],
    }
    t0 = time.monotonic()
    try:
        r = httpx.post(f"{host}/api/chat", json=body, timeout=TIMEOUT)
        r.raise_for_status()
    except httpx.HTTPError as e:
        raise ExtractError(f"Ollama request failed: {e}") from e
    seconds = round(time.monotonic() - t0, 1)
    raw = r.json().get("message", {}).get("content", "")
    meta = {"model": model, "prompt_version": PROMPT_VERSION, "seconds": seconds, "raw": raw}
    try:
        return BillFacts.model_validate_json(raw), meta
    except ValueError as e:
        meta["error"] = str(e)
        raise ExtractError(f"model output did not match the schema: {e}") from e
