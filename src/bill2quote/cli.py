"""bill2quote command line."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from . import __version__, config
from .checks import check_bill, has_block


def _cfg(args) -> config.Config:
    return config.load(args.config)


def cmd_init(args) -> int:
    dest = Path("config.toml")
    if dest.exists():
        print("config.toml already exists; leaving it alone.")
        return 0
    src = Path(__file__).resolve().parents[2] / "config.example.toml"
    shutil.copy(src, dest)
    for d in ("data/inbox", "data/bills"):
        Path(d).mkdir(parents=True, exist_ok=True)
    print("Wrote config.toml and data/ (both gitignored).")
    return 0


def cmd_doctor(args) -> int:
    from . import doctor
    rows = doctor.run(_cfg(args))
    for ok, msg in rows:
        print(("  ok   " if ok else "  FAIL ") + msg)
    return 0 if all(ok for ok, _ in rows) else 1


def cmd_read(args) -> int:
    from . import extract, ingest
    cfg = _cfg(args)
    model = args.model or cfg.models["extract"]
    pages = ingest.load_pages([Path(p) for p in args.files], cfg.models["max_pages"],
                              cfg.models["max_image_side"])
    try:
        facts, meta = extract.extract(pages, model, cfg.models["ollama_host"])
    except extract.ExtractError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    out = {"facts": facts.model_dump(), "meta": {k: v for k, v in meta.items() if k != "raw"}}
    print(json.dumps(out, indent=2))
    return 0


def cmd_check(args) -> int:
    from .schema import BillFacts
    cfg = _cfg(args)
    data = json.loads(Path(args.facts).read_text(encoding="utf-8"))
    facts = BillFacts.model_validate(data.get("facts", data))
    flags = check_bill(facts, cfg)
    for f in flags:
        print(f"{f.severity:5} {f.id} {f.field}: {f.message}")
    if not flags:
        print("no flags")
    return 2 if has_block(flags) else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="bill2quote",
                                description="Photo of a utility bill in, honest savings quote out.")
    p.add_argument("--version", action="version", version=f"bill2quote {__version__}")
    p.add_argument("--config", help="path to config.toml (default: ./config.toml)")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init", help="create config.toml and data/").set_defaults(fn=cmd_init)
    sub.add_parser("doctor", help="check Ollama, models, image support, PDF rendering"
                   ).set_defaults(fn=cmd_doctor)
    r = sub.add_parser("read", help="read bill image(s)/PDF into BillFacts JSON")
    r.add_argument("files", nargs="+")
    r.add_argument("--model")
    r.set_defaults(fn=cmd_read)
    c = sub.add_parser("check", help="run the deterministic checks on a facts JSON file")
    c.add_argument("facts")
    c.set_defaults(fn=cmd_check)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
