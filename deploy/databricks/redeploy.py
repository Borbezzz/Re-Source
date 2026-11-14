"""Sync the Re-Source runtime files and redeploy its Databricks App."""

from __future__ import annotations

import argparse
from datetime import timedelta
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.apps import AppDeployment, AppDeploymentMode
from databricks.sdk.service.workspace import ImportFormat
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_FILES = ("app.yaml", "requirements.txt")
RUNTIME_DIRS = ("backend/recovery", "data/fixtures", "data/manifests", "rules", "templates")


def deployment_files() -> list[Path]:
    files = [ROOT / name for name in RUNTIME_FILES]
    directories = [ROOT / name for name in RUNTIME_DIRS]
    frontend = ROOT / "frontend" / "dist"
    if frontend.exists():
        if not (frontend / "index.html").is_file():
            raise ValueError("frontend/dist exists but has no index.html. Build the frontend before deploying.")
        directories.append(frontend)
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Invalid deployment file: {path.relative_to(ROOT)}")
    for directory in directories:
        if not directory.is_dir() or directory.resolve() != directory:
            raise ValueError(f"Invalid deployment directory: {directory.relative_to(ROOT)}")
        for path in directory.rglob("*"):
            relative = path.relative_to(directory)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            if path.is_symlink():
                raise ValueError(f"Symlinks are unsupported: {path.relative_to(ROOT)}")
            if path.is_file() and path.suffix not in {".pyc", ".pyo"}:
                files.append(path)
    return sorted(files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--app", default="resource")
    parser.add_argument("--source", default="/Workspace/Shared/ReSource/app-src")
    parser.add_argument("--dry-run", action="store_true", help="List files without connecting to Databricks.")
    args = parser.parse_args()
    planned = deployment_files()
    source = args.source.rstrip("/")
    if not source.startswith("/Workspace/") or any(part in {"", ".", ".."} for part in source.split("/")[2:]):
        parser.error("--source must name a directory under /Workspace/")

    if args.dry_run:
        for path in planned:
            print(path.relative_to(ROOT).as_posix())
        print(f"Would sync {len(planned)} files to {source} and redeploy {args.app}.")
        return

    load_dotenv(ROOT / ".env", override=False)
    client = WorkspaceClient()
    app = client.apps.get(args.app)
    print(f"Syncing {len(planned)} files to {source} for {app.name}", flush=True)
    created = set()
    for path in planned:
        destination = f"{source}/{path.relative_to(ROOT).as_posix()}"
        parent = destination.rsplit("/", 1)[0]
        if parent not in created:
            client.workspace.mkdirs(parent)
            created.add(parent)
        with path.open("rb") as content:
            client.workspace.upload(destination, content, format=ImportFormat.AUTO, overwrite=True)
    deployment = client.apps.deploy(
        args.app, AppDeployment(source_code_path=source, mode=AppDeploymentMode.SNAPSHOT)
    )
    print(f"Deployment {deployment.response.deployment_id} submitted.", flush=True)
    deployed = deployment.result(timeout=timedelta(minutes=15))
    print(f"Deployment {deployed.deployment_id} succeeded: {app.url}")


if __name__ == "__main__":
    main()
