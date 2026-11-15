"""Export the canonical contracts (PRD §7, §14) from backend/recovery/domain/models.py.

Outputs:
  contracts/schemas/<Model>.json      JSON Schema per public Pydantic model
  contracts/schemas/all.json          combined schema ($defs for every model)
  contracts/openapi/openapi.json      FastAPI OpenAPI document (only if recovery.api.app imports)
  contracts/generated-types/api.ts    TypeScript types (openapi-typescript when OpenAPI exists,
                                      else json-schema-to-typescript over all.json)

Run:  cd backend && uv run python scripts/export_contracts.py [--no-ts]
Requires Node/npx for the TypeScript step (versions pinned below). Nothing here reads secrets.
"""

from __future__ import annotations

import argparse
import inspect
import json
import shutil
import subprocess
import sys
from enum import Enum
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
REPO = BACKEND.parent
sys.path.insert(0, str(BACKEND))

from pydantic import BaseModel  # noqa: E402

from recovery.domain import models  # noqa: E402
from recovery.domain import products  # noqa: E402
from recovery.domain import quotes  # noqa: E402

CONTRACTS = REPO / "contracts"
SCHEMAS = CONTRACTS / "schemas"
OPENAPI = CONTRACTS / "openapi"
TYPES = CONTRACTS / "generated-types"

OPENAPI_TS = "openapi-typescript@7.4.4"
JSON_SCHEMA_TS = "json-schema-to-typescript@15.0.2"


def public_models() -> dict[str, type[BaseModel]]:
    out: dict[str, type[BaseModel]] = {}
    for module in (models, products, quotes):
        for name, obj in inspect.getmembers(module, inspect.isclass):
            if obj.__module__ != module.__name__ or name.startswith("_") or name in ("Contract", "ProductContract"):
                continue
            if issubclass(obj, BaseModel):
                out[name] = obj
    return dict(sorted(out.items()))


def public_enums() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for name, obj in inspect.getmembers(models, inspect.isclass):
        if obj.__module__ == models.__name__ and issubclass(obj, Enum):
            out[name] = [m.value for m in obj]
    return dict(sorted(out.items()))


def export_schemas() -> Path:
    SCHEMAS.mkdir(parents=True, exist_ok=True)
    combined: dict = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Re-Source contracts",
        "description": f"Generated from backend/recovery/domain/models.py — schema_version {models.SCHEMA_VERSION}. Do not edit by hand.",
        "x-schema-version": models.SCHEMA_VERSION,
        "x-event-types": models.EVENT_TYPES,
        "x-enums": public_enums(),
        "$defs": {},
    }
    for name, model in public_models().items():
        schema = model.model_json_schema(ref_template="#/$defs/{model}", mode="serialization")
        defs = schema.pop("$defs", {})
        combined["$defs"].update(defs)
        combined["$defs"][name] = schema
        standalone = dict(schema)
        if defs:
            standalone["$defs"] = defs
        (SCHEMAS / f"{name}.json").write_text(json.dumps(standalone, indent=2, sort_keys=True) + "\n")
    # A top-level object referencing every model makes json-schema-to-typescript emit all of them.
    combined["type"] = "object"
    combined["properties"] = {name: {"$ref": f"#/$defs/{name}"} for name in public_models()}
    combined["additionalProperties"] = False
    all_path = SCHEMAS / "all.json"
    all_path.write_text(json.dumps(combined, indent=2, sort_keys=True) + "\n")
    print(f"wrote {len(public_models())} model schemas + all.json to {SCHEMAS.relative_to(REPO)}")
    return all_path


def export_openapi() -> Path | None:
    try:
        from recovery.api.app import app  # type: ignore
    except Exception as exc:  # noqa: BLE001 - API may not exist yet
        print(f"skip OpenAPI: recovery.api.app not importable ({type(exc).__name__}: {str(exc)[:120]})")
        return None
    OPENAPI.mkdir(parents=True, exist_ok=True)
    path = OPENAPI / "openapi.json"
    path.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"wrote {path.relative_to(REPO)}")
    return path


def export_types(openapi_path: Path | None, all_path: Path) -> None:
    npx = shutil.which("npx")
    if not npx:
        print("skip TypeScript: npx not found (install Node.js)")
        return
    TYPES.mkdir(parents=True, exist_ok=True)
    out = TYPES / "api.ts"
    if openapi_path and openapi_path.exists():
        cmd = [npx, "--yes", OPENAPI_TS, str(openapi_path), "-o", str(out)]
    else:
        cmd = [npx, "--yes", JSON_SCHEMA_TS, "-i", str(all_path), "-o", str(out), "--unreachableDefinitions",
               "--additionalProperties", "false", "--bannerComment",
               "/* Generated from contracts/schemas/all.json (backend/recovery/domain/models.py). Do not edit by hand. */"]
    print("running:", " ".join(Path(c).name if i == 0 else c for i, c in enumerate(cmd)))
    res = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True, timeout=600)
    if res.returncode != 0:
        print("TypeScript generation failed:\n" + (res.stderr or res.stdout)[-2000:])
        return
    # Append runtime constants that are not expressible as JSON Schema types.
    extra = (
        "\n// ---- appended by backend/scripts/export_contracts.py ----\n"
        f"export const SCHEMA_VERSION = {json.dumps(models.SCHEMA_VERSION)};\n"
        f"export const EVENT_TYPES = {json.dumps(models.EVENT_TYPES, indent=2)} as const;\n"
        "export type DomainEventType = (typeof EVENT_TYPES)[number];\n"
    )
    with out.open("a") as fh:
        fh.write(extra)
    print(f"wrote {out.relative_to(REPO)}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-ts", action="store_true", help="skip TypeScript generation")
    args = ap.parse_args()
    all_path = export_schemas()
    openapi_path = export_openapi()
    if not args.no_ts:
        export_types(openapi_path, all_path)


if __name__ == "__main__":
    main()
