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
        facts, meta = extract.extract(pages, model, cfg.models["ollama_host"],
                                     cfg.models["num_ctx"], cfg.models["num_predict"])
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


def _read_cached(path: Path, cfg: config.Config):
    """Read a bill (or return the cached read). Returns (sha, facts)."""
    from . import extract, ingest, store
    sha = store.sha12([path])
    d = store.bill_dir(sha)
    cached = store.load_facts(d)
    if cached:
        return sha, cached[0]
    pages = ingest.load_pages([path], cfg.models["max_pages"], cfg.models["max_image_side"])
    facts, meta = extract.extract(pages, cfg.models["extract"], cfg.models["ollama_host"],
                                  cfg.models["num_ctx"], cfg.models["num_predict"])
    store.save_model_facts(d, facts, {k: v for k, v in meta.items() if k != "raw"})
    return sha, facts


def cmd_batch(args) -> int:
    from . import extract, quote, render, store
    cfg = _cfg(args)
    files = sorted(p for p in Path(args.dir).iterdir()
                   if p.suffix.lower() in (".pdf", ".jpg", ".jpeg", ".png"))
    print(f"{'file':32} {'services':18} {'flags':22} savings (incl. GST)")
    for p in files:
        try:
            sha, facts = _read_cached(p, cfg)
        except extract.ExtractError as e:
            print(f"{p.name:32} READ FAILED: {str(e)[:60]}")
            continue
        flags = check_bill(facts, cfg)
        counts = {s: sum(f.severity == s for f in flags) for s in ("BLOCK", "WARN", "INFO")}
        flag_txt = " ".join(f"{n}{s[0]}" for s, n in counts.items() if n) or "-"
        svc = "+".join(s.commodity[:4] for s in facts.services)
        if has_block(flags):
            print(f"{p.name:32} {svc:18} {flag_txt:22} NEEDS REVIEW (blocking flag)")
            continue
        q = quote.build_quote(facts, cfg)
        sav = " ".join(f"{s.commodity[:4]} {render.money(s.diff) if s.diff >= 0 else '-' + render.money(-s.diff)}"
                       for s in q.services)
        out = store.bill_dir(sha) / "quote-staff.html"
        out.write_text(render.render_quote(facts, q, flags, cfg, view="staff", draft=True),
                       encoding="utf-8")
        print(f"{p.name:32} {svc:18} {flag_txt:22} {sav}")
    return 0


def cmd_serve(args) -> int:
    import os

    import uvicorn

    from .web.app import create_app
    if args.host not in ("127.0.0.1", "localhost", "::1") \
            and not os.environ.get("BILL2QUOTE_PASSWORD"):
        print("Refusing to listen off localhost without BILL2QUOTE_PASSWORD set.", file=sys.stderr)
        return 1
    uvicorn.run(create_app(_cfg(args)), host=args.host, port=args.port)
    return 0


def cmd_eval(args) -> int:
    from . import evaluate
    cfg = _cfg(args)
    models = args.model or [cfg.models["extract"]]
    result = evaluate.run(Path(args.dir), models, cfg)
    md = evaluate.markdown(result)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "eval.md").write_text(md, encoding="utf-8")
    (out / "eval.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(md)
    return 0


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
    sv = sub.add_parser("serve", help="run the web app (default 127.0.0.1:8000)")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.set_defaults(fn=cmd_serve)
    b = sub.add_parser("batch", help="read + check + staff quote for every bill in DIR")
    b.add_argument("dir")
    b.set_defaults(fn=cmd_batch)
    e = sub.add_parser("eval", help="score models against *.truth.json files")
    e.add_argument("dir")
    e.add_argument("--model", action="append")
    e.add_argument("--out", default="docs/eval")
    e.set_defaults(fn=cmd_eval)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
