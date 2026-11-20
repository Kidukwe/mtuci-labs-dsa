import random
import subprocess
import sys
from pathlib import Path

import pytest
from bst import BST


def make_tree(keys) -> BST:
    tree = BST()
    for key in keys:
        tree.insert(key)
    return tree


@pytest.mark.parametrize(
    "keys, deleted, expected",
    [
        ([], 1, []),
        ([5], 5, []),
        ([5, 2], 5, [2]),
        ([5, 8], 5, [8]),
        ([5, 2, 1], 2, [5, 1]),
        ([5, 8, 9], 8, [5, 9]),
        ([5, 2, 8], 2, [5, 8]),
        ([5, 2, 8], 8, [5, 2]),
        ([5, 2, 8, 9], 5, [8, 2, 9]),
        ([50, 30, 80, 60, 90, 55, 57], 50, [55, 30, 80, 60, 90, 57]),
        ([50, 30, 80, 60, 90, 65], 80, [50, 30, 90, 60, 65]),
        ([5, 2, 8], 7, [5, 2, 8]),
    ],
)
def test_delete_updates_links_and_count(keys, deleted, expected):
    tree = make_tree(keys)
    tree.delete(deleted)
    assert tree.level_order() == expected
    assert tree.in_order() == sorted(set(keys) - {deleted})
    assert tree.size() == len(expected)
    assert not tree.search(deleted)


def test_duplicate_and_key_zero():
    tree = make_tree([0, -1, 1, 0, -1])
    assert tree.size() == 3
    assert tree.in_order() == [-1, 0, 1]
    tree.delete(0)
    tree.delete(0)
    assert tree.in_order() == [-1, 1]
    assert tree.size() == 2


@pytest.mark.parametrize("order", ["in_order", "pre_order", "post_order"])
@pytest.mark.parametrize("descending", [False, True])
def test_traversal_on_chain_exceeding_recursion_limit(order, descending):
    n = sys.getrecursionlimit() + 10
    keys = sorted(range(n), reverse=descending)
    tree = make_tree(keys)
    assert tree.height() == n - 1
    assert tree.size() == n
    expected = {
        "in_order": list(range(n)),
        "pre_order": keys,
        "post_order": keys[::-1],
    }
    assert getattr(tree, order)() == expected[order]
    tree.delete(keys[-1])
    assert tree.height() == n - 2


def test_operations_against_set_on_mixed_commands():
    rng = random.Random(39)
    tree = BST()
    reference = set()
    for _ in range(1_500):
        key = rng.randint(-100, 100)
        operation = rng.randrange(3)
        if operation == 0:
            tree.insert(key)
            reference.add(key)
        elif operation == 1:
            tree.delete(key)
            reference.discard(key)
        else:
            assert tree.search(key) == (key in reference)
        assert tree.in_order() == sorted(reference)
        assert tree.size() == len(reference)


@pytest.mark.parametrize("optimized", [False, True])
def test_check_only_cli(optimized):
    script = Path(__file__).with_name("lab05-bst-starter.py")
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(script), "--variant", "9", "--check-only"])
    result = subprocess.run(
        command, check=True, capture_output=True, text=True
    )
    assert "self_check: OK" in result.stdout
