"""Самопроверка и эксперимент ЛР № 5 по заготовке курса МТУСИ (CC BY 4.0)."""

from __future__ import annotations

import argparse
import json
import math
import platform
import random
import statistics
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

from bst import BST

SIZES = (1_000, 3_000, 10_000, 30_000, 100_000)
REPEATS = 5
QUERIES = 1_000
RANDOM_SEQUENCES = 100


def expect(condition: bool, message: str) -> None:
    """Остановить проверку при нарушении контракта, в том числе с -O."""
    if not condition:
        raise AssertionError(message)


def self_check(seed: int) -> int:
    """Проверить обходы, три случая удаления и случайные команды."""
    tree = BST()
    expect(not tree.search(1), "Поиск в пустом дереве")
    tree.delete(1)
    expect(tree.height() == -1 and tree.size() == 0, "Пустое дерево")
    traversals = (
        tree.in_order,
        tree.pre_order,
        tree.post_order,
        tree.level_order,
    )
    expect(all(walk() == [] for walk in traversals), "Пустые обходы")

    tree.insert(5)
    tree.insert(5)
    expect(tree.height() == 0 and tree.size() == 1, "База и дубликат")
    for key in (2, 8, 1, 3, 7, 9):
        tree.insert(key)
    tree.delete(1)
    expect(tree.in_order() == [2, 3, 5, 7, 8, 9], "Удаление листа")
    tree.delete(2)
    expect(tree.in_order() == [3, 5, 7, 8, 9], "Удаление с одним ребёнком")
    tree.delete(5)
    expect(tree.in_order() == [3, 7, 8, 9], "Удаление с двумя детьми")

    tree = BST()
    for key in (4, 2, 6, 1, 3, 5, 7):
        tree.insert(key)
    expect(tree.in_order() == [1, 2, 3, 4, 5, 6, 7], "In-order")
    expect(tree.pre_order() == [4, 2, 1, 3, 6, 5, 7], "Pre-order")
    expect(tree.post_order() == [1, 3, 2, 5, 7, 6, 4], "Post-order")
    expect(tree.level_order() == [4, 2, 6, 1, 3, 5, 7], "Level-order")
    expect(tree.height() == 2 and tree.size() == 7, "Высота и размер")

    rng = random.Random(seed)
    commands = 0
    for _ in range(RANDOM_SEQUENCES):
        tree = BST()
        reference: set[int] = set()
        for _ in range(rng.randint(1, 80)):
            key = rng.randint(-30, 30)
            operation = rng.randrange(3)
            if operation == 0:
                tree.insert(key)
                reference.add(key)
            elif operation == 1:
                tree.delete(key)
                reference.discard(key)
            else:
                expect(tree.search(key) == (key in reference), "Поиск")
            expect(tree.in_order() == sorted(reference), "Инвариант BST")
            expect(tree.size() == len(reference), "Счётчик узлов")
            commands += 1
        for key in range(-30, 31):
            expect(tree.search(key) == (key in reference), "Итоговый поиск")
    print(f"self_check: OK ({commands} случайных команд)", flush=True)
    return commands


def bench(search_batch: Callable[[], None]) -> list[float]:
    """Вернуть пять времён пачки запросов в секундах после прогрева."""
    search_batch()
    samples = []
    for _ in range(REPEATS):
        start = time.perf_counter()
        search_batch()
        samples.append(time.perf_counter() - start)
    return samples


def system_output(command: list[str]) -> str:
    """Прочитать сведения macOS, если системная команда доступна."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, check=False, timeout=3
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def power_source() -> str:
    """На macOS вернуть зафиксированный источник питания."""
    if platform.system() == "Darwin":
        lines = system_output(["/usr/bin/pmset", "-g", "batt"]).splitlines()
        if lines:
            return lines[0]
    return "unknown"


def cpu_name() -> str:
    """Вернуть модель процессора, если она доступна на текущей платформе."""
    if platform.system() == "Darwin":
        raw = system_output(
            ["/usr/sbin/system_profiler", "SPHardwareDataType"]
        )
        for line in raw.splitlines():
            label, _, value = line.strip().partition(":")
            if label in {"Chip", "Processor Name"} and value.strip():
                return value.strip()
    return platform.processor() or platform.machine()


def run_benchmarks(seed: int) -> list[dict]:
    """Сравнить два поиска на одинаковых ключах и запросах."""
    rng = random.Random(seed)
    rows = []
    for n in SIZES:
        keys = rng.sample(range(10 * n), n)
        queries = [rng.randint(0, 10 * n) for _ in range(QUERIES)]
        tree = BST()
        for key in keys:
            tree.insert(key)

        reference = set(keys)
        hits = 0
        for query in queries:
            expected = query in reference
            expect(tree.search(query) == expected, "BST: неверный ответ")
            expect((query in keys) == expected, "Список: неверный ответ")
            hits += int(expected)

        def search_bst() -> None:
            for query in queries:
                _ = tree.search(query)

        def search_list() -> None:
            for query in queries:
                _ = query in keys

        bst_samples = bench(search_bst)
        list_samples = bench(search_list)
        row = {
            "n": n,
            "height": tree.height(),
            "hits": hits,
            "bst_samples_seconds": bst_samples,
            "list_samples_seconds": list_samples,
            "bst_median_us": statistics.median(bst_samples) * 1e6 / QUERIES,
            "list_median_us": statistics.median(list_samples) * 1e6 / QUERIES,
            "power_source": power_source(),
        }
        rows.append(row)
        print(
            f"n={n:>6}  h={row['height']:>2}  попадания={hits:>3}  "
            f"BST={row['bst_median_us']:.3f} мкс  "
            f"list={row['list_median_us']:.3f} мкс",
            flush=True,
        )
    return rows


def plot_results(rows: list[dict], out: Path) -> None:
    """Сохранить графики времени поиска и высоты BST."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    sizes = [row["n"] for row in rows]
    fig, axis = plt.subplots(figsize=(8, 4.5), layout="constrained")
    axis.loglog(
        sizes, [row["bst_median_us"] for row in rows], "o-", label="BST"
    )
    axis.loglog(
        sizes, [row["list_median_us"] for row in rows], "s-", label="list"
    )
    axis.set(
        title="Поиск в BST и списке",
        xlabel="Число ключей n",
        ylabel="Время на запрос, мкс",
    )
    axis.grid(which="both", alpha=0.25)
    axis.legend()
    fig.savefig(out / "lab05_search.png", dpi=160)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4.5), layout="constrained")
    axis.loglog(
        sizes, [row["height"] for row in rows], "o-", label="Случайный BST"
    )
    axis.loglog(
        sizes, [n - 1 for n in sizes], "--", label="Цепочка: n − 1 (теория)"
    )
    axis.loglog(
        sizes, [math.log2(n) for n in sizes], ":", label="Ориентир log₂(n)"
    )
    axis.set(
        title="Высота BST и порядок вставки",
        xlabel="Число ключей n",
        ylabel="Высота h, рёбра",
    )
    axis.grid(which="both", alpha=0.25)
    axis.legend()
    fig.savefig(out / "lab05_height.png", dpi=160)
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
    commands = self_check(seed)
    if args.check_only:
        return

    power_before = power_source()
    rows = run_benchmarks(seed)
    power_after = power_source()
    metadata = {
        "variant": args.variant,
        "seed": seed,
        "measured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": cpu_name(),
        "queries_per_sample": QUERIES,
        "warmup": 1,
        "repeats": REPEATS,
        "random_commands_checked": commands,
        "power_before": power_before,
        "power_after": power_after,
    }
    args.out.mkdir(parents=True, exist_ok=True)
    plot_results(rows, args.out)
    (args.out / "results.json").write_text(
        json.dumps(
            {"metadata": metadata, "benchmarks": rows},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Результаты и графики сохранены в {args.out}")


if __name__ == "__main__":
    main()
