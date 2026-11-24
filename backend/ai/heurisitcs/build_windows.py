import json
from pathlib import Path
from configs.settings import ROWS, COLS, H, DIRECTIONS

_CACHE_FILE = Path(__file__).with_name("windows.json")


def _build_windows() -> list[int]:
    wins = []
    for c in range(COLS):
        for r in range(ROWS):
            for dr, dc in DIRECTIONS:
                er, ec = r + 3 * dr, c + 3 * dc
                if 0 <= er < ROWS and 0 <= ec < COLS:
                    mask = 0
                    for i in range(4):
                        mask |= 1 << (H * (c + i * dc) + (r + i * dr))
                    wins.append(mask)
    return wins


def _load_windows() -> tuple[int, ...]:
    meta = {"rows": ROWS, "cols": COLS, "h": H}
    if _CACHE_FILE.exists():
        try:
            data = json.loads(_CACHE_FILE.read_text())
            if data.get("meta") == meta:
                return tuple(data["windows"])
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    windows = _build_windows()
    _CACHE_FILE.write_text(json.dumps({"meta": meta, "windows": windows}))
    return tuple(windows)


WINDOWS = _load_windows()
