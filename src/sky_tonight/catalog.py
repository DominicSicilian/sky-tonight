"""Load the curated deep-sky / bright-star catalog and define solar-system bodies."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog" / "deep_sky.csv"

# Solar-system bodies to always evaluate. Keys are ephemeris target names in DE421.
PLANETS = [
    ("mercury", "Mercury", "planet"),
    ("venus", "Venus", "planet"),
    ("mars", "Mars", "planet"),
    ("jupiter barycenter", "Jupiter", "planet"),
    ("saturn barycenter", "Saturn", "planet"),
    ("uranus barycenter", "Uranus", "planet"),
    ("neptune barycenter", "Neptune", "planet"),
]


@dataclass
class FixedObject:
    id: str
    name: str
    type: str
    ra_hours: float
    dec_deg: float
    magnitude: float
    constellation: str
    note: str


def load_fixed_objects(path: Path | str = CATALOG_PATH) -> list[FixedObject]:
    objs: list[FixedObject] = []
    with open(path, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            objs.append(
                FixedObject(
                    id=row["id"].strip(),
                    name=row["name"].strip(),
                    type=row["type"].strip(),
                    ra_hours=float(row["ra_hours"]),
                    dec_deg=float(row["dec_deg"]),
                    magnitude=float(row["magnitude"]),
                    constellation=row["constellation"].strip(),
                    note=row["note"].strip(),
                )
            )
    return objs
