from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import platform
import random
import statistics
import subprocess
import time
from collections import Counter
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

SIZES_QUADRATIC = (500, 1_000, 2_000, 4_000, 8_000)
SIZES_QUICK = (1_000, 3_000, 10_000, 30_000, 100_000)
REPEATS = 5


def identity(value):
    return value


def bubble_sort(a: list, *, key: Callable = identity) -> tuple[list, int, int]:
    data = a.copy()
    comparisons = swaps = 0
    for end in range(len(data) - 1, 0, -1):
        swapped = False
        for index in range(end):
            comparisons += 1
            if key(data[index]) > key(data[index + 1]):
                data[index], data[index + 1] = data[index + 1], data[index]
                swaps += 1
                swapped = True
        if not swapped:
            break
    return data, comparisons, swaps


def insertion_sort(
    a: list, *, key: Callable = identity
) -> tuple[list, int, int]:
    data = a.copy()
    comparisons = moves = 0
    for index in range(1, len(data)):
        value = data[index]
        position = index
        while position > 0:
            comparisons += 1
            if key(data[position - 1]) <= key(value):
                break
            data[position] = data[position - 1]
            moves += 1
            position -= 1
        data[position] = value
        moves += 1
    return data, comparisons, moves


def selection_sort(
    a: list, *, key: Callable = identity
) -> tuple[list, int, int]:
    data = a.copy()
    comparisons = swaps = 0
    for index in range(len(data) - 1):
        minimum = index
        for candidate in range(index + 1, len(data)):
            comparisons += 1
            if key(data[candidate]) < key(data[minimum]):
                minimum = candidate
        if minimum != index:
            data[index], data[minimum] = data[minimum], data[index]
            swaps += 1
    return data, comparisons, swaps


def quick_sort(
    a: list,
    rng: random.Random | None = None,
    *,
    key: Callable = identity,
) -> list:
    data = a.copy()
    if rng is None:
        rng = random.Random()
    stack = [(0, len(data))]
    while stack:
        lo, hi = stack.pop()
        while hi - lo > 1:
            pivot = key(data[rng.randrange(lo, hi)])
            left = index = lo
            right = hi
            while index < right:
                current = key(data[index])
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


SIMPLE_SORTS = {
    "bubble_sort": bubble_sort,
    "insertion_sort": insertion_sort,
    "selection_sort": selection_sort,
}
ALGORITHMS = {
    **{name: lambda a, fn=fn: fn(a)[0] for name, fn in SIMPLE_SORTS.items()},
    "quick_sort": lambda a: quick_sort(a, random.Random(39)),
}


class SelfCheckError(Exception):
    pass


def expect(condition: bool, message: str) -> None:
    if not condition:
        raise SelfCheckError(message)


def is_sorted(a: list) -> bool:
    return all(a[index] <= a[index + 1] for index in range(len(a) - 1))


def make_inputs(n: int, seed: int) -> dict[str, list[int]]:
    rng = random.Random(seed + n)
    data = [rng.randint(-1_000_000, 1_000_000) for _ in range(n)]
    return {
        "упорядоченный": sorted(data),
        "случайный": data,
        "обратный": sorted(data, reverse=True),
    }


def check_algorithm(fn, seed: int = 39) -> None:
    boundary = [[], [7], [5] * 10, [1, 2, 3, 4, 5], [5, 4, 3, 2, 1]]
    rng = random.Random(seed)
    cases = boundary + [
        [rng.randint(-100, 100) for _ in range(rng.randint(0, 80))]
        for _ in range(300)
    ]
    for original in cases:
        argument = original.copy()
        result = fn(argument)
        expect(isinstance(result, list), "Результат должен быть списком")
        expect(
            result is not argument, "Функция должна возвращать новый список"
        )
        expect(argument == original, "Изменён исходный список")
        expect(is_sorted(result), "Нарушен неубывающий порядок")
        expect(Counter(result) == Counter(original), "Потеряны элементы")
        expect(result == sorted(original), "Расхождение с sorted")


def check_counters() -> None:
    for n in range(21):
        ordered = list(range(n))
        reverse = ordered[::-1]
        maximum = n * (n - 1) // 2
        expected_linear = max(0, n - 1)
        expect(
            bubble_sort(ordered)[1:] == (expected_linear, 0),
            "Неверные счётчики пузырька на упорядоченном входе",
        )
        expect(
            bubble_sort(reverse)[1:] == (maximum, maximum),
            "Неверные счётчики пузырька на обратном входе",
        )
        expect(
            insertion_sort(ordered)[1:] == (expected_linear, expected_linear),
            "Неверные счётчики вставок на упорядоченном входе",
        )
        expect(
            insertion_sort(reverse)[1:]
            == (maximum, maximum + expected_linear),
            "Неверные счётчики вставок на обратном входе",
        )
        for data in (ordered, reverse, [0] * n):
            _, comparisons, swaps = selection_sort(data)
            expect(comparisons == maximum, "Неверное число сравнений выбора")
            expect(0 <= swaps <= expected_linear, "Слишком много обменов")


def stability_demo(seed: int = 39) -> list[dict]:
    pairs = [(2, "a"), (2, "b"), (1, "c")]
    expected = sorted(pairs, key=lambda pair: pair[0])
    functions = {
        **{
            name: lambda a, fn=fn: fn(a, key=lambda pair: pair[0])[0]
            for name, fn in SIMPLE_SORTS.items()
        },
        "quick_sort": lambda a: quick_sort(
            a, random.Random(seed), key=lambda pair: pair[0]
        ),
    }
    rows = []
    for name, function in functions.items():
        result = function(pairs)
        keys = [pair[0] for pair in result]
        expect(is_sorted(keys), f"{name}: неверный порядок ключей")
        expect(Counter(result) == Counter(pairs), f"{name}: потеряны пары")
        stable = result == expected
        expect(
            stable == (name in {"bubble_sort", "insertion_sort"}),
            f"{name}: пример не демонстрирует ожидаемую стабильность",
        )
        rows.append(
            {
                "algorithm": name,
                "input": pairs,
                "result": result,
                "stable_on_example": stable,
            }
        )
        print(f"  {name}: {result}; порядок равных ключей сохранён: {stable}")
    return rows


def self_check(seed: int = 39) -> None:
    print("self_check:", flush=True)
    for name, function in ALGORITHMS.items():
        fn = (
            (lambda a: quick_sort(a, random.Random(seed)))
            if name == "quick_sort"
            else function
        )
        check_algorithm(fn, seed)
        print(f"  {name}: OK", flush=True)
    check_counters()
    print("  счётчики: OK", flush=True)
    print("self_check: OK", flush=True)


def bench(fn, data: list) -> list[float]:
    fn(data.copy())
    times = []
    for _ in range(REPEATS):
        argument = data.copy()
        started = time.perf_counter()
        result = fn(argument)
        elapsed = time.perf_counter() - started
        times.append(elapsed)
        del result
    return times


def log_log_slope(points: list[tuple[int, float]]) -> float:
    xs = [math.log10(n) for n, _ in points]
    ys = [math.log10(seconds) for _, seconds in points]
    mean_x, mean_y = statistics.mean(xs), statistics.mean(ys)
    return sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / sum(
        (x - mean_x) ** 2 for x in xs
    )


def run_benchmarks(seed: int) -> dict:
    sizes = sorted(set(SIZES_QUADRATIC) | set(SIZES_QUICK))
    inputs = {n: make_inputs(n, seed) for n in sizes}
    hashes = {
        str(n): hashlib.sha256(
            json.dumps(classes["случайный"], separators=(",", ":")).encode()
        ).hexdigest()
        for n, classes in inputs.items()
    }
    rows = []
    for name in ALGORITHMS:
        plan = SIZES_QUICK if name == "quick_sort" else SIZES_QUADRATIC
        print(f"\n{name}:", flush=True)
        for n in plan:
            for input_class, data in inputs[n].items():
                fn = (
                    (lambda a: quick_sort(a, random.Random(seed)))
                    if name == "quick_sort"
                    else SIMPLE_SORTS[name]
                )
                samples = bench(fn, data)
                seconds = statistics.median(samples)
                row = {
                    "algorithm": name,
                    "n": n,
                    "input_class": input_class,
                    "median_seconds": seconds,
                    "samples_seconds": samples,
                    "power_source": power_source(),
                }
                if name in SIMPLE_SORTS:
                    result, comparisons, movements = SIMPLE_SORTS[name](data)
                    expect(result == sorted(data), f"Ошибка {name} при n={n}")
                    row.update(comparisons=comparisons, movements=movements)
                rows.append(row)
                print(
                    f"  n={n:>7}, {input_class:<13}: {seconds:.6f} с",
                    flush=True,
                )
    slopes = {
        name: {
            input_class: log_log_slope(
                [
                    (row["n"], row["median_seconds"])
                    for row in rows
                    if row["algorithm"] == name
                    and row["input_class"] == input_class
                ]
            )
            for input_class in ("упорядоченный", "случайный", "обратный")
        }
        for name in ALGORITHMS
    }
    return {"benchmarks": rows, "slopes": slopes, "input_sha256": hashes}


def plot_results(results: dict, out_dir: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 3, figsize=(16, 5), sharey=True)
    for axis, input_class in zip(
        axes, ("упорядоченный", "случайный", "обратный")
    ):
        for name in ALGORITHMS:
            rows = [
                row
                for row in results["benchmarks"]
                if row["algorithm"] == name
                and row["input_class"] == input_class
            ]
            slope = results["slopes"][name][input_class]
            axis.loglog(
                [row["n"] for row in rows],
                [row["median_seconds"] for row in rows],
                marker="o",
                label=f"{name}, наклон {slope:.2f}",
            )
        axis.set_title(input_class.capitalize())
        axis.set_xlabel("Размер массива n")
        axis.grid(True, which="both", alpha=0.3)
        axis.legend(fontsize=8)
    axes[0].set_ylabel("Медианное время, с")
    fig.tight_layout()
    fig.savefig(out_dir / "lab03_sorting.png", dpi=150)
    plt.close(fig)


def power_source() -> str:
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["/usr/bin/pmset", "-g", "batt"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.stdout:
                return result.stdout.splitlines()[0]
        except (OSError, subprocess.TimeoutExpired):
            pass
    return "unknown"


def cpu_name() -> str:
    if platform.system() == "Darwin":
        try:
            result = subprocess.run(
                ["/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            if result.stdout.strip():
                return result.stdout.strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
    return platform.processor() or platform.machine()


def main() -> None:
    parser = argparse.ArgumentParser(description="ЛР 3: сортировки, вариант 9")
    parser.add_argument("--variant", type=int, required=True)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument(
        "--out", type=Path, default=Path(__file__).resolve().parent / "reports"
    )
    args = parser.parse_args()
    if args.variant < 1:
        parser.error("Номер варианта должен быть положительным")
    seed = 30 + args.variant
    self_check(seed)
    print("\nСтабильность:", flush=True)
    stability = stability_demo(seed)
    if args.check_only:
        return
    args.out.mkdir(parents=True, exist_ok=True)
    gc.collect()
    power_before = power_source()
    results = run_benchmarks(seed)
    results.update(
        stability=stability,
        metadata={
            "variant": args.variant,
            "seed": seed,
            "measured_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu": cpu_name(),
            "power_before": power_before,
            "power_after": power_source(),
            "repeats": REPEATS,
            "warmup": 1,
            "source_sha256": hashlib.sha256(
                Path(__file__).read_bytes()
            ).hexdigest(),
            "generator": "random.Random(seed + n), randint(-1000000, 1000000)",
        },
    )
    (args.out / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    plot_results(results, args.out)
    print(f"\nРезультаты сохранены в {args.out}", flush=True)


if __name__ == "__main__":
    main()
