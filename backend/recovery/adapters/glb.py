"""Minimal, dependency-free glTF 2.0 / GLB reader for mesh identity validation (contract v1.1).

Reads the JSON chunk only: node names, hierarchy, translation/scale (or matrix), mesh primitives and
the POSITION accessor `min`/`max`/`count` (glTF requires min/max on POSITION accessors), plus
`node.extras`. Binary buffers are never decoded. Inputs are untrusted: sizes and structure are checked.
"""

from __future__ import annotations

import json
import math
import struct
from dataclasses import dataclass, field
from typing import Any, Optional

GLB_MAGIC = 0x46546C67  # b"glTF"
CHUNK_JSON = 0x4E4F534A
CHUNK_BIN = 0x004E4942
MAX_JSON_BYTES = 16 * 1024 * 1024


class GLTFError(ValueError):
    pass


@dataclass
class NodeInfo:
    index: int
    name: Optional[str]
    mesh: Optional[int]
    children: list[int]
    parent: Optional[int]
    translation: list[float]
    scale: list[float]
    extras: dict[str, Any]
    world_translation: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    world_scale: list[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    vertex_count: int = 0
    bbox_min: Optional[list[float]] = None
    bbox_max: Optional[list[float]] = None


def is_glb(data: bytes) -> bool:
    return len(data) >= 12 and struct.unpack_from("<I", data, 0)[0] == GLB_MAGIC


def load_json(data: bytes) -> dict:
    """Return the glTF JSON document from GLB bytes or a .gltf JSON file."""
    if is_glb(data):
        magic, version, length = struct.unpack_from("<III", data, 0)
        if version != 2:
            raise GLTFError(f"unsupported GLB version {version}")
        if length > len(data):
            raise GLTFError("GLB header length exceeds file size")
        offset = 12
        while offset + 8 <= length:
            chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
            offset += 8
            if chunk_len > MAX_JSON_BYTES and chunk_type == CHUNK_JSON:
                raise GLTFError("GLB JSON chunk too large")
            chunk = data[offset:offset + chunk_len]
            offset += chunk_len
            if chunk_type == CHUNK_JSON:
                try:
                    return json.loads(chunk.decode("utf-8").rstrip(" \x00"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise GLTFError(f"invalid GLB JSON chunk: {exc}") from exc
        raise GLTFError("GLB has no JSON chunk")
    try:
        doc = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GLTFError(f"not a GLB or glTF JSON file: {exc}") from exc
    if not isinstance(doc, dict) or "asset" not in doc:
        raise GLTFError("glTF JSON missing 'asset'")
    return doc


def _trs(node: dict) -> tuple[list[float], list[float]]:
    if "matrix" in node and isinstance(node["matrix"], list) and len(node["matrix"]) == 16:
        m = [float(x) for x in node["matrix"]]
        t = [m[12], m[13], m[14]]
        s = [math.sqrt(m[0] ** 2 + m[1] ** 2 + m[2] ** 2), math.sqrt(m[4] ** 2 + m[5] ** 2 + m[6] ** 2),
             math.sqrt(m[8] ** 2 + m[9] ** 2 + m[10] ** 2)]
        return t, s
    t = [float(x) for x in node.get("translation", [0, 0, 0])][:3]
    s = [float(x) for x in node.get("scale", [1, 1, 1])][:3]
    return t, s


def _mesh_local_bounds(doc: dict, mesh_index: int) -> tuple[int, Optional[list[float]], Optional[list[float]]]:
    meshes = doc.get("meshes", [])
    accessors = doc.get("accessors", [])
    if mesh_index < 0 or mesh_index >= len(meshes):
        return 0, None, None
    count, lo, hi = 0, None, None
    for prim in meshes[mesh_index].get("primitives", []):
        acc_i = (prim.get("attributes") or {}).get("POSITION")
        if not isinstance(acc_i, int) or acc_i >= len(accessors):
            continue
        acc = accessors[acc_i]
        count += int(acc.get("count", 0))
        mn, mx = acc.get("min"), acc.get("max")
        if isinstance(mn, list) and isinstance(mx, list) and len(mn) >= 3 and len(mx) >= 3:
            lo = [min(a, float(b)) for a, b in zip(lo, mn)] if lo else [float(x) for x in mn[:3]]
            hi = [max(a, float(b)) for a, b in zip(hi, mx)] if hi else [float(x) for x in mx[:3]]
    return count, lo, hi


def parse_nodes(doc: dict) -> list[NodeInfo]:
    raw = doc.get("nodes", [])
    if not isinstance(raw, list):
        raise GLTFError("'nodes' is not a list")
    nodes: list[NodeInfo] = []
    for i, n in enumerate(raw):
        t, s = _trs(n)
        nodes.append(NodeInfo(index=i, name=n.get("name"), mesh=n.get("mesh") if isinstance(n.get("mesh"), int) else None,
                              children=[c for c in n.get("children", []) if isinstance(c, int) and 0 <= c < len(raw)], parent=None,
                              translation=t, scale=s, extras=n.get("extras") if isinstance(n.get("extras"), dict) else {}))
    for n in nodes:
        for c in n.children:
            nodes[c].parent = n.index
    # world transforms (translation/scale only), guarded against cycles
    def resolve(i: int, depth: int = 0) -> tuple[list[float], list[float]]:
        n = nodes[i]
        if n.parent is None or depth > 64:
            return n.translation, n.scale
        pt, ps = resolve(n.parent, depth + 1)
        return [pt[k] + ps[k] * n.translation[k] for k in range(3)], [ps[k] * n.scale[k] for k in range(3)]

    for n in nodes:
        n.world_translation, n.world_scale = resolve(n.index)
        if n.mesh is not None:
            cnt, lo, hi = _mesh_local_bounds(doc, n.mesh)
            n.vertex_count = cnt
            if lo and hi:
                a = [n.world_translation[k] + n.world_scale[k] * lo[k] for k in range(3)]
                b = [n.world_translation[k] + n.world_scale[k] * hi[k] for k in range(3)]
                n.bbox_min = [min(a[k], b[k]) for k in range(3)]
                n.bbox_max = [max(a[k], b[k]) for k in range(3)]
    return nodes


def subtree(nodes: list[NodeInfo], index: int) -> list[NodeInfo]:
    out, stack, seen = [], [index], set()
    while stack:
        i = stack.pop()
        if i in seen:
            continue
        seen.add(i)
        out.append(nodes[i])
        stack.extend(nodes[i].children)
    return out


def aggregate(nodes: list[NodeInfo], index: int) -> dict[str, Any]:
    """Mesh facts for a node including its descendants (a component may be a group of meshes)."""
    parts = [n for n in subtree(nodes, index) if n.mesh is not None]
    count = sum(n.vertex_count for n in parts)
    boxes = [(n.bbox_min, n.bbox_max) for n in parts if n.bbox_min and n.bbox_max]
    if boxes:
        lo = [min(b[0][k] for b in boxes) for k in range(3)]
        hi = [max(b[1][k] for b in boxes) for k in range(3)]
    else:
        lo = hi = None
    return {"is_mesh": bool(parts), "vertex_count": count, "bbox_min": lo, "bbox_max": hi, "mesh_nodes": [n.name for n in parts]}
