from __future__ import annotations

import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.version import APP_VERSION


def main() -> int:
    iss = Path("installer/AXIA.iss").read_text(encoding="utf-8")
    match = re.search(r'#define\s+MyAppVersion\s+"([^"]+)"', iss)
    if not match:
        raise SystemExit("No fue posible leer MyAppVersion en installer/AXIA.iss")
    installer_version = match.group(1).strip()
    if installer_version != APP_VERSION:
        raise SystemExit(
            f"Versión desincronizada: core/version.py={APP_VERSION} / "
            f"installer/AXIA.iss={installer_version}"
        )
    print(f"Versión AXIA sincronizada: {APP_VERSION}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
