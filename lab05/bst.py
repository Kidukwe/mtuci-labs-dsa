"""Бинарное дерево поиска без дубликатов и автоматической балансировки."""

from __future__ import annotations

from collections import deque
from typing import Literal

Order = Literal["in", "pre", "post"]


class Node:
    """Узел с ключом и ссылками на левое и правое поддеревья."""

    __slots__ = ("key", "left", "right")

    def __init__(self, key: int) -> None:
        self.key = key
        self.left: Node | None = None
        self.right: Node | None = None


class BST:
    """Все ключи слева строго меньше ключа узла, а справа строго больше."""

    def __init__(self) -> None:
        self.root: Node | None = None
        self._size = 0

    def insert(self, key: int) -> None:
        """Вставить ключ без дублей. O(h + 1) времени, O(1) памяти."""
        parent = None
        node = self.root
        while node is not None:
            if key == node.key:
                return
            parent = node
            node = node.left if key < node.key else node.right

        leaf = Node(key)
        if parent is None:
            self.root = leaf
        elif key < parent.key:
            parent.left = leaf
        else:
            parent.right = leaf
        self._size += 1

    def search(self, key: int) -> bool:
        """Проверить наличие ключа. O(h + 1) времени и O(1) памяти."""
        node = self.root
        while node is not None:
            if key == node.key:
                return True
            node = node.left if key < node.key else node.right
        return False

    def delete(self, key: int) -> None:
        """Удалить ключ при наличии. O(h + 1) времени и O(1) памяти."""
        parent = None
        node = self.root
        while node is not None and node.key != key:
            parent = node
            node = node.left if key < node.key else node.right
        if node is None:
            return

        if node.left is not None and node.right is not None:
            successor_parent = node
            successor = node.right
            while successor.left is not None:
                successor_parent = successor
                successor = successor.left
            node.key = successor.key
            parent, node = successor_parent, successor

        child = node.left if node.left is not None else node.right
        if parent is None:
            self.root = child
        elif parent.left is node:
            parent.left = child
        else:
            parent.right = child
        self._size -= 1

    def in_order(self) -> list[int]:
        """Лево, узел, право. Возвращает ключи в возрастающем порядке."""
        return self._depth_first("in")

    def pre_order(self) -> list[int]:
        """Узел, лево, право. Корень поддерева записывается первым."""
        return self._depth_first("pre")

    def post_order(self) -> list[int]:
        """Лево, право, узел. Корень поддерева записывается последним."""
        return self._depth_first("post")

    def _depth_first(self, order: Order) -> list[int]:
        """Рекурсивный DFS. Θ(n) времени, O(h + 1) стека без результата."""
        result: list[int] = []

        def visit(node: Node | None) -> None:
            if node is None:
                return
            if order == "pre":
                result.append(node.key)
            visit(node.left)
            if order == "in":
                result.append(node.key)
            visit(node.right)
            if order == "post":
                result.append(node.key)

        try:
            visit(self.root)
        except RecursionError:
            return self._depth_first_iterative(order)
        return result

    def _depth_first_iterative(self, order: Order) -> list[int]:
        """Повторить DFS с явным стеком для дерева глубже лимита Python."""
        result: list[int] = []
        stack: list[tuple[Node | None, bool]] = [(self.root, False)]
        while stack:
            node, emit = stack.pop()
            if node is None:
                continue
            if emit:
                result.append(node.key)
                continue
            if order == "post":
                stack.append((node, True))
            stack.append((node.right, False))
            if order == "in":
                stack.append((node, True))
            stack.append((node.left, False))
            if order == "pre":
                stack.append((node, True))
        return result

    def level_order(self) -> list[int]:
        """BFS с очередью. Θ(n) времени, O(w) памяти без результата."""
        if self.root is None:
            return []

        result = []
        queue = deque([self.root])
        while queue:
            node = queue.popleft()
            result.append(node.key)
            if node.left is not None:
                queue.append(node.left)
            if node.right is not None:
                queue.append(node.right)
        return result

    def height(self) -> int:
        """Высота в рёбрах (−1 для пустого). Θ(n) времени, O(h + 1) памяти."""
        if self.root is None:
            return -1

        highest = 0
        stack = [(self.root, 0)]
        while stack:
            node, depth = stack.pop()
            highest = max(highest, depth)
            if node.right is not None:
                stack.append((node.right, depth + 1))
            if node.left is not None:
                stack.append((node.left, depth + 1))
        return highest

    def size(self) -> int:
        """Вернуть поддерживаемый счётчик узлов за Θ(1)."""
        return self._size
