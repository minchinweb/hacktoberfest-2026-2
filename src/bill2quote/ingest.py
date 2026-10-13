"""Photos and PDFs in, normalised page images out (SPEC §7)."""

from __future__ import annotations

import io
from pathlib import Path

import pypdfium2 as pdfium
from PIL import Image, ImageOps

PDF_DPI = 200


def _normalise(img: Image.Image, max_side: int) -> Image.Image:
    img = ImageOps.exif_transpose(img).convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
    return img


def load_pages(paths: list[Path], max_pages: int = 4, max_side: int = 2000) -> list[Image.Image]:
    """Each path is an image or a PDF. Returns at most `max_pages` RGB images."""
    pages: list[Image.Image] = []
    for p in paths:
        if p.suffix.lower() == ".pdf":
            pdf = pdfium.PdfDocument(str(p))
            for i in range(len(pdf)):
                if len(pages) >= max_pages:
                    break
                pil = pdf[i].render(scale=PDF_DPI / 72).to_pil()
                pages.append(_normalise(pil, max_side))
        else:
            with Image.open(p) as im:
                pages.append(_normalise(im, max_side))
        if len(pages) >= max_pages:
            break
    return pages[:max_pages]


def to_png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
