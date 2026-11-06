#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ЛР 4. MergeSort, CountingSort, RadixSort и HeapSort — вариант 9.

На основе материалов МТУСИ, кафедра «Программная инженерия», 2026,
CC BY 4.0: https://github.com/mel0d1an/data-structures-and-algorithms
Алгоритмы дополнены проверками, сохранением замеров и графиками.
Порядок запуска и обоснования сложности — в README.md.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# 1. Сортировки (реализуются вручную; sorted() используется только как эталон)
# ---------------------------------------------------------------------------


def merge(left: list, right: list, key) -> list:
    """Стабильное слияние двух отсортированных списков в новый список.

    При равных ключах первым выбирается элемент из left.
    Временная сложность: Θ(m + n) во всех случаях.
    Пространственная сложность: Θ(m + n) для результата, Θ(1) без него.
    m и n — длины двух входов; получение и сравнение ключа стоят O(1).
    """
    result = []
    i = j = 0

    while i < len(left) and j < len(right):
        if key(left[i]) <= key(right[j]):
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    while i < len(left):
        result.append(left[i])
        i += 1

    while j < len(right):
        result.append(right[j])
        j += 1
    return result


def merge_sort(a: list, key=lambda x: x) -> list:
    """Стабильная сортировка слиянием; возвращает новый список.

    Временная сложность: Θ(n log n) в лучшем, среднем и худшем случаях.
    Пространственная сложность: Θ(n) пиковая память списков;
    дополнительно O(log n) кадров рекурсии. n = len(a).
    """
    if len(a) <= 1:
        return a.copy()
    mid = len(a) // 2
    left = a[:mid]
    right = a[mid:]

    left_sorted = merge_sort(left, key=key)
    right_sorted = merge_sort(right, key=key)
    return merge(left_sorted, right_sorted, key=key)


def counting_sort(a: list[int], key_max: int) -> list[int]:
    """Стабильная сортировка подсчётом целых из [0, key_max].

    Частоты -> префиксные суммы -> расстановка с конца.
    Временная сложность: Θ(n + k) во всех случаях.
    Пространственная сложность: Θ(n + k), включая результат.
    n = len(a), k = key_max + 1. Требуется небольшой диапазон ключей.
    """
    counts = [0] * (key_max + 1)

    for value in a:
        counts[value] += 1

    for value in range(1, len(counts)):
        counts[value] += counts[value - 1]

    result = [0] * len(a)

    for value in reversed(a):
        position = counts[value] - 1
        result[position] = value
        counts[value] -= 1

    return result


def radix_sort_lsd(a: list[int]) -> list[int]:
    """Стабильный RadixSort LSD для неотрицательных целых.

    Временная сложность: Θ(d * (n + 10)) во всех случаях при заданных n, d.
    Пространственная сложность: Θ(n + 10), то есть Θ(n).
    n = len(a); d — число десятичных цифр максимума, минимум 1.
    Оценка предполагает постоянную стоимость арифметики разряда.
    """
    if not a:
        return []
    if any(value < 0 for value in a):
        raise ValueError("RadixSort принимает только неотрицательные числа")

    result = a.copy()
    maximum = max(result)
    exp = 1

    while maximum // exp > 0:
        counts = [0] * 10
        for value in result:
            digit = (value // exp) % 10
            counts[digit] += 1

        for digit in range(1, 10):
            counts[digit] += counts[digit - 1]

        output = [0] * len(result)
        for value in reversed(result):
            digit = (value // exp) % 10
            position = counts[digit] - 1
            output[position] = value
            counts[digit] -= 1

        result = output
        exp *= 10

    return result


def sift_down(a: list[int], i: int, n: int) -> None:
    """Восстановить max-heap a[0:n], опуская элемент с индексом i.

    Поддеревья детей должны быть кучами. Элементы за границей n не меняются.
    Временная сложность: Θ(1) в лучшем случае, O(log n) в худшем.
    Пространственная сложность: Θ(1), реализация итеративная.
    """
    while 2 * i + 1 < n:
        child = 2 * i + 1
        if child + 1 < n and a[child + 1] > a[child]:
            child += 1
        if a[i] >= a[child]:
            break
        a[i], a[child] = a[child], a[i]
        i = child


def heap_sort(a: list[int]) -> None:
    """HeapSort in-place: изменяет a, возвращает None.

    Построение max-кучи: Θ(n). Извлечение максимумов: O(n log n).
    Временная сложность: Θ(n) в лучшем случае на равных элементах;
    Θ(n log n) в среднем и худшем случаях.
    Пространственная сложность: Θ(1), без вспомогательного массива.
    Сортировка нестабильна. n = len(a).
    """
    n = len(a)

    for i in range(n // 2 - 1, -1, -1):
        sift_down(a, i, n)

    for end in range(n - 1, 0, -1):
        a[0], a[end] = a[end], a[0]
        sift_down(a, 0, end)


def quick_sort(a: list[int]) -> list[int]:
    """Рандомизированный QuickSort из ЛР 3; возвращает новый список.

    Для различных ключей: лучшее и ожидаемое время Θ(n log n),
    худшее Θ(n²). На всех равных ключах трёхсторонний проход даёт Θ(n).
    Пространственная сложность: Θ(n) с учётом копии входа;
    явный стек ограничен O(log n) обработкой меньшей части первой.
    Сортировка нестабильна. n = len(a).
    """
    data = a.copy()
    stack = [(0, len(data))]

    while stack:
        lo, hi = stack.pop()
        while hi - lo > 1:
            pivot = data[random.randrange(lo, hi)]
            left = index = lo
            right = hi

            while index < right:
                current = data[index]
                if current < pivot:
                    data[left], data[index] = data[index], data[left]
                    left += 1
                    index += 1
                elif current > pivot:
                    right -= 1
                    data[index], data[right] = data[right], data[index]
                else:
                    index += 1

            if left - lo < hi - right:
                if hi - right > 1:
                    stack.append((right, hi))
                hi = left
            else:
                if left - lo > 1:
                    stack.append((lo, left))
                lo = right

    return data


# ---------------------------------------------------------------------------
# 2. Верификация: инварианты + сверка с эталоном sorted()
#    (шаги 1–3 методики docs/ai-verification.md)
# ---------------------------------------------------------------------------


class SelfCheckError(Exception):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SelfCheckError(message)


def self_check() -> None:
    """Граничные и типовые случаи, стабильность, сверка с эталоном sorted()."""
    # Граничные случаи: пустой массив, один элемент, все элементы равны
    expect(merge_sort([]) == [], "Нарушена проверка: merge_sort([]) == []")
    expect(merge_sort([7]) == [7], "Нарушена проверка: merge_sort([7]) == [7]")
    expect(
        merge_sort([5, 5, 5]) == [5, 5, 5],
        "Нарушена проверка: merge_sort([5, 5, 5]) == [5, 5, 5]",
    )
    expect(
        counting_sort([], key_max=10) == [],
        "Нарушена проверка: counting_sort([], key_max=10) == []",
    )
    expect(
        radix_sort_lsd([0]) == [0],
        "Нарушена проверка: radix_sort_lsd([0]) == [0]",
    )
    single = [42]
    heap_sort(single)
    expect(single == [42], "Нарушена проверка: single == [42]")

    # Стабильность слияния проверяем на парах (ключ, порядковый номер).
    # поэтому при равных ключах порядок номеров обязан совпасть
    rng = random.Random(0)
    pairs = [(rng.randint(0, 5), i) for i in range(100)]
    expect(
        merge_sort(pairs, key=lambda p: p[0])
        == sorted(pairs, key=lambda p: p[0]),
        "Нарушена стабильность MergeSort на парах",
    )

    # Случайные тесты: инвариант перестановки + сверка с эталоном
    for _ in range(200):
        a = [rng.randint(0, 999) for _ in range(rng.randint(0, 60))]
        expected = sorted(a)
        expect(
            merge_sort(a) == expected,
            "Нарушена проверка: merge_sort(a) == expected",
        )
        expect(
            counting_sort(a, key_max=999) == expected,
            "Нарушена проверка: counting_sort(a, key_max=999) == expected",
        )
        expect(
            radix_sort_lsd(a) == expected,
            "Нарушена проверка: radix_sort_lsd(a) == expected",
        )
        buf = list(a)
        heap_sort(buf)
        expect(buf == expected, "Нарушена проверка: buf == expected")
        expect(
            sorted(buf) == expected,
            "Нарушена проверка: sorted(buf) == expected",
        )
    boundary = [
        [],
        [0],
        [7],
        [5] * 10,
        list(range(20)),
        list(range(20, -1, -1)),
    ]
    functions = (merge_sort, radix_sort_lsd, quick_sort)
    for original in boundary:
        expected = sorted(original)
        for function in functions:
            argument = original.copy()
            result = function(argument)
            expect(result == expected, function.__name__)
            expect(
                argument == original and result is not argument,
                "Нарушен контракт нового списка",
            )
        result = counting_sort(original, max(original, default=0))
        expect(result == expected, "CountingSort: граничный вход")
        buf = original.copy()
        expect(
            heap_sort(buf) is None and buf == expected,
            "HeapSort: контракт сортировки на месте",
        )
    for _ in range(300):
        original = [rng.randrange(1000) for _ in range(rng.randrange(80))]
        expected = sorted(original)
        for function in functions:
            argument = original.copy()
            result = function(argument)
            expect(result == expected, function.__name__)
            expect(
                Counter(result) == Counter(original),
                "Изменено мультимножество",
            )
            expect(
                argument == original and result is not argument,
                "Изменён исходный список",
            )
    print("self_check: OK", flush=True)


# ---------------------------------------------------------------------------
# 3. Бенчмарк (методика — docs/reproducibility.md)
# ---------------------------------------------------------------------------

SIZES = [1_000, 3_000, 10_000, 30_000, 100_000]
REPEATS = 5
SMALL_KEY_MAX = 100  # узкий диапазон: counting уместен
WIDE_KEY_MAX = (
    10**9
)  # широкий диапазон: counting теряет смысл (обсудить в отчёте)


def make_datasets(rng: random.Random, n: int) -> dict[str, list[int]]:
    """Массивы разных распределений и диапазонов ключей для размера n."""
    almost = list(range(n))
    for _ in range(max(1, n // 100)):  # ~1 % случайных обменов
        i, j = rng.randrange(n), rng.randrange(n)
        almost[i], almost[j] = almost[j], almost[i]
    return {
        "random_wide": [rng.randint(0, WIDE_KEY_MAX) for _ in range(n)],
        "random_small": [rng.randint(0, SMALL_KEY_MAX) for _ in range(n)],
        "sorted": list(range(n)),
        "reversed": list(range(n, 0, -1)),
        "almost_sorted": almost,
    }


def bench(fn, data: list[int], samples: list[float] | None = None) -> float:
    """Прогрев, свежая копия на повтор и медиана пяти измерений."""
    fn(list(data))
    times = []
    for _ in range(REPEATS):
        buf = list(data)
        started = time.perf_counter()
        result = fn(buf)
        times.append(time.perf_counter() - started)
        del result
    if samples is not None:
        samples.extend(times)
    return statistics.median(times)


def power_source() -> str:
    if platform.system() == "Darwin":
        try:
            process = subprocess.run(
                ["/usr/bin/pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if process.stdout:
                return process.stdout.splitlines()[0]
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "unknown"


def log_log_slope(points: list[tuple[int, float]]) -> float:
    xs = [math.log10(n) for n, _ in points]
    ys = [math.log10(seconds) for _, seconds in points]
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sum(
        (x - mean_x) ** 2 for x in xs
    )


def run_benchmarks(seed: int) -> dict:
    rng = random.Random(seed)
    datasets = {n: make_datasets(rng, n) for n in SIZES}
    algorithms = {
        "merge_sort": merge_sort,
        "counting_sort": lambda a: counting_sort(a, max(a, default=0)),
        "radix_sort_lsd": radix_sort_lsd,
        "heap_sort": heap_sort,
        "quick_sort": quick_sort,
        "sorted": sorted,
    }
    rows = []
    for n, classes in datasets.items():
        print(f"\nn = {n}:", flush=True)
        for distribution, data in classes.items():
            print(f"  распределение {distribution}:", flush=True)
            expected = sorted(data)
            digest = hashlib.sha256(
                json.dumps(data, separators=(",", ":")).encode()
            ).hexdigest()
            for name, function in algorithms.items():
                row = {
                    "n": n,
                    "distribution": distribution,
                    "algorithm": name,
                    "input_sha256": digest,
                }
                if name == "counting_sort" and distribution == "random_wide":
                    row.update(skipped=True, reason="диапазон ключей до 10**9")
                    rows.append(row)
                    print(
                        f"    {name:>18}: пропуск (диапазон ключей)",
                        flush=True,
                    )
                    continue
                argument = data.copy()
                result = function(argument)
                got = argument if name == "heap_sort" else result
                expect(
                    got == expected, f"{name}: ошибка на {distribution}, n={n}"
                )
                if name != "heap_sort":
                    expect(argument == data, f"{name}: изменён вход")
                samples = []
                seconds = bench(function, data, samples)
                row.update(
                    skipped=False,
                    median_seconds=seconds,
                    samples_seconds=samples,
                    power_source=power_source(),
                )
                rows.append(row)
                print(f"    {name:>18}: t = {seconds:.6f} c", flush=True)
    slopes = {}
    for distribution in next(iter(datasets.values())):
        slopes[distribution] = {}
        for name in algorithms:
            points = [
                (row["n"], row["median_seconds"])
                for row in rows
                if row["distribution"] == distribution
                and row["algorithm"] == name
                and not row["skipped"]
            ]
            if len(points) > 1:
                slopes[distribution][name] = log_log_slope(points)
    return {"benchmarks": rows, "slopes": slopes}


def plot_results(results: dict, out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    titles = {
        "random_wide": "Случайные, широкий диапазон",
        "random_small": "Случайные, узкий диапазон",
        "sorted": "Отсортированные",
        "reversed": "Обратно отсортированные",
        "almost_sorted": "Почти отсортированные",
    }
    colors = {
        "merge_sort": "tab:blue",
        "counting_sort": "tab:orange",
        "radix_sort_lsd": "tab:green",
        "heap_sort": "tab:red",
        "quick_sort": "tab:purple",
        "sorted": "tab:brown",
    }
    for distribution, title in titles.items():
        fig, axis = plt.subplots(figsize=(9, 5.5))
        for name, color in colors.items():
            rows = [
                row
                for row in results["benchmarks"]
                if row["distribution"] == distribution
                and row["algorithm"] == name
                and not row["skipped"]
            ]
            if not rows:
                continue
            slope = results["slopes"][distribution][name]
            axis.loglog(
                [row["n"] for row in rows],
                [row["median_seconds"] for row in rows],
                marker="o",
                color=color,
                label=f"{name}: наклон {slope:.2f}",
            )
        axis.set_title(title)
        axis.set_xlabel("Размер массива n")
        axis.set_ylabel("Медианное время, с")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(fontsize=9)
        if distribution == "random_wide":
            axis.text(
                0.02,
                0.98,
                "CountingSort пропущен: диапазон до 10⁹",
                transform=axis.transAxes,
                va="top",
                fontsize=9,
            )
        fig.tight_layout()
        fig.savefig(out_dir / f"lab04_{distribution}.png", dpi=150)
        plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", type=int, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "reports"
    )
    args = parser.parse_args()
    if args.variant < 1:
        parser.error("Номер варианта должен быть положительным")
    seed = 30 + args.variant
    random.seed(seed)
    self_check()
    if args.check_only:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    power_before = power_source()
    results = run_benchmarks(seed)
    results["metadata"] = {
        "variant": args.variant,
        "seed": seed,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "repeats": REPEATS,
        "warmup": 1,
        "power_before": power_before,
        "power_after": power_source(),
        "source_sha256": hashlib.sha256(
            Path(__file__).read_bytes()
        ).hexdigest(),
    }
    (args.out / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_results(results, args.out)
    print(f"\nГрафики и результаты сохранены в {args.out}", flush=True)


if __name__ == "__main__":
    main()
