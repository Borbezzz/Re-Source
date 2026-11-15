"""Content-addressed upload storage (contract v1.1).

Every upload is cached locally under `<RS_VAR_DIR>/uploads/<sha256><ext>`. When Databricks is configured
it is also mirrored to the Unity Catalog volume `/Volumes/<catalog>/<schema>/rs_uploads/` (created once
with CREATE VOLUME IF NOT EXISTS), which is the durable copy for a Databricks App whose local disk is
ephemeral. `storage_uri` always reports where the authoritative copy actually lives.
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import tempfile
import threading
from pathlib import Path
from typing import Optional

from ..config import settings
from .databricks_sql import databricks_sql

log = logging.getLogger("recovery.blob_store")
VOLUME_NAME = "rs_uploads"


class BlobStore:
    def __init__(self) -> None:
        self._volume_ready: Optional[bool] = None
        self._lock = threading.Lock()
        self.last_error: Optional[str] = None

    # ------------------------------------------------------------------ paths
    @property
    def local_dir(self) -> Path:
        d = Path(settings.var_dir) / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def local_path(self, sha: str, ext: str) -> Path:
        return self.local_dir / f"{sha}{ext}"

    def volume_dir(self) -> str:
        return f"/Volumes/{settings.databricks_catalog}/{settings.databricks_schema}/{VOLUME_NAME}"

    def volume_path(self, sha: str, ext: str) -> str:
        return f"{self.volume_dir()}/{sha}{ext}"

    def is_safe_volume_path(self, path: str) -> bool:
        return bool(re.fullmatch(re.escape(self.volume_dir()) + r"/[0-9a-f]{64}\.(pdf|png|jpg|jpeg|txt|md|json|glb|gltf)", path))

    # ------------------------------------------------------------------ write/read
    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()

    def put_local(self, data: bytes, ext: str) -> tuple[str, Path]:
        sha = self.sha256(data)
        path = self.local_path(sha, ext)
        if not path.exists():
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as file:
                tmp = Path(file.name)
                try:
                    file.write(data)
                    file.close()
                    tmp.replace(path)
                finally:
                    tmp.unlink(missing_ok=True)
        return sha, path

    def _client(self):  # noqa: ANN202
        from databricks.sdk import WorkspaceClient

        if settings.databricks_token:
            return WorkspaceClient(host=settings.databricks_host or f"https://{settings.databricks_server_hostname}", token=settings.databricks_token)
        return WorkspaceClient()  # Databricks App service principal (DATABRICKS_CLIENT_ID/SECRET)

    def ensure_volume(self) -> bool:
        with self._lock:
            if self._volume_ready is not None:
                return self._volume_ready
            if not databricks_sql.configured:
                self._volume_ready = False
                return False
            try:
                rows = databricks_sql.query(f"SHOW VOLUMES IN {databricks_sql.fq_schema} LIKE '{VOLUME_NAME}'")
                if not rows:
                    databricks_sql.query(f"CREATE VOLUME IF NOT EXISTS {databricks_sql.fq_schema}.`{VOLUME_NAME}` "
                                         "COMMENT 'Re-Source intake uploads (content-addressed by sha256)'")
                self._volume_ready = True
            except Exception as exc:  # noqa: BLE001
                self.last_error = f"volume unavailable: {str(exc)[:200]}"
                log.warning(self.last_error)
                self._volume_ready = False
            return self._volume_ready

    def mirror(self, sha: str, ext: str) -> Optional[str]:
        """Copy the local blob to the UC volume; returns the volume path or None."""
        if not self.ensure_volume():
            return None
        vpath = self.volume_path(sha, ext)
        try:
            data = self.local_path(sha, ext).read_bytes()
            self._client().files.upload(vpath, io.BytesIO(data), overwrite=True)
            return vpath
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"mirror failed: {str(exc)[:200]}"
            log.warning(self.last_error)
            return None

    def read(self, sha: str, ext: str, volume_uri: Optional[str] = None) -> bytes:
        path = self.local_path(sha, ext)
        if path.exists():
            return path.read_bytes()
        if volume_uri and self.is_safe_volume_path(volume_uri):
            resp = self._client().files.download(volume_uri)
            data = resp.contents.read()
            if self.sha256(data) != sha:
                raise ValueError("volume copy hash mismatch")
            self.put_local(data, ext)
            return data
        raise FileNotFoundError(f"blob {sha}{ext} not available")


blob_store = BlobStore()
