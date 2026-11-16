"""Reproduce the lecture examples from the Lab 4 and Lab 5 notebooks."""
from bplus import assert_valid, deletion_tree, find_leaf, lecture_tree, levels


def show(tree):
    for depth, layer in enumerate(levels(tree)):
        print(f"  level {depth}  " + " | ".join(str(list(page)) for page in layer))
    leaf = find_leaf(tree, float("-inf"))
    chain = []
    while leaf is not None:
        chain.append(str(leaf.keys))
        leaf = leaf.next
    print("  linked leaves  " + " <-> ".join(chain))


def task4(impl):
    search = impl["bplus_range"]
    insert = impl["bplus_insert"]

    tree = lecture_tree()
    leaf = find_leaf(tree, 20)
    print(f"4.1 Point search 20 lands in {leaf.keys}")
    print(f"4.1 Range 19 to 29 {list(search(tree, 19, 29))}")

    tree = lecture_tree()
    insert(tree, 15)
    assert_valid(tree)
    print(f"4.2 Insert 15 leaf {find_leaf(tree, 15).keys}")

    tree = lecture_tree()
    insert(tree, 6, "redistribute")
    assert_valid(tree)
    print(f"4.2 Insert 6 first separator {tree.root.keys[0]}")
    show(tree)

    tree = lecture_tree()
    insert(tree, 8, "split")
    assert_valid(tree)
    print(f"4.3 Insert 8 copied leaf key {find_leaf(tree, 8).keys[0]}")
    print(f"4.3 Insert 8 pushed root key {tree.root.keys[0]}")
    print(f"4.3 Insert 8 final leaf depth {len(levels(tree)) - 1}")
    show(tree)


def task5(impl):
    delete = impl["bplus_delete"]
    tree = deletion_tree()
    for key in (19, 20, 24):
        delete(tree, key)
        assert_valid(tree)
        print(f"After deleting {key}")
        show(tree)
        if key == 20:
            print(f"5.1 Receiver leaf {find_leaf(tree, 22).keys}")
            print(f"5.1 New separator {tree.root.children[1].keys[0]}")

    print(f"5.2 Merged leaf {find_leaf(tree, 22).keys}")
    print(f"5.2 Final root {tree.root.keys}")
    print(f"5.2 Final leaf depth {len(levels(tree)) - 1}")
    raw, stored, before, after = impl["prefix_page_stats"](
        ["robbed", "robbing", "robot"], 128, 16, 8, 12, 4
    )
    print(f"5.3 Raw and compressed key bytes {raw}, {stored}")
    print(f"5.3 Entries per page before and after {before}, {after}")
