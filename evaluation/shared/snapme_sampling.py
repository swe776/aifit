# Read the 184 SNAPMe photographs that the food evaluations use
import csv

from paths import DATA_DIRECTORY

MANIFEST_PATH = (
    DATA_DIRECTORY / "manifests" / "snapme_food_sample.csv"
)
SNAPME_PHOTOS_FOLDER = DATA_DIRECTORY / "snapme_photos"


def read_snapme_sample() -> list[dict]:
    with MANIFEST_PATH.open(encoding="utf-8-sig", newline="") as handle:
        manifest = list(csv.DictReader(handle))

    missing = [
        row["filename"]
        for row in manifest
        if not (SNAPME_PHOTOS_FOLDER / row["filename"]).is_file()
    ]

    # Stop straight away when a photograph is missing
    if missing:
        raise SystemExit(
            f"{len(missing)} of the {len(manifest)} SNAPMe photographs are missing from {SNAPME_PHOTOS_FOLDER}."
        )

    return [
        {
            "filename": row["filename"],
            "image_path": SNAPME_PHOTOS_FOLDER / row["filename"],
        }
        for row in manifest
    ]
