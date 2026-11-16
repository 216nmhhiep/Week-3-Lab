"""Print fixed written results for one task using the supplied fixtures."""
import argparse
import csv
from pathlib import Path
import runpy

from bplus_experiments import task4, task5
from models import Chunk, ISAM, RowGroup

ROOT = Path(__file__).resolve().parent


def parquet_groups(path):
    import pyarrow.parquet as pq

    parquet = pq.ParquetFile(path)
    groups = []
    for group_id in range(parquet.num_row_groups):
        group = parquet.metadata.row_group(group_id)
        chunks = {}
        for column_id in range(group.num_columns):
            column = group.column(column_id)
            stats = column.statistics
            bounds = (stats.min, stats.max) if stats and stats.has_min_max else (None, None)
            chunks[column.path_in_schema] = Chunk(column.total_compressed_size, *bounds)
        groups.append(RowGroup(group.num_rows, chunks))
    return groups


def task1(impl):
    groups = parquet_groups(ROOT / "data/sales.parquet")
    plan = impl["plan_scan"]
    query_a = plan(groups, ["amount"], {"order_id": (1950, 2050)})
    query_b = plan(groups, ["category", "quantity"], {"order_id": (4001, 4150),
                                                       "quantity": (3, None)})
    for label, result in [("A", query_a), ("B", query_b)]:
        print(f"Query {label} groups {result.groups}, compressed bytes {result.compressed_bytes}")
    full = plan(groups, ["amount", "order_id"], {})
    print(f"Query A bytes skipped {full.compressed_bytes - query_a.compressed_bytes}")


def sales_rows():
    with (ROOT / "data/sales.csv").open(newline="", encoding="utf-8") as file:
        return list(csv.DictReader(file))


def task2(impl):
    rows = sales_rows()
    encode = impl["encode_page"]
    decode = impl["decode_page"]
    layouts = [("CSV order", rows), (
        "Sorted by quantity",
        sorted(rows, key=lambda row: (int(row["quantity"]), int(row["order_id"]))),
    )]

    print(f"{'Layout':20} {'Frame bytes':>12} {'R pages':>8} {'P pages':>8} {'Page reads':>11}")
    for name, layout in layouts:
        quantities = [int(row["quantity"]) for row in layout]
        frame_bytes = rle = packed = reads = 0
        for start in range(0, len(quantities), 128):
            page = quantities[start:start + 128]
            frame = encode(page)
            if decode(frame) != page or frame[:1] not in (b"R", b"P"):
                raise ValueError(f"Invalid round trip for {name} page {start // 128}")
            frame_bytes += len(frame)
            rle += frame[:1] == b"R"
            packed += frame[:1] == b"P"
            reads += name == "CSV order" or min(page) <= 3 <= max(page)
        print(f"{name:20} {frame_bytes:12,} {rle:8} {packed:8} {reads:11}")


def task3(impl):
    source_keys = {int(row["order_id"]) for row in sales_rows()}
    index = ISAM((40, 80), [[10, 20], [40, 50], [80, 90]], [[], [], []], 2)
    added = (25, 37, 35)
    for key in (10, 20, 40, 50, 80, 90, *added):
        if key not in source_keys:
            raise ValueError(f"Missing source order {key}")
    for key in added:
        location = impl["insert"](index, key)
        if key == 35:
            print(f"Page allocated for order 35 {location}")
    scan = impl["range_scan"](index, 35, 40)
    print(f"Matching keys {scan.keys}")
    print(f"Data pages read {len(scan.pages)}")


def main():
    tasks = {1: task1, 2: task2, 3: task3, 4: task4, 5: task5}
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=int, choices=tasks, required=True)
    parser.add_argument("--implementation", type=Path, default=ROOT / "lab.py",
                        help="Load an alternate implementation file")
    args = parser.parse_args()
    try:
        tasks[args.task](runpy.run_path(str(args.implementation.resolve())))
    except NotImplementedError as exc:
        parser.exit(1, f"Finish {exc} in lab.py and pass its checks first.\n")


if __name__ == "__main__":
    main()
