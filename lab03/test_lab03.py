import importlib.util
import random
import subprocess
import sys
from itertools import permutations
from pathlib import Path

import pytest

LAB_PATH = Path(__file__).with_name("lab03-simple-sorts-quicksort-starter.py")
SPEC = importlib.util.spec_from_file_location("lab03", LAB_PATH)
LAB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB)


@pytest.mark.parametrize("algorithm", LAB.ALGORITHMS.values())
@pytest.mark.parametrize(
    "data",
    [
        [],
        [1],
        [2, 1],
        [0] * 20,
        [-3, 0, -3, 9],
        list(range(20)),
        list(range(20, -1, -1)),
    ],
)
def test_boundaries_and_input_preservation(algorithm, data):
    original = data.copy()
    result = algorithm(data)
    LAB.expect(result == sorted(original), "Неверный результат")
    LAB.expect(data == original, "Изменён вход")
    LAB.expect(result is not data, "Не создан новый список")


def test_counters_on_every_small_permutation():
    for permutation in permutations(range(5)):
        data = list(permutation)
        inversions = sum(
            data[left] > data[right]
            for left in range(len(data))
            for right in range(left + 1, len(data))
        )
        _, _, bubble_swaps = LAB.bubble_sort(data)
        _, _, insertion_moves = LAB.insertion_sort(data)
        _, selection_comparisons, selection_swaps = LAB.selection_sort(data)
        LAB.expect(bubble_swaps == inversions, "Неверное число обменов")
        LAB.expect(
            insertion_moves == inversions + len(data) - 1,
            "Неверное число сдвигов и финальных записей",
        )
        LAB.expect(selection_comparisons == 10, "Неверное число сравнений")
        LAB.expect(selection_swaps <= 4, "Слишком много обменов выбора")


@pytest.mark.parametrize("seed", [0, 9, 39])
def test_random_inputs_against_reference(seed):
    for algorithm in LAB.ALGORITHMS.values():
        LAB.check_algorithm(algorithm, seed)


@pytest.mark.parametrize("algorithm", [LAB.bubble_sort, LAB.insertion_sort])
def test_stable_sorts_compare_only_keys(algorithm):
    pairs = [(2, "z"), (1, "y"), (2, "a"), (1, "b")]
    result, _, _ = algorithm(pairs, key=lambda pair: pair[0])
    LAB.expect(
        result == sorted(pairs, key=lambda pair: pair[0]),
        "Изменён порядок равных ключей или сравнивались метки",
    )


@pytest.mark.parametrize("seed", [0, 9, 39])
def test_stability_counterexample(seed):
    rows = LAB.stability_demo(seed)
    LAB.expect(
        [row["stable_on_example"] for row in rows]
        == [True, True, False, False],
        "Неверная демонстрация",
    )


def test_quick_sort_uses_random_index():
    class RecordingRandom(random.Random):
        def __init__(self):
            super().__init__(39)
            self.calls = []

        def randrange(self, start, stop=None, step=1):
            self.calls.append((start, stop))
            return super().randrange(start, stop, step)

    rng = RecordingRandom()
    data = [7, 1, 8, 2, 6, 0, 5, 3, 4]
    LAB.expect(
        LAB.quick_sort(data, rng) == sorted(data), "Неверная сортировка"
    )
    LAB.expect(bool(rng.calls), "Генератор не использовался")
    LAB.expect(rng.calls[0] == (0, len(data)), "Неверный диапазон опорного")
    LAB.expect(
        all(0 <= lo < hi <= len(data) for lo, hi in rng.calls),
        "Опорный выбирался за границами подмассива",
    )


def test_quick_sort_equal_keys_are_processed_in_one_partition():
    calls = 0

    def count_key(value):
        nonlocal calls
        calls += 1
        return value

    data = [7] * 20_000
    result = LAB.quick_sort(data, random.Random(39), key=count_key)
    LAB.expect(result == data, "Потеряны одинаковые значения")
    LAB.expect(
        calls == len(data) + 1,
        "Равные ключи обрабатывались несколькими разбиениями",
    )


def test_quick_sort_large_ordered_input():
    data = list(range(20_000))
    result = LAB.quick_sort(data, random.Random(39))
    LAB.expect(result == data, "Неверный результат на большом входе")


def test_input_generator_reproducibility():
    first = LAB.make_inputs(100, 39)
    LAB.expect(first == LAB.make_inputs(100, 39), "Генерация неповторяема")
    LAB.expect(first != LAB.make_inputs(100, 40), "Вариант не влияет на вход")
    expected = sorted(first["случайный"])
    LAB.expect(first["упорядоченный"] == expected, "Неверный прямой вход")
    LAB.expect(first["обратный"] == expected[::-1], "Неверный обратный вход")


def test_benchmark_uses_fresh_input():
    seen = []

    def mutate(data):
        LAB.expect(data == [2, 1], "Вход изменён предыдущим повтором")
        seen.append(data)
        data.clear()

    samples = LAB.bench(mutate, [2, 1])
    LAB.expect(len(seen) == LAB.REPEATS + 1, "Неверное число запусков")
    LAB.expect(len(samples) == LAB.REPEATS, "Прогрев попал в измерения")
    LAB.expect(
        len({id(data) for data in seen}) == len(seen),
        "Переиспользован один и тот же список",
    )


@pytest.mark.parametrize("optimized", [False, True])
def test_self_check_cli(optimized):
    command = [sys.executable]
    if optimized:
        command.append("-O")
    command.extend([str(LAB_PATH), "--variant", "9", "--check-only"])
    result = subprocess.run(
        command, check=True, capture_output=True, text=True
    )
    LAB.expect("self_check: OK" in result.stdout, "Проверки не завершены")


def test_explicit_check_cannot_silently_accept_failure():
    with pytest.raises(LAB.SelfCheckError):
        LAB.expect(False, "Контрольная ошибка")
