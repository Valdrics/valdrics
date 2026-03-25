import asyncio
import sys
from decimal import Decimal
from datetime import date

# Mock objects since we don't want a full DB env for a simple logic check
class Record:
    def __init__(self, amount: float, d: date):
        self.amount = amount
        self.date = d


async def verify_precision() -> int:
    print("--- Verifying Forecaster Precision (Decimal) ---")

    # 1. Setup History
    today = date.today()
    history = [Record(100.05, today) for _ in range(10)]  # 10 records

    # 2. Import and Run
    try:
        from app.shared.analysis.forecaster import SymbolicForecaster

        # We need to ensure prophet doesn't block the test if not installed
        result = await SymbolicForecaster.forecast(history)

        print(f"Model used: {result['model']}")
        print(
            "Total Forecasted Cost: "
            f"{result['total_forecasted_cost']} "
            f"(Type: {type(result['total_forecasted_cost'])})"
        )

        # Check type
        if not isinstance(result["total_forecasted_cost"], Decimal):
            raise TypeError("Error: result is not Decimal")
        print("✅ SUCCESS: Precision verified.")
        return 0

    except (
        AssertionError,
        ImportError,
        KeyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as e:
        print(f"❌ FAILED: {str(e)}")
        return 1


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(verify_precision())

if __name__ == "__main__":
    raise SystemExit(main())
