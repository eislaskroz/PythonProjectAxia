from __future__ import annotations
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    files = [Path(p) for p in sys.argv[1:]]
    if not files or any(not p.is_file() for p in files):
        raise SystemExit("Indica uno o más archivos existentes.")
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "files": [{"name": p.name, "size": p.stat().st_size, "sha256": sha256(p)} for p in files],
    }
    out = files[0].parent / "release_manifest.json"
    out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(out)
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
