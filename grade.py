"""Run the public tests. Use --task 1 through --task 5 to focus."""
import argparse
from copy import deepcopy
from pathlib import Path
import runpy
import sys
import unittest

import bplus_checks
from models import Chunk, ISAM, RangeResult, RowGroup, ScanPlan

ROOT = Path(__file__).resolve().parent


class PlannerTests(unittest.TestCase):
    def setUp(self):
        self.groups = [
            RowGroup(10, {"id": Chunk(9, 1, 10), "flag": Chunk(4, 0, 0), "price": Chunk(8)}),
            RowGroup(10, {"id": Chunk(12, 11, 20), "flag": Chunk(4, 1, 1), "price": Chunk(11)}),
            RowGroup(5, {"id": Chunk(7, None, 25), "flag": Chunk(3), "price": Chunk(6)}),
            RowGroup(0, {}),
        ]

    def assert_plan(self, projection, filters, expected):
        function = self.implementation["plan_scan"]
        arguments = (self.groups, projection, filters)
        before = deepcopy(arguments)
        self.assertEqual(function(*arguments), expected)
        self.assertEqual(arguments, before, "The planner changed its input")

    def test_projection_and_filter_union(self):
        self.assert_plan(["price", "id", "price"], {"id": (1, 10), "flag": (None, 1)},
                         ScanPlan((0, 2), ("price", "id", "flag"), 6, 37))

    def test_inclusive_boundaries(self):
        self.assert_plan(["price"], {"id": (10, 11)},
                         ScanPlan((0, 1, 2), ("price", "id"), 6, 53))

    def test_and_can_reject_on_second_column(self):
        self.assert_plan(["id"], {"id": (1, 20), "flag": (1, None)},
                         ScanPlan((1, 2), ("id", "flag"), 4, 26))

    def test_known_maximum_can_prune_with_missing_minimum(self):
        self.assert_plan([], {"id": (26, None)}, ScanPlan((), ("id",), 0, 0))

    def test_no_filter_and_zero_rows(self):
        self.assert_plan(["price"], {}, ScanPlan((0, 1, 2), ("price",), 3, 25))

    def test_empty_projection_still_reads_predicate(self):
        self.assert_plan([], {"id": (20, 20)}, ScanPlan((1, 2), ("id",), 2, 19))

    def test_empty_file(self):
        self.groups = []
        self.assert_plan(["price"], {"id": (0, 10)}, ScanPlan((), ("price", "id"), 0, 0))

    def test_zero_byte_chunk_counts(self):
        self.groups = [RowGroup(1, {"id": Chunk(0, 1, 1)})]
        self.assert_plan(["id"], {}, ScanPlan((0,), ("id",), 1, 0))


class CodecTests(unittest.TestCase):
    def assert_frame(self, values, frame):
        originals = list(values)
        actual = self.implementation["encode_page"](values)
        self.assertIsInstance(actual, bytes)
        self.assertEqual(actual, frame)
        self.assertEqual(values, originals, "The encoder changed its input")

    def test_empty(self):
        self.assert_frame([], bytes.fromhex("52 00 00"))

    def test_three_bit_values_cross_byte_boundary(self):
        self.assert_frame([5, 2, 7], bytes.fromhex("50 03 00 03 d5 01"))

    def test_tie_uses_packed_mode(self):
        self.assert_frame([1] * 9, bytes.fromhex("50 09 00 01 ff 01"))

    def test_rle_keeps_separated_runs(self):
        self.assert_frame([240] * 10 + [5] * 10 + [240] * 10,
                          bytes.fromhex("52 1e 00 f0 0a 00 05 0a 00 f0 0a 00"))

    def test_maximum_run_length(self):
        self.assert_frame([0] * 65535, bytes.fromhex("52 ff ff 00 ff ff"))

    def test_decode_packed_padding_and_order(self):
        self.assertEqual(self.implementation["decode_page"](bytes.fromhex("50 03 00 03 d5 01")),
                         [5, 2, 7])

    def test_decode_valid_rle_even_when_packed_is_smaller(self):
        self.assertEqual(self.implementation["decode_page"](bytes.fromhex("52 03 00 04 02 00 01 01 00")),
                         [4, 4, 1])

    def test_decode_empty_frames(self):
        for frame in ("52 00 00", "50 00 00 01"):
            with self.subTest(mode=frame[:2]):
                self.assertEqual(self.implementation["decode_page"](bytes.fromhex(frame)), [])

    def test_varied_round_trips(self):
        for values in ([0], [255], list(range(256)), [0, 3, 1, 2] * 20,
                       [4] * 30 + [3] * 30, [127, 1, 0] * 57):
            with self.subTest(length=len(values), max_value=max(values)):
                self.assertEqual(self.implementation["decode_page"](
                    self.implementation["encode_page"](values)), values)


class ISAMTests(unittest.TestCase):
    def setUp(self):
        self.index = ISAM((20, 40), [[3, 8], [20], [40, 55]], [[], [], []], 2)

    def test_fill_primary_at_separator(self):
        self.assertEqual(self.implementation["insert"](self.index, 20), (1, 0))
        self.assertEqual(self.index.primary, [[3, 8], [20, 20], [40, 55]])
        self.assertEqual(self.index.overflow, [[], [], []])

    def test_first_overflow_and_append(self):
        put = self.implementation["insert"]
        self.assertEqual(put(self.index, 18), (0, 1))
        self.assertEqual(put(self.index, 9), (0, 1))
        self.assertEqual(self.index.overflow, [[[18, 9]], [], []])

    def test_allocate_second_overflow_page(self):
        put = self.implementation["insert"]
        self.index.overflow[2] = [[49, 47]]
        self.assertEqual(put(self.index, 44), (2, 2))
        self.assertEqual(self.index.overflow[2], [[49, 47], [44]])
        self.assertEqual(self.index.separators, (20, 40))
        self.assertEqual(self.index.primary, [[3, 8], [20], [40, 55]])
        self.assertEqual(self.index.overflow[:2], [[], []])

    def test_scan_crosses_separator_and_preserves_duplicate_keys(self):
        self.index.overflow = [[[18, 14], [18]], [], [[48]]]
        before = deepcopy(self.index)
        actual = self.implementation["range_scan"](self.index, 18, 20)
        self.assertEqual(actual, RangeResult((18, 18, 20), ((0, 0), (0, 1), (0, 2), (1, 0))))
        self.assertEqual(self.index, before)

    def test_scan_does_not_stop_at_larger_overflow_key(self):
        self.index.overflow[0] = [[19, 11], [10]]
        self.assertEqual(self.implementation["range_scan"](self.index, 9, 12),
                         RangeResult((10, 11), ((0, 0), (0, 1), (0, 2))))

    def test_boundary_equality_visits_right_partition_only(self):
        self.assertEqual(self.implementation["range_scan"](self.index, 40, 40),
                         RangeResult((40,), ((2, 0),)))

    def test_empty_primary_still_read_for_its_range(self):
        self.index.primary[1] = []
        self.assertEqual(self.implementation["range_scan"](self.index, 27, 28),
                         RangeResult((), ((1, 0),)))

    def test_single_partition(self):
        index = ISAM((), [[4]], [[]], 1)
        self.assertEqual(self.implementation["insert"](index, -2), (0, 1))
        self.assertEqual(self.implementation["range_scan"](index, -3, 4),
                         RangeResult((-2, 4), ((0, 0), (0, 1))))

    def test_reversed_bounds(self):
        with self.assertRaises(ValueError):
            self.implementation["range_scan"](self.index, 10, 9)


TEST_CLASSES = {
    1: PlannerTests,
    2: CodecTests,
    3: ISAMTests,
    4: bplus_checks.InsertionTests,
    5: bplus_checks.DeletionTests,
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task", type=int, choices=TEST_CLASSES)
    parser.add_argument("--implementation", type=Path, default=ROOT / "lab.py",
                        help="Load an alternate implementation file")
    args = parser.parse_args()
    try:
        implementation = runpy.run_path(str(args.implementation.resolve()))
    except (OSError, SyntaxError, ImportError) as exc:
        parser.exit(1, f"Could not load {args.implementation.name}: {exc}\n")
    suite = unittest.TestSuite()
    for number in (args.task,) if args.task else TEST_CLASSES:
        case = TEST_CLASSES[number]
        case.implementation = implementation
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(case))
    return int(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())


if __name__ == "__main__":
    sys.exit(main())
