"""Дополнительные проверки ЛР 2; запускаются также под python -O."""

import collections
import gc
import importlib.util
import json
import random
import subprocess
import sys
import weakref
from pathlib import Path

import pytest

LAB_PATH = Path(__file__).with_name("lab02-recursion-structures-starter.py")
SPEC = importlib.util.spec_from_file_location("lab02", LAB_PATH)
LAB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB)


@pytest.mark.parametrize("n, expected", [(0, 1), (1, 1), (2, 2), (5, 120)])
def test_factorial(n, expected):
    LAB.expect(LAB.factorial(n) == expected, "Неверный факториал")


@pytest.mark.parametrize(
    "function", [LAB.factorial, LAB.fib_naive, LAB.fib_memo, LAB.hanoi]
)
def test_negative_arguments(function):
    with pytest.raises(ValueError):
        function(-1)


def test_cold_and_warm_fibonacci_cache():
    memo = {}
    LAB.CALLS["fib_memo"] = 0
    LAB.expect(LAB.fib_memo(30, memo) == 832040, "Неверное F(30)")
    LAB.expect(LAB.CALLS["fib_memo"] == 59, "Неверное число холодных вызовов")
    LAB.CALLS["fib_memo"] = 0
    LAB.expect(LAB.fib_memo(30, memo) == 832040, "Неверный ответ из кеша")
    LAB.expect(
        LAB.CALLS["fib_memo"] == 1, "Повторно вычислено готовое значение"
    )
    LAB.CALLS["fib_memo"] = 0
    LAB.fib_memo(30)
    LAB.expect(LAB.CALLS["fib_memo"] == 59, "Кеш утёк между внешними вызовами")


@pytest.mark.parametrize("n", [0, 1, 2, 3, 7, 10])
def test_hanoi_moves(n):
    moves = []
    count = LAB.hanoi(n, "левый", "правый", "средний", moves)
    LAB.expect(count == len(moves) == 2**n - 1, "Неверное число ходов")
    towers = {
        "левый": list(range(n, 0, -1)),
        "правый": [],
        "средний": [],
    }
    for source, destination in moves:
        LAB.expect(bool(towers[source]), "Ход с пустого стержня")
        disk = towers[source].pop()
        LAB.expect(
            not towers[destination] or towers[destination][-1] > disk,
            "Большой диск положен на маленький",
        )
        towers[destination].append(disk)
    LAB.expect(
        towers["правый"] == list(range(n, 0, -1)), "Диски не перенесены"
    )


def test_hanoi_appends_to_supplied_log():
    moves = [("старый", "ход")]
    count = LAB.hanoi(2, moves=moves)
    LAB.expect(moves[0] == ("старый", "ход"), "Журнал ходов перезаписан")
    LAB.expect(len(moves) == count + 1, "Ходы не дописаны в исходный список")
    with pytest.raises(ValueError):
        LAB.hanoi(1, "A", "A", "B")


def test_array_amortized_bound_for_every_prefix():
    arr = LAB.DynamicArray()
    for n in range(1, 10_001):
        arr.append(n)
        LAB.expect(n + arr.copies < 3 * n, "Превышен бюджет метода учёта")
        LAB.expect(arr.get(n - 1) == n, "Последний элемент потерян")


def test_removed_array_element_is_not_retained():
    class Payload:
        pass

    arr = LAB.DynamicArray()
    value = Payload()
    reference = weakref.ref(value)
    arr.append(value)
    del value
    removed = arr.pop()
    LAB.expect(reference() is removed, "Удалён другой объект")
    del removed
    gc.collect()
    LAB.expect(reference() is None, "Массив удерживает удалённый объект")


@pytest.mark.parametrize("seed", [0, 9, 39])
def test_mixed_array_operations(seed):
    rng = random.Random(seed)
    arr, reference = LAB.DynamicArray(), []
    for _ in range(5_000):
        operation = rng.choice(("append", "pop", "get", "set"))
        if operation == "append":
            value = rng.choice((None, -10, 0, 7, "значение"))
            arr.append(value)
            reference.append(value)
        elif operation == "pop":
            if reference:
                LAB.expect(arr.pop() == reference.pop(), "Неверный pop")
            else:
                with pytest.raises(IndexError):
                    arr.pop()
        else:
            index = rng.randrange(-1, len(reference) + 2)
            if not 0 <= index < len(reference):
                with pytest.raises(IndexError):
                    if operation == "get":
                        arr.get(index)
                    else:
                        arr.set(index, 42)
            elif operation == "get":
                LAB.expect(arr.get(index) == reference[index], "Неверный get")
            else:
                arr.set(index, 42)
                reference[index] = 42
        LAB.check_array_invariants(arr)
        LAB.expect(
            [arr.get(i) for i in range(len(arr))] == reference,
            "Состояние массива отличается от list",
        )


@pytest.mark.parametrize("seed", [0, 9, 39])
def test_deque_links_after_mixed_operations(seed):
    rng = random.Random(seed)
    dq, reference = LAB.Deque(), collections.deque()
    for _ in range(2_000):
        operation = rng.choice(
            ("push_front", "push_back", "pop_front", "pop_back")
        )
        if operation.startswith("push"):
            value = rng.choice((None, -1, 0, "значение"))
            getattr(dq, operation)(value)
            if operation == "push_front":
                reference.appendleft(value)
            else:
                reference.append(value)
        elif reference:
            expected = (
                reference.popleft()
                if operation == "pop_front"
                else reference.pop()
            )
            LAB.expect(
                getattr(dq, operation)() == expected, "Неверный pop дека"
            )
        else:
            with pytest.raises(IndexError):
                getattr(dq, operation)()
        LAB.check_deque_invariants(dq, list(reference))


def test_structural_checker_detects_broken_link():
    dq = LAB.Deque()
    dq.push_back(1)
    dq.push_back(2)
    dq._tail.prev = None
    with pytest.raises(LAB.SelfCheckError):
        LAB.check_deque_invariants(dq, [1, 2])


@pytest.mark.parametrize("optimized", [False, True])
def test_checks_remain_active_with_optimization(optimized):
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(LAB_PATH), "--variant", "9", "--check-only"])
    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    LAB.expect("self_check: OK" in result.stdout, "Самопроверка не завершена")


@pytest.mark.parametrize(
    "manifest", [None, {"variant": 8, "seed": 38}, {"variant": 9, "seed": 38}]
)
def test_wrong_or_missing_manifest_is_rejected(tmp_path, manifest):
    if manifest is not None:
        (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(SystemExit):
        LAB.check_variant(tmp_path, 9)
