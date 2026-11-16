"""Data and result shapes shared by the starter, tests and experiment runner."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    compressed_bytes: int
    minimum: int | None = None
    maximum: int | None = None


@dataclass(frozen=True)
class RowGroup:
    rows: int
    chunks: dict[str, Chunk]


@dataclass(frozen=True)
class ScanPlan:
    groups: tuple[int, ...]
    columns: tuple[str, ...]
    chunks: int
    compressed_bytes: int


@dataclass
class ISAM:
    separators: tuple[int, ...]
    primary: list[list[int]]
    overflow: list[list[list[int]]]
    capacity: int


@dataclass(frozen=True)
class RangeResult:
    keys: tuple[int, ...]
    pages: tuple[tuple[int, int], ...]
