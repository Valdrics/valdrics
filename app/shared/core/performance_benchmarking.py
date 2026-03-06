"""
Performance benchmarking primitives shared across load-test workflows.
"""

from __future__ import annotations

import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import structlog

logger = structlog.get_logger()


@dataclass
class BenchmarkResult:
    """Results from a benchmark test."""

    name: str
    iterations: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    median_time: float = 0.0
    min_time: float = float("inf")
    max_time: float = 0.0
    throughput: float = 0.0  # operations per second


class PerformanceBenchmark:
    """Performance benchmarking utility."""

    def __init__(self, name: str = "benchmark"):
        self.name = name
        self.results: list[BenchmarkResult] = []

    async def benchmark_async(
        self,
        func: Callable[..., Awaitable[Any]],
        *args: Any,
        iterations: int = 100,
        warmup_iterations: int = 10,
        **kwargs: Any,
    ) -> BenchmarkResult:
        """Benchmark an async function."""
        for _ in range(warmup_iterations):
            await func(*args, **kwargs)

        times: list[float] = []
        start_time = time.time()
        for _ in range(iterations):
            iteration_start = time.perf_counter()
            await func(*args, **kwargs)
            times.append(time.perf_counter() - iteration_start)

        total_time = time.time() - start_time

        result = BenchmarkResult(
            name=f"{self.name}_{func.__name__}",
            iterations=iterations,
            total_time=total_time,
            avg_time=statistics.mean(times),
            median_time=statistics.median(times),
            min_time=min(times),
            max_time=max(times),
            throughput=iterations / total_time,
        )
        self.results.append(result)

        logger.info(
            "benchmark_completed",
            name=result.name,
            iterations=result.iterations,
            avg_time=result.avg_time,
            median_time=result.median_time,
            throughput=result.throughput,
        )
        return result

    def benchmark_sync(
        self,
        func: Callable[..., Any],
        *args: Any,
        iterations: int = 100,
        warmup_iterations: int = 10,
        **kwargs: Any,
    ) -> BenchmarkResult:
        """Benchmark a sync function using a thread pool."""

        def run_warmup() -> None:
            for _ in range(warmup_iterations):
                func(*args, **kwargs)

        def run_benchmark() -> list[float]:
            times: list[float] = []
            for _ in range(iterations):
                iteration_start = time.perf_counter()
                func(*args, **kwargs)
                times.append(time.perf_counter() - iteration_start)
            return times

        with ThreadPoolExecutor(max_workers=1) as executor:
            executor.submit(run_warmup).result()

        start_time = time.time()
        with ThreadPoolExecutor(max_workers=1) as executor:
            times = executor.submit(run_benchmark).result()
        total_time = time.time() - start_time

        result = BenchmarkResult(
            name=f"{self.name}_{func.__name__}",
            iterations=iterations,
            total_time=total_time,
            avg_time=statistics.mean(times),
            median_time=statistics.median(times),
            min_time=min(times),
            max_time=max(times),
            throughput=iterations / total_time,
        )
        self.results.append(result)
        return result

    def get_summary(self) -> dict[str, Any]:
        """Get summary of all benchmark results."""
        return {
            "benchmark_name": self.name,
            "total_benchmarks": len(self.results),
            "results": [
                {
                    "name": r.name,
                    "iterations": r.iterations,
                    "avg_time": r.avg_time,
                    "median_time": r.median_time,
                    "throughput": r.throughput,
                    "min_time": r.min_time,
                    "max_time": r.max_time,
                }
                for r in self.results
            ],
        }
