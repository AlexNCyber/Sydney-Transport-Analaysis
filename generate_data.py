"""
generate_data.py
-----------------
Builds a SYNTHETIC daily patronage dataset for Sydney's public transport
network (Train, Metro, Bus, Ferry, Light Rail), Jan 2019 - Dec 2025.

This is NOT real TfNSW data. It's a realistic stand-in calibrated to
publicly reported patterns so the analysis/visualisation pipeline in
analyze.py can be built and tested end-to-end today:

  - Pre-COVID (2019) baseline volumes roughly reflect published annual
    trip totals (rail + bus each in the hundreds of millions/year;
    ferry and light rail an order of magnitude smaller).
  - The Mar-Oct 2020 COVID collapse and the slow, uneven recovery are
    modelled per mode: bus/ferry/light rail recover to (or above) 2019
    levels by ~2024-25, while rail lags behind, consistent with TfNSW's
    reported patronage recovery figures.
  - Strong weekday vs weekend seasonality is included for every mode.

Swap-in point for real data:
  Once you have a free TfNSW Open Data Hub account + API key, replace
  the body of `build_dataset()` with a loader for the real "Opal
  Patronage" CSV export (see README.md for the exact steps and the
  column-mapping you'll need). Everything downstream in analyze.py
  works off the same tidy schema:
      date | mode | trips
  so no other code needs to change.
"""

from pathlib import Path

import numpy as np
import pandas as pd

MODES = ["Train", "Metro", "Bus", "Ferry", "Light Rail"]

# Approximate pre-COVID (2019) average WEEKDAY trips per mode, per day.
# (Order-of-magnitude, derived from published annual totals.)
BASE_WEEKDAY = {
    "Train": 1_150_000,
    "Metro": 45_000,       # Sydney Metro Northwest opened May 2019
    "Bus": 950_000,
    "Ferry": 32_000,
    "Light Rail": 65_000,
}

# Weekend / weekday multipliers (Mon=0 ... Sun=6)
DOW_MULTIPLIER = {
    0: 1.00, 1: 1.00, 2: 1.00, 3: 1.00, 4: 1.02,   # Mon-Fri
    5: 0.55,                                        # Saturday
    6: 0.38,                                        # Sunday
}

# Recovery trajectory: fraction of 2019 baseline reached, by mode, at
# key milestones. We interpolate between these anchor points.
# Format: {mode: [(date, fraction_of_2019_baseline), ...]}
RECOVERY_ANCHORS = {
    "Train": [
        ("2019-06-01", 1.00), ("2020-04-01", 0.12), ("2020-09-01", 0.45),
        ("2021-06-01", 0.35), ("2021-11-01", 0.55), ("2022-06-01", 0.68),
        ("2023-06-01", 0.75), ("2024-06-01", 0.80), ("2025-12-01", 0.83),
    ],
    "Metro": [
        ("2019-06-01", 1.00), ("2020-04-01", 0.15), ("2020-09-01", 0.50),
        ("2021-06-01", 0.40), ("2021-11-01", 0.65), ("2022-06-01", 0.90),
        ("2023-06-01", 1.15), ("2024-06-01", 1.55), ("2025-12-01", 1.90),
    ],  # Metro grew via network extensions (City & Southwest line, 2024)
    "Bus": [
        ("2019-06-01", 1.00), ("2020-04-01", 0.20), ("2020-09-01", 0.55),
        ("2021-06-01", 0.45), ("2021-11-01", 0.68), ("2022-06-01", 0.85),
        ("2023-06-01", 0.95), ("2024-06-01", 1.00), ("2025-12-01", 1.03),
    ],
    "Ferry": [
        ("2019-06-01", 1.00), ("2020-04-01", 0.10), ("2020-09-01", 0.40),
        ("2021-06-01", 0.35), ("2021-11-01", 0.65), ("2022-06-01", 0.88),
        ("2023-06-01", 0.98), ("2024-06-01", 1.02), ("2025-12-01", 1.05),
    ],
    "Light Rail": [
        ("2019-06-01", 1.00), ("2020-04-01", 0.15), ("2020-09-01", 0.50),
        ("2021-06-01", 0.42), ("2021-11-01", 0.70), ("2022-06-01", 1.05),
        ("2023-06-01", 1.20), ("2024-06-01", 1.25), ("2025-12-01", 1.30),
    ],  # boosted by CBD & South East Light Rail line maturing
}

RNG = np.random.default_rng(42)


def _recovery_series(mode: str, dates: pd.DatetimeIndex) -> np.ndarray:
    anchors = RECOVERY_ANCHORS[mode]
    anchor_dates = pd.to_datetime([a[0] for a in anchors]).astype("int64")
    anchor_vals = np.array([a[1] for a in anchors])
    x = dates.astype("int64").to_numpy()
    return np.interp(x, anchor_dates, anchor_vals)


def build_dataset() -> pd.DataFrame:
    dates = pd.date_range("2019-01-01", "2025-12-31", freq="D")
    frames = []
    for mode in MODES:
        recovery = _recovery_series(mode, dates)
        dow_mult = np.array([DOW_MULTIPLIER[d] for d in dates.dayofweek])
        noise = RNG.normal(1.0, 0.03, size=len(dates))  # +/-3% daily noise

        # A few public-holiday-style dips (Christmas/New Year week, Anzac Day-ish)
        holiday_mask = ((dates.month == 12) & (dates.day >= 25)) | \
                       ((dates.month == 1) & (dates.day <= 1))
        holiday_mult = np.where(holiday_mask, 0.45, 1.0)

        trips = (
            BASE_WEEKDAY[mode] * recovery * dow_mult * noise * holiday_mult
        ).round().astype(int)

        frames.append(pd.DataFrame({"date": dates, "mode": mode, "trips": trips}))

    df = pd.concat(frames, ignore_index=True)
    return df


if __name__ == "__main__":
    df = build_dataset()
    out_dir = Path(__file__).resolve().parent / "data"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "sydney_transport_patronage_synthetic.csv"
    df.to_csv(out_path, index=False)
    print(f"Wrote {len(df):,} rows to {out_path}")
    print(df.head())
