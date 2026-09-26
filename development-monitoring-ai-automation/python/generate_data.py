import pandas as pd
import numpy as np
from faker import Faker
from pathlib import Path
import random

fake = Faker()
random.seed(42)
np.random.seed(42)

# -----------------------------
# Configuration
# -----------------------------

NUM_RECORDS = 1800

districts = [
    "District A",
    "District B",
    "District C",
    "District D",
    "District E",
    "District F",
    "District G",
    "District H"
]

training_centers = [
    f"Center {i:02d}" for i in range(1, 21)
]

program_types = [
    "Digital Skills",
    "Vocational Training",
    "Entrepreneurship",
    "Career Readiness"
]

statuses = [
    "Completed",
    "In Progress",
    "Dropped Out"
]

months = pd.date_range(
    start="2025-01-01",
    end="2025-12-01",
    freq="MS"
)

# -----------------------------
# Generate base dataset
# -----------------------------

records = []

for i in range(NUM_RECORDS):

    district = random.choice(districts)
    center = random.choice(training_centers)
    program = random.choice(program_types)
    month = random.choice(months)

    participants_enrolled = random.randint(20, 100)

    completion_rate = np.random.uniform(0.55, 0.95)

    participants_completed = int(
        participants_enrolled * completion_rate
    )

    participants_dropped = random.randint(
        0,
        max(1, participants_enrolled - participants_completed)
    )

    participants_in_progress = max(
        0,
        participants_enrolled
        - participants_completed
        - participants_dropped
    )

    budget_allocated = random.randint(50000, 250000)

    budget_spent = int(
        budget_allocated * np.random.uniform(0.55, 1.05)
    )

    records.append({
        "record_id": i + 1,
        "month": month.strftime("%Y-%m-%d"),
        "district": district,
        "training_center": center,
        "program_type": program,
        "participants_enrolled": participants_enrolled,
        "participants_completed": participants_completed,
        "participants_in_progress": participants_in_progress,
        "participants_dropped": participants_dropped,
        "budget_allocated": budget_allocated,
        "budget_spent": budget_spent
    })


df = pd.DataFrame(records)

# -----------------------------
# Inject intentional data issues
# -----------------------------

# 1. Missing district values
missing_indices = np.random.choice(
    df.index,
    size=20,
    replace=False
)

df.loc[missing_indices, "district"] = np.nan


# 2. Invalid negative values
negative_indices = np.random.choice(
    df.index,
    size=10,
    replace=False
)

df.loc[
    negative_indices,
    "participants_enrolled"
] = -5


# 3. Duplicate records
duplicates = df.sample(
    15,
    random_state=42
)

df = pd.concat(
    [df, duplicates],
    ignore_index=True
)


# 4. Invalid completion counts
invalid_indices = np.random.choice(
    df.index,
    size=10,
    replace=False
)

df.loc[
    invalid_indices,
    "participants_completed"
] = (
    df.loc[invalid_indices, "participants_enrolled"] + 20
)


# 5. Extreme budget values / anomalies
anomaly_indices = np.random.choice(
    df.index,
    size=10,
    replace=False
)

df.loc[
    anomaly_indices,
    "budget_spent"
] = (
    df.loc[anomaly_indices, "budget_allocated"] * 3
)


# -----------------------------
# Save dataset
# -----------------------------

output_dir = Path("data/raw")
output_dir.mkdir(
    parents=True,
    exist_ok=True
)

output_file = output_dir / "development_monitoring_data.csv"

df.to_csv(
    output_file,
    index=False
)

print("=" * 60)
print("Synthetic dataset generated successfully")
print("=" * 60)
print(f"Records: {len(df)}")
print(f"Columns: {len(df.columns)}")
print(f"Output: {output_file}")
print()
print("Missing district values:",
      df["district"].isna().sum())
print("Negative enrollment values:",
      (df["participants_enrolled"] < 0).sum())
print("Potential duplicate rows:",
      df.duplicated().sum())
print()
print(df.head())