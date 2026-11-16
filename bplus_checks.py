"""Public tests for the Lab 4 and Lab 5 B+ tree exercises."""
import unittest

from bplus import BPlusTree, assert_valid, branch, deletion_tree, find_leaf, lecture_tree, levels, linked_leaves


class InsertionTests(unittest.TestCase):
    def test_search_crosses_linked_leaves(self):
        tree = lecture_tree()
        search = self.implementation["bplus_range"]
        before = levels(tree)
        self.assertEqual(search(tree, 19, 29), (19, 20, 22, 24, 27, 29))
        self.assertEqual(search(tree, 13, 13), ())
        self.assertEqual(search(tree, 24, 24), (24,))
        self.assertEqual(levels(tree), before)
        assert_valid(tree)

    def test_search_empty_tree_and_reversed_range(self):
        search = self.implementation["bplus_range"]
        self.assertEqual(search(BPlusTree(), 0, 1), ())
        with self.assertRaises(ValueError):
            search(lecture_tree(), 20, 19)

    def test_simple_insertion_and_duplicate(self):
        tree = lecture_tree()
        put = self.implementation["bplus_insert"]
        self.assertIs(put(tree, 15), True)
        self.assertEqual(find_leaf(tree, 15).keys, [14, 15, 16])
        self.assertEqual(tree.root.keys, [13, 17, 24, 30])
        self.assertIs(put(tree, 15), False)
        assert_valid(tree)

    def test_insertion_redistributes_right(self):
        tree = lecture_tree()
        self.assertIs(self.implementation["bplus_insert"](tree, 6, "redistribute"), True)
        self.assertEqual(tree.root.keys, [7, 17, 24, 30])
        self.assertEqual(tree.root.children[0].keys, [2, 3, 5, 6])
        self.assertEqual(tree.root.children[1].keys, [7, 14, 16])
        assert_valid(tree)

    def test_insertion_redistributes_left_when_no_right_sibling(self):
        tree = lecture_tree()
        self.implementation["bplus_insert"](tree, 41, "redistribute")
        self.assertEqual(tree.root.keys, [13, 17, 24, 34])
        self.assertEqual(tree.root.children[-2].keys, [24, 27, 29, 33])
        self.assertEqual(tree.root.children[-1].keys, [34, 38, 39, 41])
        assert_valid(tree)

    def test_root_split_keeps_copy_up_in_leaf_and_pushes_middle(self):
        tree = lecture_tree()
        self.implementation["bplus_insert"](tree, 8, "split")
        self.assertEqual(levels(tree), (
            ((17,),),
            ((5, 13), (24, 30)),
            ((2, 3), (5, 7, 8), (14, 16), (19, 20, 22), (24, 27, 29), (33, 34, 38, 39)),
        ))
        assert_valid(tree)

    def test_redistribution_falls_back_to_split(self):
        leaves = linked_leaves([[1, 2, 3, 4], [10, 11, 12, 13]])
        tree = BPlusTree(branch([10], leaves))
        self.implementation["bplus_insert"](tree, 5, "redistribute")
        self.assertEqual(levels(tree), (((3, 10),), ((1, 2), (3, 4, 5), (10, 11, 12, 13))))
        assert_valid(tree)

    def test_first_split_and_invalid_strategy(self):
        tree = BPlusTree()
        put = self.implementation["bplus_insert"]
        with self.assertRaises(ValueError):
            put(tree, 9, "invalid")
        self.assertEqual(tree.root.keys, [])
        for key in (3, 1, 4, 2, 0):
            self.assertIs(put(tree, key), True)
        self.assertEqual(levels(tree), (((2,),), ((0, 1), (2, 3, 4))))
        assert_valid(tree)


class DeletionTests(unittest.TestCase):
    def test_missing_key_and_delete_without_underflow(self):
        tree = deletion_tree()
        remove = self.implementation["bplus_delete"]
        before = levels(tree)
        self.assertIs(remove(tree, 18), False)
        self.assertEqual(levels(tree), before)
        self.assertIs(remove(tree, 19), True)
        self.assertEqual(tree.root.children[1].keys, [24, 30])
        self.assertEqual(find_leaf(tree, 20).keys, [20, 22])
        assert_valid(tree)

    def test_borrow_from_right_updates_separator(self):
        tree = deletion_tree()
        remove = self.implementation["bplus_delete"]
        remove(tree, 19)
        remove(tree, 20)
        self.assertEqual(tree.root.children[1].keys, [27, 30])
        self.assertEqual(find_leaf(tree, 24).keys, [22, 24])
        self.assertEqual(find_leaf(tree, 27).keys, [27, 29])
        assert_valid(tree)

    def test_borrow_from_left(self):
        tree = BPlusTree(branch([10], linked_leaves([[1, 2, 3], [10, 12]])))
        self.assertIs(self.implementation["bplus_delete"](tree, 10), True)
        self.assertEqual(levels(tree), (((3,),), ((1, 2), (3, 12))))
        assert_valid(tree)

    def test_leaf_merge_cascades_and_shrinks_root(self):
        tree = deletion_tree()
        remove = self.implementation["bplus_delete"]
        for key in (19, 20, 24):
            self.assertIs(remove(tree, key), True)
            assert_valid(tree)
        self.assertEqual(levels(tree), (
            ((5, 13, 17, 30),),
            ((2, 3), (5, 7, 8), (14, 16), (22, 27, 29), (33, 34, 38, 39)),
        ))

    def test_merge_left_and_empty_root_leaf(self):
        tree = BPlusTree(branch([10], linked_leaves([[1, 2], [10, 12]])))
        remove = self.implementation["bplus_delete"]
        self.assertIs(remove(tree, 10), True)
        self.assertEqual(levels(tree), (((1, 2, 12),),))
        for key in (1, 12, 2):
            self.assertIs(remove(tree, key), True)
            assert_valid(tree)
        self.assertEqual(tree.root.keys, [])
        self.assertTrue(tree.root.leaf)

    def test_prefix_and_entries_match_lecture(self):
        stats = self.implementation["prefix_page_stats"]
        self.assertEqual(stats(["robbed", "robbing", "robot"], 128, 16, 8, 12, 4),
                         (18, 12, 5, 9))

    def test_prefix_is_character_based_but_sizes_are_utf8(self):
        stats = self.implementation["prefix_page_stats"]
        self.assertEqual(stats(["éclair", "élan"], 64, 8, 6, 10, 8), (12, 10, 3, 4))
        self.assertEqual(stats(["å", "ä"], 64, 8, 6, 10, 8), (4, 4, 3, 4))

    def test_empty_key_list_and_no_room_for_entries(self):
        self.assertEqual(self.implementation["prefix_page_stats"](
            [], 16, 16, 8, 12, 4), (0, 0, 0, 0))
