#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЛР 2. Рекурсия, динамический массив, стек и дек — вариант 9.

Реализация и каркас проверки/замеров на основе заготовки курса:
https://github.com/mel0d1an/data-structures-and-algorithms
ФГБОУ ВО МТУСИ, кафедра «Программная инженерия», 2026, CC BY 4.0.
Заготовка дополнена реализациями, проверками, строгой сверкой паспорта
и сохранением результатов в JSON. См. README.md для запуска и анализа.
"""

from __future__ import annotations

import argparse
import collections
import functools
import gc
import hashlib
import json
import math
import platform
import random
import statistics
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Параметры эксперимента
# ---------------------------------------------------------------------------

#: Размеры структуры для замера операций у начала (вставка и удаление).
FRONT_SIZES = (1_000, 3_000, 10_000, 30_000, 100_000)

#: Операций у начала в одном замере: одна операция слишком быстра для таймера.
FRONT_OPS = 1_000

#: n для таблицы числа вызовов наивной и мемоизированной рекурсии.
FIB_NS = (5, 10, 15, 20, 25, 30)

REPEATS = 5  # повторов на точку (берётся медиана)

# ---------------------------------------------------------------------------
# 1. Рекурсивные функции (счётчик вызовов — для сравнения наивной рекурсии
#    и мемоизации; результаты счётчика включаются в отчёт)
# ---------------------------------------------------------------------------

CALLS = {"fib_naive": 0, "fib_memo": 0}  # счётчики рекурсивных вызовов


def factorial(n: int) -> int:
    """Факториал: Θ(n) арифметических операций и Θ(n) кадров стека."""
    if n < 0:
        raise ValueError("Входное число n должно быть >= 0.")
    if n == 0:
        return 1
    return n * factorial(n - 1)


def fib_naive(n: int) -> int:
    """Фибоначчи без кеша: Θ(φ**n) операций, Θ(n) кадров стека."""
    if n < 0:
        raise ValueError("Индекс n должен быть >= 0.")
    CALLS["fib_naive"] += 1
    if n < 2:
        return n
    return fib_naive(n - 1) + fib_naive(n - 2)


def fib_memo(n: int, memo: dict[int, int] | None = None) -> int:
    """Фибоначчи с общим кешем: ожидаемые Θ(n) время и Θ(n) ячеек памяти.

    Считаются все вызовы, включая попадания в кеш. Новый внешний вызов
    без memo получает новый словарь; рекурсивные вызовы используют его же.
    """
    if n < 0:
        raise ValueError("Индекс n должен быть >= 0.")
    CALLS["fib_memo"] += 1
    if memo is None:
        memo = {}
    if n in memo:
        return memo[n]
    if n < 2:
        memo[n] = n
    else:
        memo[n] = fib_memo(n - 1, memo) + fib_memo(n - 2, memo)
    return memo[n]


def hanoi(
    n: int,
    src: str = "A",
    dst: str = "C",
    aux: str = "B",
    moves: list[tuple[str, str]] | None = None,
) -> int:
    """Перенести n дисков; Θ(2**n) время, Θ(n) стек, Θ(2**n) запись ходов.

    В moves дописываются пары стержней; без списка возвращается только
    количество ходов. Во всех вызовах используется один и тот же список.
    """
    if n < 0:
        raise ValueError("Количество дисков должно быть >= 0.")
    if src == dst or src == aux or dst == aux:
        raise ValueError("Стержни должны иметь разные имена.")
    if n == 0:
        return 0
    before = hanoi(n - 1, src, aux, dst, moves)
    if moves is not None:
        moves.append((src, dst))
    after = hanoi(n - 1, aux, dst, src, moves)
    return before + 1 + after


# ---------------------------------------------------------------------------
# 2. Динамический массив с ручным управлением ёмкостью (рост x2)
# ---------------------------------------------------------------------------


class DynamicArray:
    """Собственный массив поверх списка фиксированной длины.

    0 <= size <= capacity; len(buffer) == capacity. Активные элементы
    занимают префикс [0, size), остальные ячейки содержат None.
    Ёмкость растёт вдвое, сжатие не реализовано (допускается КИМ-02).
    """

    INITIAL_CAPACITY = 4

    def __init__(self) -> None:
        self._capacity = self.INITIAL_CAPACITY
        self._size = 0
        self._buffer: list[object] = [None] * self._capacity
        self.copies = 0

    def __len__(self) -> int:
        return self._size

    @property
    def capacity(self) -> int:
        """Количество выделенных ячеек, включая свободные."""
        return self._capacity

    def _grow(self) -> None:
        """Удвоить ёмкость, сохранить порядок и учесть перенесённые ссылки."""
        new_capacity = self._capacity * 2
        new_buffer: list[object] = [None] * new_capacity
        for index in range(self._size):
            new_buffer[index] = self._buffer[index]
        self.copies += self._size
        self._buffer = new_buffer
        self._capacity = new_capacity

    def append(self, value: object) -> None:
        """
        Добавление: Θ(1) без роста, Θ(size) при росте, Θ(1)
        амортизированно.
        """
        if self._size == self._capacity:
            self._grow()
        self._buffer[self._size] = value
        self._size += 1

    def pop(self) -> object:
        """Удалить последний элемент за Θ(1); пустой массив — IndexError."""
        if self._size == 0:
            raise IndexError("Нельзя удалить элемент из пустого массива.")
        self._size -= 1
        value = self._buffer[self._size]
        # Освобождаем ссылку, но сохраняем выделенную ёмкость.
        self._buffer[self._size] = None
        return value

    def get(self, index: int) -> object:
        """Чтение за Θ(1); допускаются только индексы 0 <= index < size."""
        if not 0 <= index < self._size:
            raise IndexError("Индекс выходит за границы массива.")
        return self._buffer[index]

    def set(self, index: int, value: object) -> None:
        """Изменить существующий элемент за Θ(1), сохранив размер массива."""
        if not 0 <= index < self._size:
            raise IndexError("Индекс выходит за границы массива.")
        self._buffer[index] = value


# ---------------------------------------------------------------------------
# 3. Стек и дек на базе собственных структур
# ---------------------------------------------------------------------------


class Stack:
    """LIFO-стек; доступ к DynamicArray только через публичные методы."""

    def __init__(self) -> None:
        self._data = DynamicArray()

    def __len__(self) -> int:
        return len(self._data)

    def push(self, value: object) -> None:
        """Положить на вершину: Θ(1) амортизированно, Θ(n) при росте."""
        self._data.append(value)

    def pop(self) -> object:
        """Снять вершину за Θ(1); пустой стек — IndexError."""
        return self._data.pop()

    def peek(self) -> object:
        """Прочитать вершину за Θ(1), не меняя размер."""
        if len(self) == 0:
            raise IndexError("У пустого стека нет вершины.")
        return self._data.get(len(self) - 1)


class _Node:
    """Значение и две ссылки; __slots__ убирает словарь атрибутов узла."""

    __slots__ = ("value", "prev", "next")

    def __init__(
        self,
        value: object,
        prev: _Node | None = None,
        next_node: _Node | None = None,
    ) -> None:
        self.value = value
        self.prev = prev
        self.next = next_node


class Deque:
    """Дек на двусвязном списке: все операции концов Θ(1).

    У пустого дека обе крайние ссылки равны None. У непустого head.prev
    и tail.next равны None; соседние узлы ссылаются друг на друга.
    """

    def __init__(self) -> None:
        self._head: _Node | None = None
        self._tail: _Node | None = None
        self._size = 0

    def __len__(self) -> int:
        return self._size

    def push_front(self, value: object) -> None:
        """Добавить узел в начало за Θ(1)."""
        node = _Node(value, next_node=self._head)
        if self._head is None:
            self._tail = node
        else:
            self._head.prev = node
        self._head = node
        self._size += 1

    def push_back(self, value: object) -> None:
        """Добавить узел в конец за Θ(1)."""
        node = _Node(value, prev=self._tail)
        if self._tail is None:
            self._head = node
        else:
            self._tail.next = node
        self._tail = node
        self._size += 1

    def pop_front(self) -> object:
        """Удалить первый узел за Θ(1); пустой дек — IndexError."""
        if self._head is None:
            raise IndexError("Нельзя удалить элемент из пустого дека.")
        node = self._head
        self._head = node.next
        if self._head is None:
            self._tail = None
        else:
            self._head.prev = None
        node.next = None  # удалённый узел больше не удерживает соседей
        self._size -= 1
        return node.value

    def pop_back(self) -> object:
        """Удалить последний узел за Θ(1); пустой дек — IndexError."""
        if self._tail is None:
            raise IndexError("Нельзя удалить элемент из пустого дека.")
        node = self._tail
        self._tail = node.prev
        if self._tail is None:
            self._head = None
        else:
            self._tail.next = None
        node.prev = None
        self._size -= 1
        return node.value


# ---------------------------------------------------------------------------
# 4. Данные варианта: поиск каталога и загрузка
# ---------------------------------------------------------------------------

Op = tuple[
    str, int | None
]  # операция и её аргумент (None, если аргумента нет)


def find_data_dir(explicit: Path | None) -> Path:
    """
    Каталог с данными варианта: --data, либо data/generated рядом с
    работой.
    """
    if explicit is not None:
        if not explicit.is_dir():
            raise SystemExit(f"Каталог не найден: {explicit}")
        return explicit
    candidates = []
    for base in (Path.cwd(), Path(__file__).resolve().parent):
        for parent in (base, *base.parents):
            candidates.append(parent / "data" / "generated")
    for path in candidates:
        if path.is_dir():
            return path
    raise SystemExit(
        "Не найден каталог data/generated с данными варианта.\n"
        "Сгенерируйте данные из корня репозитория курса:\n"
        "    python scripts/generate_data.py --variant N --only ops\n"
        "или укажите каталог явно: --data <путь>"
    )


def check_variant(data_dir: Path, variant: int) -> None:
    """Без корректного паспорта нельзя считать данные данными варианта."""
    path = data_dir / "manifest.json"
    if not path.is_file():
        raise SystemExit(f"Нет паспорта {path}; сгенерируйте данные варианта.")
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if (
        manifest.get("variant") != variant
        or manifest.get("seed") != 30 + variant
    ):
        raise SystemExit(
            f"Паспорт не соответствует варианту "
            f"{variant} (seed={30 + variant})."
        )
    print(f"Данные варианта {variant} (seed={30 + variant}) из {data_dir}")


def read_data_lines(data_dir: Path, name: str) -> list[str]:
    """
    Строки файла данных варианта; при его отсутствии — подсказка, как
    создать.
    """
    path = data_dir / name
    if not path.is_file():
        raise SystemExit(
            f"Не найден файл данных: {path}\n"
            f"Сгенерируйте его: python scripts/generate_data.py "
            f"--variant <ваш вариант> --only ops"
        )
    return path.read_text(encoding="utf-8").splitlines()


def load_append_sizes(data_dir: Path) -> list[int]:
    """Размеры серий append из ops_append_sizes.txt."""
    return [
        int(line) for line in read_data_lines(data_dir, "ops_append_sizes.txt")
    ]


def load_ops(data_dir: Path, kind: str) -> list[Op]:
    """
    Операции из ops_<kind>.txt (kind — stack или deque): «push 17», «pop»,
    ...
    """
    ops: list[Op] = []
    for line in read_data_lines(data_dir, f"ops_{kind}.txt"):
        name, *arg = line.split()
        ops.append((name, int(arg[0]) if arg else None))
    return ops


# ---------------------------------------------------------------------------
# 5. Репрезентативные тесты и инварианты (шаги 1–3 методики верификации)
# ---------------------------------------------------------------------------


class SelfCheckError(Exception):
    """Нарушен контракт или инвариант реализации."""


def expect(condition: bool, message: str) -> None:
    """
    Явная проверка вместо assert: assert-ы исчезают при запуске python -O.
    """
    if not condition:
        raise SelfCheckError(message)


def expect_index_error(call, what: str) -> None:
    """call() должен бросить IndexError."""
    try:
        call()
    except IndexError:
        return
    raise SelfCheckError(f"{what}: ожидался IndexError")


# Операции над структурой — словарь «имя операции из данных -> метод»;
# ключ "len" нужен для сверки размера. Эталоны — list и collections.deque.


def stack_methods(st: Stack) -> dict:
    return {"push": st.push, "pop": st.pop, "peek": st.peek, "len": st.__len__}


def list_stack_methods(a: list) -> dict:
    return {
        "push": a.append,
        "pop": a.pop,
        "peek": lambda: a[-1],
        "len": a.__len__,
    }


def deque_methods(dq: Deque) -> dict:
    return {
        "push_front": dq.push_front,
        "push_back": dq.push_back,
        "pop_front": dq.pop_front,
        "pop_back": dq.pop_back,
        "len": dq.__len__,
    }


def std_deque_methods(d: collections.deque) -> dict:
    return {
        "push_front": d.appendleft,
        "push_back": d.append,
        "pop_front": d.popleft,
        "pop_back": d.pop,
        "len": d.__len__,
    }


def apply_op(methods: dict, op: str, arg: int | None):
    """Выполнить операцию; IndexError превращается в результат "IndexError"."""
    try:
        return methods[op]() if arg is None else methods[op](arg)
    except IndexError:
        return "IndexError"


def compare_with_reference(
    ops: list[Op], own: dict, ref: dict, label: str
) -> None:
    """
    Выполнить ops над своей структурой и эталоном, сверяя результат и
    размер.
    """
    for i, (op, arg) in enumerate(ops, start=1):
        call = op if arg is None else f"{op} {arg}"
        got, expected = apply_op(own, op, arg), apply_op(ref, op, arg)
        expect(
            got == expected,
            f"{label}, операция №{i} ({call}): "
            f"получено {got!r}, эталон {expected!r}",
        )
        expect(
            own["len"]() == ref["len"](),
            f"{label}, операция №{i} ({call}): len "
            f"= {own['len']()}, эталон {ref['len']()}",
        )


def random_ops(
    rng: random.Random,
    pushes: tuple[str, ...],
    others: tuple[str, ...],
    count: int,
    max_size: int,
) -> list[Op]:
    """
    Случайная серия операций над маленькой структурой — с частыми
    опустошениями.
    """
    ops: list[Op] = []
    size = 0
    for _ in range(count):
        op = rng.choice(pushes + others)
        if op in pushes and size >= max_size:
            op = rng.choice(others)
        if op in pushes:
            ops.append((op, rng.randrange(100)))
            size += 1
        else:
            ops.append((op, None))
            size = max(0, size - op.startswith("pop"))
    return ops


def expected_capacity(size: int) -> int:
    """Ёмкость после size подряд идущих append в пустой массив (рост x2)."""
    cap = DynamicArray.INITIAL_CAPACITY
    while cap < size:
        cap *= 2
    return cap


def expected_copies(size: int) -> int:
    """Число копирований после size подряд идущих append в пустой массив."""
    copies, cap = 0, DynamicArray.INITIAL_CAPACITY
    while cap < size:
        copies += cap
        cap *= 2
    return copies


def check_recursion() -> None:
    """
    Факториал, числа Фибоначчи со счётчиками вызовов, ходы Ханойских башен.
    """
    for n in range(21):
        got = factorial(n)
        expect(
            got == math.factorial(n),
            f"factorial({n}) = {got}, ожидалось {math.factorial(n)}",
        )

    fib = [0, 1]
    while len(fib) <= 90:
        fib.append(fib[-1] + fib[-2])
    for n in range(21):
        got = fib_naive(n)
        expect(got == fib[n], f"fib_naive({n}) = {got}, ожидалось {fib[n]}")
    CALLS["fib_naive"] = 0
    fib_naive(20)
    expect(
        CALLS["fib_naive"] >= fib[20],
        f"fib_naive(20): число вызовов "
        f"{CALLS['fib_naive']} — это не наивная рекурсия",
    )
    for n in (0, 1, 2, 10, 30, 90):
        CALLS["fib_memo"] = 0
        got = fib_memo(n)
        expect(got == fib[n], f"fib_memo({n}) = {got}, ожидалось {fib[n]}")
        expect(
            CALLS["fib_memo"] <= 2 * n + 1,
            f"fib_memo({n}): число вызовов "
            f"{CALLS['fib_memo']}, а с мемоизацией оно "
            f"не больше 2n + 1 = {2 * n + 1} — memo не передаётся в рекурсию?",
        )

    for n, (src, dst, aux) in (
        (0, "ACB"),
        (1, "ACB"),
        (2, "ACB"),
        (3, "XZY"),
        (6, "ACB"),
        (7, "PQR"),
    ):
        where = f"hanoi({n}, {src!r}, {dst!r}, {aux!r})"
        moves: list[tuple[str, str]] = []
        count = hanoi(n, src, dst, aux, moves)
        expect(
            count == 2**n - 1,
            f"{where} вернул {count}, ожидалось {2 ** n - 1}",
        )
        expect(
            len(moves) == count,
            f"{where}: записано ходов {len(moves)}, возвращено {count}",
        )
        towers = {src: list(range(n, 0, -1)), dst: [], aux: []}
        for k, move in enumerate(moves, start=1):
            expect(
                len(move) == 2
                and move[0] in towers
                and move[1] in towers
                and move[0] != move[1],
                f"{where}, ход {k}: {move!r} — не пара "
                f"разных стержней из {src}, {dst}, {aux}",
            )
            frm, to = move
            expect(bool(towers[frm]), f"{where}, ход {k}: стержень {frm} пуст")
            disk = towers[frm].pop()
            top = towers[to][-1] if towers[to] else None
            expect(
                top is None or top > disk,
                f"{where}, ход {k}: диск {disk} "
                f"кладётся на меньший диск {top}",
            )
            towers[to].append(disk)
        expect(
            towers[dst] == list(range(n, 0, -1)),
            f"{where}: после всех ходов на стержне {dst} лежит {towers[dst]}",
        )
        expect(
            hanoi(n, src, dst, aux) == count,
            f"{where} без moves вернул другое число",
        )


def check_dynamic_array() -> None:
    """
    Границы индексов, рост x2 (ёмкость и копирования), pop и допустимое
    сжатие.
    """
    initial = DynamicArray.INITIAL_CAPACITY
    arr = DynamicArray()
    expect(
        len(arr) == 0 and arr.capacity == initial,
        f"пустой массив: len = {len(arr)}, capacity = {arr.capacity}",
    )
    expect_index_error(lambda: arr.get(0), "get(0) пустого массива")
    expect_index_error(lambda: arr.set(0, 1), "set(0, 1) пустого массива")
    expect_index_error(arr.pop, "pop() пустого массива")

    ref: list[int] = []
    for i in range(100):  # проходим границы ёмкости 4, 8, 16, 32, 64
        arr.append(i * i)
        ref.append(i * i)
        size = len(ref)
        expect(len(arr) == size, f"после {size} append: len = {len(arr)}")
        expect(
            arr.capacity == expected_capacity(size),
            f"после {size} append: capacity = {arr.capacity}, ожидалось "
            f"{expected_capacity(size)} (расширение "
            f"x2 и только при size == capacity)",
        )
        expect(
            arr.copies == expected_copies(size),
            f"после {size} append: copies = {arr.copies}, "
            f"ожидалось {expected_copies(size)}",
        )
    for i, value in enumerate(ref):
        got = arr.get(i)
        expect(got == value, f"get({i}) = {got!r}, ожидалось {value!r}")
    arr.set(0, -1)
    arr.set(99, -99)
    ref[0], ref[99] = -1, -99
    expect(
        arr.get(0) == -1 and arr.get(99) == -99,
        "set(0, ...) или set(99, ...) не изменил элемент",
    )
    for bad in (100, arr.capacity - 1, arr.capacity, -1, -100):
        expect_index_error(
            lambda bad=bad: arr.get(bad), f"get({bad}) при size = 100"
        )
        expect_index_error(
            lambda bad=bad: arr.set(bad, 0), f"set({bad}, 0) при size = 100"
        )

    # pop до пустого, повторный рост и снова pop; сжатие, если есть, — только
    # на ¼
    for refill in (70, 0):
        while ref:
            cap_before = arr.capacity
            got, expected = arr.pop(), ref.pop()
            size = len(ref)
            expect(
                got == expected,
                f"pop() при size = {size + 1}: "
                f"{got!r}, ожидалось {expected!r}",
            )
            expect(
                len(arr) == size,
                f"после pop(): len = {len(arr)}, ожидалось {size}",
            )
            expect(
                arr.capacity == cap_before
                or (
                    arr.capacity == cap_before // 2
                    and size <= cap_before // 4
                    and arr.capacity >= initial
                ),
                f"pop() при size = {size + 1}: capacity "
                f"{cap_before} -> {arr.capacity}; "
                f"сжимать можно только вдвое, при size "
                f"<= capacity // 4 и не ниже {initial}",
            )
        expect_index_error(arr.pop, "pop() опустошённого массива")
        for i in range(refill):
            arr.append(i)
            ref.append(i)
            expect(
                len(arr) == len(ref) <= arr.capacity,
                f"повторный рост: len = {len(arr)}, capacity = {arr.capacity}",
            )
        for i, value in enumerate(ref):
            got = arr.get(i)
            expect(
                got == value,
                f"после повторного роста get({i}) "
                f"= {got!r}, ожидалось {value!r}",
            )


def check_stack() -> None:
    """LIFO через границы ёмкости, pop/peek пустого стека, сверка с list."""
    st = Stack()
    expect(len(st) == 0, f"пустой стек: len = {len(st)}")
    expect_index_error(st.pop, "pop() пустого стека")
    expect_index_error(st.peek, "peek() пустого стека")

    for start in (0, 100):  # второй проход — после опустошения
        values = list(
            range(start, start + 20)
        )  # 20 элементов: границы 4, 8 и 16
        for k, x in enumerate(values, start=1):
            st.push(x)
            top = st.peek()
            expect(
                top == x and len(st) == k,
                f"после push({x}): peek() = {top!r}, len = {len(st)}",
            )
        top = st.peek()
        expect(
            top == values[-1] and len(st) == len(values),
            "повторный peek() изменил стек",
        )
        for k, expected in enumerate(reversed(values), start=1):
            got = st.pop()
            expect(
                got == expected,
                f"pop() №{k}: {got!r}, ожидалось {expected!r} (LIFO)",
            )
            expect(
                len(st) == len(values) - k,
                f"после pop() №{k}: len = {len(st)}",
            )
        expect_index_error(st.pop, "pop() опустошённого стека")
        expect_index_error(st.peek, "peek() опустошённого стека")

    own, ref = Stack(), []
    ops = random_ops(
        random.Random(1), ("push",), ("pop", "peek"), count=3_000, max_size=40
    )
    compare_with_reference(
        ops,
        stack_methods(own),
        list_stack_methods(ref),
        "Stack против list, случайная серия",
    )


def check_deque() -> None:
    """
    Операции с обоих концов, опустошение и повторное наполнение, сверка с
    deque.
    """
    dq = Deque()
    expect(len(dq) == 0, f"пустой дек: len = {len(dq)}")
    expect_index_error(dq.pop_front, "pop_front() пустого дека")
    expect_index_error(dq.pop_back, "pop_back() пустого дека")

    # Все сочетания концов для одного элемента с повторным наполнением:
    # забытые head/tail при опустошении проявляются только так.
    pushes, pops = ("push_front", "push_back"), ("pop_front", "pop_back")
    for push1 in pushes:
        for pop1 in pops:
            for push2 in pushes:
                for pop2 in pops:
                    dq = Deque()
                    story = f"{push1}(1), {pop1}(), {push2}(2), {pop2}()"
                    getattr(dq, push1)(1)
                    first = getattr(dq, pop1)()
                    getattr(dq, push2)(2)
                    second = getattr(dq, pop2)()
                    expect(
                        (first, second, len(dq)) == (1, 2, 0),
                        f"{story}: извлечено {first!r} "
                        f"и {second!r}, len = {len(dq)}",
                    )
                    expect_index_error(
                        dq.pop_front, f"{story}, затем pop_front()"
                    )
                    expect_index_error(
                        dq.pop_back, f"{story}, затем pop_back()"
                    )

    own, ref = Deque(), collections.deque()
    ops = random_ops(random.Random(2), pushes, pops, count=5_000, max_size=12)
    compare_with_reference(
        ops,
        deque_methods(own),
        std_deque_methods(ref),
        "Deque против collections.deque, случайная серия",
    )


def check_variant_ops(stack_ops: list[Op], deque_ops: list[Op]) -> None:
    """
    Операции варианта: свой стек против list, свой дек против
    collections.deque.
    """
    compare_with_reference(
        stack_ops,
        stack_methods(Stack()),
        list_stack_methods([]),
        "ops_stack.txt",
    )
    compare_with_reference(
        deque_ops,
        deque_methods(Deque()),
        std_deque_methods(collections.deque()),
        "ops_deque.txt",
    )


def check_array_invariants(arr: DynamicArray) -> None:
    """Структурные проверки массива; свободные ячейки не удерживают объекты."""
    expect(0 <= len(arr) <= arr.capacity, "Нарушено size <= capacity")
    expect(len(arr._buffer) == arr.capacity, "Длина буфера != capacity")
    expect(
        all(value is None for value in arr._buffer[len(arr) :]),
        "Свободная ячейка удерживает объект",
    )


def check_deque_invariants(dq: Deque, expected: list[object]) -> None:
    """
    Проверить крайние ссылки, оба направления, размер и отсутствие циклов.
    """
    expect(len(dq) == len(expected), "Неверный размер дека")
    if not expected:
        expect(dq._head is None and dq._tail is None, "Пустой дек хранит узлы")
        return
    expect(
        dq._head is not None and dq._tail is not None, "Потерян крайний узел"
    )
    expect(
        dq._head.prev is None and dq._tail.next is None,
        "Неверные ссылки концов",
    )
    node, previous = dq._head, None
    for value in expected:
        expect(node is not None, "Список слишком короткий")
        expect(
            node.prev is previous and node.value == value,
            "Нарушена прямая связь",
        )
        previous, node = node, node.next
    expect(node is None and previous is dq._tail, "Лишний узел или цикл")
    node, following = dq._tail, None
    for value in reversed(expected):
        expect(node is not None, "Обратный список слишком короткий")
        expect(
            node.next is following and node.value == value,
            "Нарушена обратная связь",
        )
        following, node = node, node.prev
    expect(
        node is None and following is dq._head, "Лишний обратный узел или цикл"
    )


def check_own_invariants() -> None:
    """Свойства рекурсии, массива и двусвязного списка на граничных сериях."""
    for call in (factorial, fib_naive, fib_memo, hanoi):
        try:
            call(-1)
        except ValueError:
            pass
        else:
            raise SelfCheckError(f"{call.__name__} приняла отрицательный n")
    for n in range(16):
        CALLS["fib_naive"] = CALLS["fib_memo"] = 0
        value = fib_naive(n)
        next_value = fib_memo(n + 1)
        expect(
            CALLS["fib_naive"] == 2 * next_value - 1,
            "Неверная формула числа наивных вызовов",
        )
        CALLS["fib_memo"] = 0
        expect(fib_memo(n) == value, "Неверное значение Фибоначчи")
        expect(
            CALLS["fib_memo"] == (1 if n < 2 else 2 * n - 1),
            "Неверная формула числа вызовов с пустым кешем",
        )
    arr = DynamicArray()
    ref = []
    for value in (None, -1, 0, 0, "элемент", 7, 8, 9, 10):
        arr.append(value)
        ref.append(value)
        check_array_invariants(arr)
        expect(
            [arr.get(i) for i in range(len(arr))] == ref,
            "Потерян порядок массива",
        )
    while ref:
        expect(arr.pop() == ref.pop(), "Неверное удаление из массива")
        check_array_invariants(arr)
    dq, ref_deque = Deque(), collections.deque()
    methods = deque_methods(dq)
    reference = std_deque_methods(ref_deque)
    rng = random.Random(39)
    for _ in range(2_000):
        op = rng.choice(("push_front", "push_back", "pop_front", "pop_back"))
        arg = rng.choice((None, -1, 0, 1)) if op.startswith("push") else None
        # apply_op использует None как отсутствие аргумента; push(None)
        # проверяем отдельно.
        if op.startswith("push"):
            methods[op](arg)
            reference[op](arg)
        else:
            expect(
                apply_op(methods, op, None) == apply_op(reference, op, None),
                "Дек отличается от эталона",
            )
        check_deque_invariants(dq, list(ref_deque))


def self_check(stack_ops: list[Op], deque_ops: list[Op]) -> None:
    """Все проверки по разделам; при любой ошибке замеры не выполняются."""
    checks = (
        ("рекурсия", check_recursion),
        ("DynamicArray", check_dynamic_array),
        ("Stack", check_stack),
        ("Deque", check_deque),
        ("собственные инварианты", check_own_invariants),
        ("операции варианта", lambda: check_variant_ops(stack_ops, deque_ops)),
    )
    failed = 0
    print("self_check:")
    for name, check in checks:
        try:
            check()
        except NotImplementedError as err:
            where = traceback.extract_tb(err.__traceback__)[-1].name
            print(f"  {name}: не реализовано — {where} (TODO)")
            failed += 1
        except SelfCheckError as err:
            print(f"  {name}: ОШИБКА — {err}")
            failed += 1
        except (
            Exception
        ):  # noqa: BLE001 — падение реализации тоже результат проверки
            print(f"  {name}: ИСКЛЮЧЕНИЕ")
            traceback.print_exc(file=sys.stdout)
            failed += 1
        else:
            print(f"  {name}: OK")
    if failed:
        raise SystemExit(
            f"self_check: не пройдено разделов — {failed}; "
            f"замеры выполняются только после всех проверок."
        )
    print("self_check: OK")


# ---------------------------------------------------------------------------
# 6. Замеры (методика — docs/reproducibility.md)
# ---------------------------------------------------------------------------


def bench(call) -> float:
    """Прогрев + медиана пяти запусков; циклический GC вне замеров."""
    gc.collect()
    call()
    times = []
    for _ in range(REPEATS):
        gc_enabled = gc.isenabled()
        gc.disable()
        try:
            t0 = time.perf_counter()
            call()
            times.append(time.perf_counter() - t0)
        finally:
            if gc_enabled:
                gc.enable()
    return statistics.median(times)


def log_log_slope(points: list[tuple[int, float]]) -> float:
    """Наклон прямой в осях (log n, log t) — оценка показателя степени."""
    xs = [math.log10(n) for n, _ in points]
    ys = [math.log10(t) for _, t in points]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum(
        (x - mx) ** 2 for x in xs
    )


def appends(add, n: int) -> None:
    """n последовательных добавлений в конец."""
    for i in range(n):
        add(i)


def steady_ops(add, remove, k: int = FRONT_OPS) -> None:
    """k пар «добавить + удалить»: размер структуры не меняется."""
    for i in range(k):
        add(i)
        remove()


def replay(ops: list[Op], methods: dict) -> None:
    """Выполнить операции варианта без сверки — для замера."""
    for op, arg in ops:
        try:
            if arg is None:
                methods[op]()
            else:
                methods[op](arg)
        except IndexError:
            pass


def filled_structure(kind: str, n: int):
    """list, collections.deque или свой Deque из n элементов."""
    if kind == "list":
        return list(range(n))
    if kind == "deque":
        return collections.deque(range(n))
    dq = Deque()
    appends(dq.push_back, n)
    return dq


# : Операции у начала: подпись, тип структуры и пара методов (добавить,
# удалить).
#: Второй метод работает на другом конце и держит размер равным n.
FRONT_CASES = {
    "insert": (
        (
            "list.insert(0, x) + pop()",
            "list",
            lambda a: (functools.partial(a.insert, 0), a.pop),
        ),
        ("deque.appendleft + pop", "deque", lambda d: (d.appendleft, d.pop)),
        (
            "Deque.push_front + pop_back",
            "Deque",
            lambda d: (d.push_front, d.pop_back),
        ),
    ),
    "remove": (
        (
            "list.append + pop(0)",
            "list",
            lambda a: (a.append, functools.partial(a.pop, 0)),
        ),
        ("deque.append + popleft", "deque", lambda d: (d.append, d.popleft)),
        (
            "Deque.push_back + pop_front",
            "Deque",
            lambda d: (d.push_back, d.pop_front),
        ),
    ),
}
FRONT_TITLES = {"insert": "Вставка в начало", "remove": "Удаление из начала"}


def run_benchmarks(
    append_sizes: list[int], stack_ops: list[Op], deque_ops: list[Op]
) -> dict:
    """Замеры на данных варианта. Возвращает результаты для графиков."""
    results: dict = {"fibonacci": [], "replay": []}

    print("\nЧисло вызовов: наивная рекурсия против мемоизации")
    for n in FIB_NS:
        CALLS["fib_naive"] = CALLS["fib_memo"] = 0
        value = fib_naive(n)
        memo_value = fib_memo(n)
        expect(value == memo_value, f"Фибоначчи: несовпадение для n={n}")
        results["fibonacci"].append(
            {
                "n": n,
                "value": value,
                "naive_calls": CALLS["fib_naive"],
                "memo_calls": CALLS["fib_memo"],
            }
        )
        print(
            f"  n={n:>2}  F(n)={value:>6}  fib_naive: "
            f"{CALLS['fib_naive']:>7} вызовов"
            f"  fib_memo: {CALLS['fib_memo']:>2} вызовов"
        )

    print("\nСерии append на размерах варианта:")
    results["append"] = []
    for n in append_sizes:
        t_own = bench(lambda: appends(DynamicArray().append, n)) / n
        t_list = bench(lambda: appends([].append, n)) / n
        arr = DynamicArray()
        appends(arr.append, n)
        cost = (n + arr.copies) / n  # записи и копирования на одну операцию
        results["append"].append(
            (n, t_own, t_list, cost, arr.copies, arr.capacity)
        )
        print(
            f"  n={n:>7}  t/n: DynamicArray {t_own:.2e} c, list {t_list:.2e} c"
            f"  копирований {arr.copies:>7}  (n + копирования)/n = {cost:.3f}"
        )

    for key, title in FRONT_TITLES.items():
        print(
            f"\n{title}: время одной пары операций при размере n = "
            f"{', '.join(map(str, FRONT_SIZES))}"
        )
        results[key] = {}
        for label, kind, methods in FRONT_CASES[key]:
            points = []
            for n in FRONT_SIZES:
                add, remove = methods(filled_structure(kind, n))
                points.append(
                    (n, bench(lambda: steady_ops(add, remove)) / FRONT_OPS)
                )
            results[key][label] = points
            row = "  ".join(f"{t:.2e}" for _, t in points)
            print(f"  {label:28s} {row}   наклон {log_log_slope(points):.2f}")

    print("\nОперации варианта целиком: время на операцию")
    cases = (
        (
            "ops_stack.txt",
            stack_ops,
            "Stack",
            lambda: stack_methods(Stack()),
            "list",
            lambda: list_stack_methods([]),
        ),
        (
            "ops_deque.txt",
            deque_ops,
            "Deque",
            lambda: deque_methods(Deque()),
            "collections.deque",
            lambda: std_deque_methods(collections.deque()),
        ),
    )
    for name, ops, own_label, make_own, ref_label, make_ref in cases:
        t_own = bench(lambda: replay(ops, make_own())) / len(ops)
        t_ref = bench(lambda: replay(ops, make_ref())) / len(ops)
        results["replay"].append(
            {
                "file": name,
                "operations": len(ops),
                "own": own_label,
                "reference": ref_label,
                "own_seconds_per_op": t_own,
                "reference_seconds_per_op": t_ref,
            }
        )
        print(
            f"  {name}: {own_label} {t_own:.2e} c, {ref_label} {t_ref:.2e} c"
            f" — в {t_own / t_ref:.1f} раза медленнее"
        )
    return results


# ---------------------------------------------------------------------------
# 7. Графики
# ---------------------------------------------------------------------------


def plot_results(results: dict, out_dir: Path) -> None:
    """Два графика: серии append варианта и операции у начала (log-log)."""
    try:
        import matplotlib

        matplotlib.use("Agg")  # сохранение в файл без графической оболочки
        import matplotlib.pyplot as plt
    except ImportError:
        raise SystemExit(
            "Установите matplotlib: pip install -r requirements.txt"
        )

    rows = results["append"]
    ns = [row[0] for row in rows]
    fig, (ax_t, ax_c) = plt.subplots(1, 2, figsize=(12, 4.5))
    ax_t.plot(
        ns, [row[1] for row in rows], marker="o", label="DynamicArray.append"
    )
    ax_t.plot(ns, [row[2] for row in rows], marker="s", label="list.append")
    ax_t.set_xscale("log")
    ax_t.set_xlabel("число операций n")
    ax_t.set_ylabel("время на операцию t/n, с")
    ax_t.set_title("Средняя стоимость append")
    ax_t.grid(True, which="both", linewidth=0.3)
    ax_t.legend()
    ax_c.plot(
        ns, [row[3] for row in rows], marker="o", label="(n + копирования)/n"
    )
    ax_c.axhline(3, color="grey", linestyle="--", label="оценка методом учёта")
    ax_c.set_xscale("log")
    ax_c.set_ylim(0, 3.5)
    ax_c.set_xlabel("число операций n")
    ax_c.set_ylabel("записей и копирований на append")
    ax_c.set_title("DynamicArray: стоимость в элементарных действиях")
    ax_c.grid(True, which="both", linewidth=0.3)
    ax_c.legend(loc="lower right")
    fig.tight_layout()
    append_path = out_dir / "lab02_append.png"
    fig.savefig(append_path, dpi=150)
    plt.close(fig)

    fig2, axes = plt.subplots(1, 2, figsize=(12, 4.5), sharey=True)
    for ax, (key, title) in zip(axes, FRONT_TITLES.items()):
        for label, points in results[key].items():
            ax.plot(
                [n for n, _ in points],
                [t for _, t in points],
                marker="o",
                label=f"{label} (наклон ≈ {log_log_slope(points):.2f})",
            )
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlabel("размер структуры n")
        ax.set_title(title)
        ax.grid(True, which="both", linewidth=0.3)
        ax.legend(fontsize=8)
    axes[0].set_ylabel("время одной пары операций, с")
    fig2.tight_layout()
    front_path = out_dir / "lab02_front.png"
    fig2.savefig(front_path, dpi=150)
    plt.close(fig2)

    print(f"\nГрафики сохранены:\n  {append_path}\n  {front_path}")


# ---------------------------------------------------------------------------


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument(
        "--variant", type=int, required=True, help="номер варианта"
    )
    ap.add_argument(
        "--data",
        type=Path,
        default=None,
        help="каталог с данными варианта (по умолчанию ищется data/generated)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=Path(__file__).resolve().parent / "reports",
        help="каталог графиков и JSON-результатов",
    )
    ap.add_argument(
        "--check-only", action="store_true", help="только проверки"
    )
    args = ap.parse_args()
    if args.variant < 1:
        ap.error("номер варианта должен быть положительным")

    data_dir = find_data_dir(args.data)
    check_variant(data_dir, args.variant)
    append_sizes = load_append_sizes(data_dir)
    stack_ops = load_ops(data_dir, "stack")
    deque_ops = load_ops(data_dir, "deque")

    self_check(stack_ops, deque_ops)
    if args.check_only:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    results = run_benchmarks(append_sizes, stack_ops, deque_ops)
    results["metadata"] = {
        "variant": args.variant,
        "seed": 30 + args.variant,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "repeats": REPEATS,
        "warmup": 1,
        "front_pairs_per_repeat": FRONT_OPS,
        "gc_disabled_during_timing": True,
        "sha256": {
            path.name: hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(data_dir.iterdir())
            if path.name
            in {
                "manifest.json",
                "ops_append_sizes.txt",
                "ops_stack.txt",
                "ops_deque.txt",
            }
        },
    }
    result_path = args.out / "results.json"
    result_path.write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_results(results, args.out)
    print(f"Результаты сохранены: {result_path}")


if __name__ == "__main__":
    main()
