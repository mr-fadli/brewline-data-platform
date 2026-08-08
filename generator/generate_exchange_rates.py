"""
generate_exchange_rates.py

Generates a synthetic exchange-rate CSV for a portfolio project.

Usage:
    1. Edit the CONFIG section below (START_DATE, NUM_DAYS, currencies).
    2. Run:  python generate_exchange_rates.py
    3. Output written to the FILE_PATH path.

CSV columns:
    currency_date, currency, rate_to_usd
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

# ------------------------------------------------------------------
# CONFIG — edit these values
# ------------------------------------------------------------------

START_DATE = date(2026, 7, 8)

# How many days of data to generate, starting from START_DATE (inclusive).
# e.g. NUM_DAYS = 23 with START_DATE = 2026-06-08 generates 2026-06-08
# through 2026-06-30.
NUM_DAYS = 60

# Where this script itself lives, e.g. my_project/generator/
SCRIPT_DIR = Path(__file__).resolve().parent

# Output path for the CSV. This is resolved RELATIVE TO THIS SCRIPT'S
# LOCATION (not your current working directory), so it works the same
# whether you run:
#   python generate_exchange_rates.py
#   python my_project/generator/generate_exchange_rates.py
#
# Default assumes this file sits in my_project/generator/ and writes
# to a sibling my_project/data/ folder. Adjust the "../data/..." part
# to match your project's actual folder layout.
FILE_PATH = SCRIPT_DIR / "../brewline_dbt/seeds/exchange_rates.csv"

# USD is always the base currency with a fixed rate of 1.00000000.
# For every other currency, define a (min_rate, max_rate) range.
# Each day's rate is picked randomly (uniform) within that range.
# Add/remove currencies here as needed.
CURRENCY_RANGES = {
    "CAD": (0.71, 0.73),
    # "EUR": (0.90, 0.95),
    # "GBP": (0.77, 0.80),
}

DECIMAL_PLACES = 8

# Set a seed for reproducible output, or None for different results each run.
RANDOM_SEED = None

# ------------------------------------------------------------------
# SCRIPT LOGIC — no need to edit below this line
# ------------------------------------------------------------------


def daterange(start: date, num_days: int):
    """Yield num_days consecutive dates starting from start (inclusive)."""
    if num_days < 1:
        raise ValueError("NUM_DAYS must be at least 1")
    for offset in range(num_days):
        yield start + timedelta(days=offset)


def generate_rows():
    rows = []
    for current_date in daterange(START_DATE, NUM_DAYS):
        # USD is always the base rate.
        rows.append(
            {
                "currency_date": current_date.isoformat(),
                "currency": "USD",
                "rate_to_usd": f"{1.0:.{DECIMAL_PLACES}f}",
            }
        )
        # Other currencies get a random rate within their configured range.
        for currency, (low, high) in CURRENCY_RANGES.items():
            rate = random.uniform(low, high)
            rows.append(
                {
                    "currency_date": current_date.isoformat(),
                    "currency": currency,
                    "rate_to_usd": f"{rate:.{DECIMAL_PLACES}f}",
                }
            )
    return rows


def write_csv(rows, output_file: Path):
    # Make sure the destination folder exists (e.g. "data/") before writing.
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(
            f, fieldnames=["currency_date", "currency", "rate_to_usd"]
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    if RANDOM_SEED is not None:
        random.seed(RANDOM_SEED)

    output_path = FILE_PATH.resolve()
    rows = generate_rows()
    write_csv(rows, output_path)
    end_date = START_DATE + timedelta(days=NUM_DAYS - 1)
    print(f"Wrote {len(rows)} rows to {output_path}")
    print(f"Date range: {START_DATE} to {end_date} ({NUM_DAYS} days)")
    print(f"Currencies: USD, {', '.join(CURRENCY_RANGES.keys())}")


if __name__ == "__main__":
    main()