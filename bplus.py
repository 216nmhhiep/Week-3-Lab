"""B+ tree fixtures, navigation and internal node maintenance for Labs 4 and 5.

The lecture tree uses d=2, so a nonroot node holds two to four keys.
Separators are routing fences, including fences that no longer match a live key.
"""
from bisect import bisect_right
from dataclasses import dataclass, field

MIN_KEYS = 2
MAX_KEYS = 4


@dataclass(eq=False)
class Node:
    leaf: bool = True
    keys: list[int] = field(default_factory=list)
    children: list["Node"] = field(default_factory=list)
    parent: "Node | None" = None
    prev: "Node | None" = None
    next: "Node | None" = None


@dataclass
class BPlusTree:
    root: Node = field(default_factory=Node)


def branch(keys, children):
    """Create an internal page and assign its children's parent pointers."""
    node = Node(leaf=False, keys=list(keys), children=list(children))
    for child in node.children:
        child.parent = node
    return node


def linked_leaves(groups):
    """Build a chain of fresh leaf pages for a fixture."""
    leaves = [Node(keys=list(keys)) for keys in groups]
    for left, right in zip(leaves, leaves[1:]):
        left.next = right
        right.prev = left
    return leaves


def lecture_tree():
    """The Lab 4 starting tree. Nonmatching separators are lecture fences."""
    leaves = linked_leaves([[2, 3, 5, 7], [14, 16], [19, 20, 22],
                            [24, 27, 29], [33, 34, 38, 39]])
    return BPlusTree(branch([13, 17, 24, 30], leaves))


def deletion_tree():
    """The Lab 5 starting tree, independently built from the insert-8 example."""
    leaves = linked_leaves([[2, 3], [5, 7, 8], [14, 16], [19, 20, 22],
                            [24, 27, 29], [33, 34, 38, 39]])
    left = branch([5, 13], leaves[:3])
    right = branch([24, 30], leaves[3:])
    return BPlusTree(branch([17], [left, right]))


def find_leaf(tree, key):
    node = tree.root
    while not node.leaf:
        node = node.children[bisect_right(node.keys, key)]
    return node


def siblings(node):
    """Return (parent, child_index, left sibling, right sibling)."""
    parent = node.parent
    if parent is None:
        return None, 0, None, None
    slot = parent.children.index(node)
    left = parent.children[slot - 1] if slot else None
    right = parent.children[slot + 1] if slot + 1 < len(parent.children) else None
    return parent, slot, left, right


def link_after(left, right):
    """Insert a new leaf after left in the doubly linked chain."""
    right.prev = left
    right.next = left.next
    if left.next is not None:
        left.next.prev = right
    left.next = right


def unlink(leaf):
    """Detach one leaf and connect its two neighbours."""
    if leaf.prev is not None:
        leaf.prev.next = leaf.next
    if leaf.next is not None:
        leaf.next.prev = leaf.prev
    leaf.prev = leaf.next = None


def insert_parent(tree, left, separator, right):
    """Add a split's new right child and propagate internal overflow."""
    parent = left.parent
    if parent is None:
        tree.root = branch([separator], [left, right])
        return

    slot = parent.children.index(left)
    parent.children.insert(slot + 1, right)
    right.parent = parent
    parent.keys.insert(slot, separator)
    if len(parent.keys) > MAX_KEYS:
        middle = len(parent.keys) // 2
        pushed = parent.keys[middle]
        new_right = branch(parent.keys[middle + 1:], parent.children[middle + 1:])
        parent.keys = parent.keys[:middle]
        parent.children = parent.children[:middle + 1]
        insert_parent(tree, parent, pushed, new_right)


def repair_internal(tree, node):
    """Restore internal occupancy after a merge, including shrinking the root."""
    while True:
        if node is tree.root:
            if not node.leaf and not node.keys:
                tree.root = node.children[0]
                tree.root.parent = None
            return
        if len(node.keys) >= MIN_KEYS:
            return

        parent, slot, left, right = siblings(node)
        if right is not None and len(right.keys) > MIN_KEYS:
            node.keys.append(parent.keys[slot])
            parent.keys[slot] = right.keys.pop(0)
            child = right.children.pop(0)
            node.children.append(child)
            child.parent = node
            return
        if left is not None and len(left.keys) > MIN_KEYS:
            node.keys.insert(0, parent.keys[slot - 1])
            parent.keys[slot - 1] = left.keys.pop()
            child = left.children.pop()
            node.children.insert(0, child)
            child.parent = node
            return

        if right is not None:
            node.keys.extend([parent.keys.pop(slot), *right.keys])
            for child in right.children:
                child.parent = node
            node.children.extend(right.children)
            del parent.children[slot + 1]
        else:
            left.keys.extend([parent.keys.pop(slot - 1), *node.keys])
            for child in node.children:
                child.parent = left
            left.children.extend(node.children)
            del parent.children[slot]
        node = parent


def levels(tree):
    """Snapshot each level from root to leaves, in left-to-right page order."""
    layer = [tree.root]
    result = []
    while layer:
        result.append(tuple(tuple(node.keys) for node in layer))
        layer = [child for node in layer for child in node.children]
    return tuple(result)


def assert_valid(tree):
    """Raise AssertionError if occupancy, routing or the leaf list is broken."""
    seen = set()
    chain = []
    depths = set()

    def visit(node, parent, depth, low, high):
        assert node not in seen, "Page is linked into the tree more than once"
        seen.add(node)
        assert node.parent is parent, "Incorrect parent pointer"
        minimum = (0 if node.leaf else 1) if parent is None else MIN_KEYS
        assert minimum <= len(node.keys) <= MAX_KEYS, "Node occupancy violated"
        assert node.keys == sorted(set(node.keys)), "Node keys must be strictly increasing"
        assert all((low is None or low <= key) and (high is None or key < high)
                   for key in node.keys), "Key is outside its routing bounds"
        if node.leaf:
            assert not node.children, "Leaf has child pointers"
            chain.append(node)
            depths.add(depth)
            return
        assert len(node.children) == len(node.keys) + 1, "Wrong number of child pointers"
        bounds = [low, *node.keys, high]
        for slot, child in enumerate(node.children):
            visit(child, node, depth + 1, bounds[slot], bounds[slot + 1])

    visit(tree.root, None, 0, None, None)
    assert len(depths) == 1, "Leaves at different depths"
    for slot, leaf in enumerate(chain):
        assert leaf.prev is (chain[slot - 1] if slot else None), "Broken prev link"
        assert leaf.next is (chain[slot + 1] if slot + 1 < len(chain) else None), "Broken next link"
