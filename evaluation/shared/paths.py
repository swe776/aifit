# Find the project folders so every evaluation script can be run from the project folder
import sys
from pathlib import Path


EVALUATION_DIRECTORY = Path(__file__).resolve().parent.parent

# The evaluation is split into models, logic, parameters and objectives like Chapter 5
LEVEL_DIRECTORIES = [
    EVALUATION_DIRECTORY / name
    for name in ("shared", "model", "logic", "parameters", "objectives")
]

DATA_DIRECTORY = EVALUATION_DIRECTORY / "data"
RESULTS_DIRECTORY = EVALUATION_DIRECTORY / "results"


def find_project_root(start: Path | None = None) -> Path:
    start = start or EVALUATION_DIRECTORY

    for candidate in (start, *start.parents):
        if (candidate / "backend" / "app").is_dir():
            return candidate

    raise RuntimeError(
        "Could not find the project root with backend/app."
    )


# The project folder is the one that holds backend/app
PROJECT_ROOT = find_project_root()


# Let the scripts use the app code and each other's helpers
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

for _level in LEVEL_DIRECTORIES:
    if _level.is_dir() and str(_level) not in sys.path:
        sys.path.insert(0, str(_level))


# Turn a path saved in a data file into a real file path on this computer
def resolve_data_path(stored_path: str | Path) -> Path:
    cleaned = str(stored_path).replace("\\", "/").strip()
    candidate = Path(cleaned)

    if candidate.is_absolute():
        return candidate

    from_root = PROJECT_ROOT / candidate

    if from_root.exists():
        return from_root

    parts = [part for part in candidate.parts if part not in (".", "")]

    if parts and parts[0] == "evaluation":
        parts = parts[1:]

    return EVALUATION_DIRECTORY.joinpath(*parts)


