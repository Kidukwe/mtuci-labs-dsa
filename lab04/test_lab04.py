import importlib.util
import random
import subprocess
import sys
from pathlib import Path

import pytest

LAB_PATH = Path(__file__).with_name(
    "lab04-mergesort-linear-heapsort-starter.py"
)
SPEC = importlib.util.spec_from_file_location("lab04", LAB_PATH)
LAB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB)
BOUNDARIES = [
    [],
    [0],
    [42],
    [7] * 20,
    [-3, 0, 5],
    list(range(20)),
    list(range(20, -1, -1)),
]


@pytest.mark.parametrize(
    "name", ["merge_sort", "counting_sort", "radix_sort_lsd", "quick_sort"]
)
@pytest.mark.parametrize("values", BOUNDARIES)
def test_new_list_and_correct_result(name, values):
    if name in {"counting_sort", "radix_sort_lsd"}:
        values = [abs(value) for value in values]
    argument = values.copy()
    if name == "counting_sort":
        result = LAB.counting_sort(argument, max(argument, default=0))
    else:
        result = getattr(LAB, name)(argument)
    LAB.expect(result == sorted(values), "Неверный результат")
    LAB.expect(argument == values, "Изменён исходный список")
    LAB.expect(result is not argument, "Не создан новый список")


@pytest.mark.parametrize("values", BOUNDARIES)
def test_heap_sort_in_place(values):
    argument = values.copy()
    returned = LAB.heap_sort(argument)
    LAB.expect(returned is None, "HeapSort должен возвращать None")
    LAB.expect(argument == sorted(values), "Нарушен порядок HeapSort")


class TaggedInt(int):
    def __new__(cls, value, tag):
        instance = super().__new__(cls, value)
        instance.tag = tag
        return instance


@pytest.mark.parametrize(
    "name", ["merge_sort", "counting_sort", "radix_sort_lsd"]
)
def test_stability_with_distinguishable_equal_keys(name):
    rng = random.Random(39)
    for _ in range(100):
        values = [TaggedInt(rng.randrange(10), index) for index in range(50)]
        expected = [(int(value), value.tag) for value in sorted(values)]
        result = (
            LAB.counting_sort(values, 9)
            if name == "counting_sort"
            else getattr(LAB, name)(values)
        )
        LAB.expect(
            [(int(value), value.tag) for value in result] == expected,
            "Равные ключи потеряли порядок меток",
        )


@pytest.mark.parametrize(
    "left,right",
    [([], []), ([1], [2, 3]), ([2, 3], [1]), ([1, 4, 7], [2, 3, 6])],
)
def test_merge_keeps_both_tails(left, right):
    original_left, original_right = left.copy(), right.copy()
    result = LAB.merge(left, right, key=lambda value: value)
    LAB.expect(result == sorted(left + right), "Потерян остаток списка")
    LAB.expect(
        left == original_left and right == original_right,
        "Слияние изменило вход",
    )


def test_sift_down_preserves_active_heap_boundary():
    data = [3, 9, 8, 5, 2, 7, 1, 777]
    LAB.sift_down(data, 0, 7)
    LAB.expect(data[7] == 777, "Изменён элемент за пределами кучи")
    LAB.expect(
        all(data[(i - 1) // 2] >= data[i] for i in range(1, 7)),
        "Не восстановлена max-куча",
    )


def test_radix_rejects_negative_values():
    with pytest.raises(ValueError):
        LAB.radix_sort_lsd([0, -1])


@pytest.mark.parametrize("optimized", [False, True])
def test_self_check_cli(optimized):
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(LAB_PATH), "--variant", "9", "--check-only"])
    result = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    LAB.expect("self_check: OK" in result.stdout, "Самопроверка не завершена")


def test_benchmark_warmup_samples_and_fresh_copies():
    seen = []

    def mutate(values):
        LAB.expect(values == [2, 1], "Повтор получил изменённый список")
        seen.append(values)
        values.clear()

    samples = []
    median = LAB.bench(mutate, [2, 1], samples)
    LAB.expect(len(seen) == LAB.REPEATS + 1, "Неверное число запусков")
    LAB.expect(len(samples) == LAB.REPEATS, "Прогрев попал в измерения")
    LAB.expect(median >= 0, "Некорректное время")
    LAB.expect(
        len({id(values) for values in seen}) == len(seen),
        "Не выделены свежие копии",
    )


def test_all_sorts_against_reference():
    rng = random.Random(39)
    for _ in range(300):
        values = [rng.randrange(1000) for _ in range(rng.randrange(100))]
        expected = sorted(values)
        for name in ("merge_sort", "radix_sort_lsd", "quick_sort"):
            LAB.expect(getattr(LAB, name)(values) == expected, name)
        LAB.expect(LAB.counting_sort(values, 999) == expected, "CountingSort")
        copy = values.copy()
        LAB.heap_sort(copy)
        LAB.expect(copy == expected, "HeapSort")
    large = [10**9, 0, 10, 100, 10**9]
    LAB.expect(LAB.radix_sort_lsd(large) == sorted(large), "Широкий диапазон")
    LAB.expect(
        LAB.quick_sort([7] * 10_000) == [7] * 10_000,
        "QuickSort на многочисленных повторах",
    )


def test_failed_check_is_not_silently_ignored():
    with pytest.raises(LAB.SelfCheckError):
        LAB.expect(False, "Контрольная ошибка")
