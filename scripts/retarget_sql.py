"""Retarget the demo SQL to a different catalog / schema naming for production.

The committed SQL hard-codes the demo's co-located layout
(`elexon_app_for_settlement_acc_catalog.momentum_claims_<layer>` /
`...momentum_uw_<layer>`) because the demo workspace lacks CREATE CATALOG. On a
production workspace WITH catalog rights you'd use a dedicated catalog and clean
schema names. This script rewrites the FQNs so you don't hand-edit every file.

Usage:
    python scripts/retarget_sql.py --catalog momentum_claims_demo \
        --out build/prod_sql [--uw-catalog momentum_uw]

Default mapping (demo -> prod):
    <democat>.momentum_claims_<layer>  ->  <catalog>.<layer>
    <democat>.momentum_uw_<layer>      ->  <uw_catalog or catalog>.uw_<layer>

It only rewrites FQNs; it does not run anything. Review the output, then run the
files (or point the DAB jobs at them) against the prod workspace.
"""
from __future__ import annotations

import argparse
import pathlib
import re

DEMO_CAT = "elexon_app_for_settlement_acc_catalog"
CLAIMS_LAYERS = ["bronze", "silver", "gold", "ai", "ops"]
UW_LAYERS = ["bronze", "silver", "gold", "ai"]

SQL_DIRS = ["sql", "src/pipelines", "src/ai/tools"]


def retarget(text: str, catalog: str, uw_catalog: str) -> str:
    # underwriting first (more specific prefix), then claims
    for layer in UW_LAYERS:
        text = text.replace(f"{DEMO_CAT}.momentum_uw_{layer}", f"{uw_catalog}.uw_{layer}")
    for layer in CLAIMS_LAYERS:
        text = text.replace(f"{DEMO_CAT}.momentum_claims_{layer}", f"{catalog}.{layer}")
    return text


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, help="Target catalog for claims (and UW if --uw-catalog omitted).")
    ap.add_argument("--uw-catalog", default=None, help="Optional separate catalog for underwriting.")
    ap.add_argument("--out", default="build/prod_sql", help="Output directory.")
    ap.add_argument("--root", default=".", help="Repo root.")
    args = ap.parse_args()

    uw_catalog = args.uw_catalog or args.catalog
    root = pathlib.Path(args.root).resolve()
    out = pathlib.Path(args.out).resolve()

    n = 0
    for d in SQL_DIRS:
        for src in (root / d).rglob("*.sql"):
            rel = src.relative_to(root)
            dst = out / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(retarget(src.read_text(), args.catalog, uw_catalog))
            n += 1
    print(f"Retargeted {n} SQL files -> {out}")
    print(f"  claims: {DEMO_CAT}.momentum_claims_<layer>  ->  {args.catalog}.<layer>")
    print(f"  uw:     {DEMO_CAT}.momentum_uw_<layer>       ->  {uw_catalog}.uw_<layer>")
    print("Also update the app env (MOMENTUM_CATALOG, MOMENTUM_*_SCHEMA in app.yaml) "
          "and the UW server FQNs (server/uw_data.py CAT/G/S/AI) or drive them from env.")


if __name__ == "__main__":
    main()
