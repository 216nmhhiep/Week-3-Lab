"""Implement these functions using the contracts in README.md."""
from models import ISAM, RangeResult, RowGroup, ScanPlan


def plan_scan(
    groups: list[RowGroup],
    projection: list[str],
    filters: dict[str, tuple[int | None, int | None]],
) -> ScanPlan:
    """Build a scan plan for the projection and inclusive filter bounds."""
    raise NotImplementedError("Task 1: plan_scan")


def encode_page(values: list[int]) -> bytes:
    """Encode unsigned 8-bit values using the smaller specified frame."""
    raise NotImplementedError("Task 2: encode_page")


def decode_page(frame: bytes) -> list[int]:
    """Decode either valid page format."""
    raise NotImplementedError("Task 2: decode_page")


def insert(index: ISAM, key: int) -> tuple[int, int]:
    """Insert a key and return the page that received it."""
    raise NotImplementedError("Task 3: insert")


def range_scan(index: ISAM, low: int, high: int) -> RangeResult:
    """Return matching keys and the pages read for an inclusive range."""
    raise NotImplementedError("Task 3: range_scan")


def bplus_range(tree, low: int, high: int) -> tuple[int, ...]:
    """Return the keys in an inclusive range by following linked leaves."""
    raise NotImplementedError("Task 4: bplus_range")


def bplus_insert(tree, key: int, strategy: str = "split") -> bool:
    """Insert a unique key and apply the specified overflow policy."""
    raise NotImplementedError("Task 4: bplus_insert")


def bplus_delete(tree, key: int) -> bool:
    """Remove a key and repair leaf underflow."""
    raise NotImplementedError("Task 5: bplus_delete")


def prefix_page_stats(keys, page_bytes, header_bytes, pointer_bytes,
                      key_bytes_before, key_bytes_after):
    """Return (raw bytes, compressed bytes, entries before, entries after)."""
    raise NotImplementedError("Task 5: prefix_page_stats")
