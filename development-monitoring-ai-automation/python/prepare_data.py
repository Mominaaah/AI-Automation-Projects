import pandas as pd
import numpy as np
from pathlib import Path
import random


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/raw/development_monitoring_data.csv")

OUTPUT_DIR = Path("data/processed")

MONITORING_OUTPUT = OUTPUT_DIR / "program_monitoring_prepared.csv"
CENTERS_OUTPUT = OUTPUT_DIR / "training_centers.csv"
ISSUES_OUTPUT = OUTPUT_DIR / "intentional_issues.csv"

random.seed(42)
np.random.seed(42)


# ============================================================
# CREATE OUTPUT DIRECTORY
# ============================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# LOAD EXISTING DATASET
# ============================================================

print("=" * 70)
print("AI-POWERED DEVELOPMENT MONITORING PLATFORM")
print("Data Preparation")
print("=" * 70)

print("\nLoading existing dataset...")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

print(f"Loaded rows: {len(df)}")


# ============================================================
# BASIC SAFETY CHECK
# ============================================================

required_columns = [
    "record_id",
    "month",
    "district",
    "training_center",
    "program_type",
    "participants_enrolled",
    "participants_completed",
    "participants_in_progress",
    "participants_dropped",
    "budget_allocated",
    "budget_spent",
]

missing_columns = [
    column
    for column in required_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing expected columns: {missing_columns}"
    )


# ============================================================
# PRESERVE ORIGINAL RECORD COUNT
# ============================================================

original_row_count = len(df)


# ============================================================
# RENAME EXISTING COLUMNS
# ============================================================

df = df.rename(
    columns={
        "month": "reporting_month",
        "training_center": "training_center_id",
    }
)


# ============================================================
# STANDARDIZE EXISTING IDENTIFIERS
# ============================================================

df["training_center_id"] = (
    df["training_center_id"]
    .astype(str)
    .str.strip()
    .str.replace(" ", "_")
    .str.upper()
)

# Example:
# Center 01 -> CENTER_01


# ============================================================
# STANDARDIZE REPORTING MONTH
# ============================================================

df["reporting_month"] = pd.to_datetime(
    df["reporting_month"],
    errors="coerce"
)


# ============================================================
# CREATE REPORTING DATE
# ============================================================

# Reporting date = last calendar day of reporting month

df["reporting_date"] = (
    df["reporting_month"]
    + pd.offsets.MonthEnd(0)
)


# ============================================================
# CREATE SUBMISSION DATE
# ============================================================

# Normally reports are submitted within a few days
# after the reporting period.

submission_delays = np.random.randint(
    1,
    8,
    size=len(df)
)

df["submission_date"] = (
    df["reporting_date"]
    + pd.to_timedelta(
        submission_delays,
        unit="D"
    )
)


# ============================================================
# CREATE TRAINER COUNTS
# ============================================================

# Approximate trainer requirement based on participant volume.
# This creates realistic variation rather than a fixed ratio.

df["trainers_count"] = (
    np.ceil(
        df["participants_enrolled"]
        / np.random.uniform(
            12,
            22,
            size=len(df)
        )
    )
    .astype(int)
)

df["trainers_count"] = df["trainers_count"].clip(
    lower=1,
    upper=15
)


# ============================================================
# CREATE EMPLOYMENT OUTCOMES
# ============================================================

# Employment outcomes are based on completed participants.
# This intentionally creates valid values by default.

employment_rate = np.random.uniform(
    0.20,
    0.70,
    size=len(df)
)

df["employment_outcomes"] = (
    df["participants_completed"]
    * employment_rate
).round().astype(int)

df["employment_outcomes"] = (
    df["employment_outcomes"]
    .clip(lower=0)
)


# ============================================================
# CREATE TRAINING HOURS
# ============================================================

# Added because the KPI design includes average training hours.

df["training_hours"] = np.random.randint(
    20,
    121,
    size=len(df)
)


# ============================================================
# CREATE DATA SOURCE
# ============================================================

data_sources = [
    "monthly_center_report",
    "program_database",
    "manual_submission",
]

df["data_source"] = np.random.choice(
    data_sources,
    size=len(df),
    p=[0.65, 0.25, 0.10]
)


# ============================================================
# CREATE TRAINING CENTER REFERENCE TABLE
# ============================================================

# The existing dataset contains Center 01 ... Center 20.
# We preserve those references and add 10 additional centers
# to create a richer reference table.

center_ids = [
    f"CENTER_{i:02d}"
    for i in range(1, 31)
]

districts = [
    "District A",
    "District B",
    "District C",
    "District D",
    "District E",
    "District F",
    "District G",
    "District H",
    "District I",
    "District J",
]

center_types = [
    "Government",
    "Partner",
    "Community",
]

center_rows = []

for i, center_id in enumerate(center_ids):

    district = districts[i % len(districts)]

    center_rows.append(
        {
            "training_center_id": center_id,
            "district": district,
            "center_name": f"{district} Training Center {i + 1:02d}",
            "center_type": random.choice(center_types),
            "capacity": random.choice(
                [60, 80, 100, 120, 150]
            ),
            "active_status": True,
        }
    )

training_centers = pd.DataFrame(center_rows)


# ============================================================
# ALIGN EXISTING CENTER IDS WITH REFERENCE TABLE
# ============================================================

# Existing Center 01 becomes CENTER_01, etc.
#
# The original dataset only contains Centers 01-20.
# Therefore those IDs are guaranteed to exist in the
# reference table.

# ============================================================
# CONTROLLED INTENTIONAL ISSUES
# ============================================================

issues = []


def add_issue(
    record_id,
    issue_type,
    field_name,
    actual_value,
    expected_condition,
    severity,
    issue_category="validation_error",
):
    issues.append(
        {
            "issue_id": len(issues) + 1,
            "record_id": record_id,
            "issue_type": issue_type,
            "field_name": field_name,
            "actual_value": str(actual_value),
            "expected_condition": expected_condition,
            "severity": severity,
            "issue_category": issue_category,
        }
    )


# ============================================================
# ISSUE 1 — MISSING VALUE
# ============================================================

idx = df.index[10]

df.loc[idx, "district"] = np.nan

add_issue(
    df.loc[idx, "record_id"],
    "missing_required_value",
    "district",
    "NULL",
    "district must not be NULL",
    "MEDIUM",
)


# ============================================================
# ISSUE 2 — COMPLETED > ENROLLED
# ============================================================

idx = df.index[25]

enrolled = int(df.loc[idx, "participants_enrolled"])

df.loc[idx, "participants_completed"] = enrolled + 15

add_issue(
    df.loc[idx, "record_id"],
    "completion_exceeds_enrollment",
    "participants_completed",
    enrolled + 15,
    "participants_completed <= participants_enrolled",
    "HIGH",
)


# ============================================================
# ISSUE 3 — DROPPED > ENROLLED
# ============================================================

idx = df.index[40]

enrolled = int(df.loc[idx, "participants_enrolled"])

df.loc[idx, "participants_dropped"] = enrolled + 5

add_issue(
    df.loc[idx, "record_id"],
    "dropout_exceeds_enrollment",
    "participants_dropped",
    enrolled + 5,
    "participants_dropped <= participants_enrolled",
    "HIGH",
)


# ============================================================
# ISSUE 4 — IN PROGRESS > ENROLLED
# ============================================================

idx = df.index[55]

enrolled = int(df.loc[idx, "participants_enrolled"])

df.loc[idx, "participants_in_progress"] = enrolled + 10

add_issue(
    df.loc[idx, "record_id"],
    "in_progress_exceeds_enrollment",
    "participants_in_progress",
    enrolled + 10,
    "participants_in_progress <= participants_enrolled",
    "HIGH",
)


# ============================================================
# ISSUE 5 — PARTICIPANT TOTAL EXCEEDS ENROLLMENT
# ============================================================

idx = df.index[70]

enrolled = int(df.loc[idx, "participants_enrolled"])

df.loc[idx, "participants_completed"] = int(
    enrolled * 0.70
)

df.loc[idx, "participants_in_progress"] = int(
    enrolled * 0.50
)

df.loc[idx, "participants_dropped"] = int(
    enrolled * 0.20
)

add_issue(
    df.loc[idx, "record_id"],
    "participant_components_exceed_enrollment",
    "participants_completed,participants_in_progress,participants_dropped",
    (
        int(df.loc[idx, "participants_completed"])
        + int(df.loc[idx, "participants_in_progress"])
        + int(df.loc[idx, "participants_dropped"])
    ),
    "completed + in_progress + dropped <= enrolled",
    "HIGH",
)


# ============================================================
# ISSUE 6 — EMPLOYMENT OUTCOMES > COMPLETED
# ============================================================

idx = df.index[85]

completed = int(df.loc[idx, "participants_completed"])

df.loc[idx, "employment_outcomes"] = completed + 10

add_issue(
    df.loc[idx, "record_id"],
    "employment_outcomes_exceed_completed",
    "employment_outcomes",
    completed + 10,
    "employment_outcomes <= participants_completed",
    "HIGH",
)


# ============================================================
# ISSUE 7 — BUDGET SPENT > ALLOCATED
# ============================================================

idx = df.index[100]

allocated = float(df.loc[idx, "budget_allocated"])

df.loc[idx, "budget_spent"] = allocated * 1.50

add_issue(
    df.loc[idx, "record_id"],
    "budget_spent_exceeds_allocated",
    "budget_spent",
    df.loc[idx, "budget_spent"],
    "budget_spent <= budget_allocated",
    "HIGH",
)


# ============================================================
# ISSUE 8 — INVALID TRAINER COUNT
# ============================================================

idx = df.index[115]

df.loc[idx, "trainers_count"] = 0

add_issue(
    df.loc[idx, "record_id"],
    "invalid_trainer_count",
    "trainers_count",
    0,
    "trainers_count must be greater than 0",
    "MEDIUM",
)


# ============================================================
# ISSUE 9 — UNKNOWN TRAINING CENTER
# ============================================================

idx = df.index[130]

df.loc[idx, "training_center_id"] = "CENTER_999"

add_issue(
    df.loc[idx, "record_id"],
    "unknown_training_center",
    "training_center_id",
    "CENTER_999",
    "training_center_id must exist in training_centers",
    "HIGH",
)


# ============================================================
# ISSUE 10 — INVALID DISTRICT
# ============================================================

idx = df.index[145]

df.loc[idx, "district"] = "District ZZZ"

add_issue(
    df.loc[idx, "record_id"],
    "unknown_district",
    "district",
    "District ZZZ",
    "district must exist in approved district list",
    "HIGH",
)


# ============================================================
# ISSUE 11 — DISTRICT/CENTER MISMATCH
# ============================================================

idx = df.index[160]

center_id = df.loc[idx, "training_center_id"]

center_number = int(
    center_id.split("_")[1]
)

correct_district = districts[
    (center_number - 1) % len(districts)
]

wrong_district = "District J"

if correct_district == wrong_district:
    wrong_district = "District I"

df.loc[idx, "district"] = wrong_district

add_issue(
    df.loc[idx, "record_id"],
    "district_center_mismatch",
    "district",
    wrong_district,
    f"district must match {center_id} reference district",
    "HIGH",
)


# ============================================================
# ISSUE 12 — INVALID DATE
# ============================================================

idx = df.index[175]

# Use an impossible calendar date as a controlled test value.
# We temporarily convert the column to object so the raw
# invalid value can be preserved for the validation engine.

df["submission_date"] = df["submission_date"].astype(object)

df.loc[idx, "submission_date"] = "2025-99-99"

add_issue(
    df.loc[idx, "record_id"],
    "invalid_submission_date",
    "submission_date",
    "2025-99-99",
    "submission_date must be a valid calendar date",
    "HIGH",
)


# ============================================================
# ISSUE 13 — NEGATIVE PARTICIPANT VALUE
# ============================================================

idx = df.index[190]

df.loc[idx, "participants_dropped"] = -3

add_issue(
    df.loc[idx, "record_id"],
    "negative_participant_value",
    "participants_dropped",
    -3,
    "participant counts must be >= 0",
    "HIGH",
)


# ============================================================
# ISSUE 14 — NEGATIVE BUDGET
# ============================================================

idx = df.index[205]

df.loc[idx, "budget_spent"] = -1000

add_issue(
    df.loc[idx, "record_id"],
    "negative_budget",
    "budget_spent",
    -1000,
    "budget values must be >= 0",
    "HIGH",
)


# ============================================================
# ISSUE 15 — LATE SUBMISSION
# ============================================================

idx = df.index[220]

reporting_date = pd.to_datetime(
    df.loc[idx, "reporting_date"]
)

late_date = reporting_date + pd.Timedelta(
    days=35
)

df.loc[idx, "submission_date"] = late_date

add_issue(
    df.loc[idx, "record_id"],
    "late_submission",
    "submission_date",
    late_date,
    "submission should normally occur within 10 days",
    "MEDIUM",
)


# ============================================================
# ISSUE 16 — DUPLICATE BUSINESS RECORD
# ============================================================

duplicate_source = df.iloc[250].copy()

duplicate_record = duplicate_source.copy()

# Keep the same record_id and business fields.
# This creates a genuine duplicate row.

df = pd.concat(
    [
        df,
        pd.DataFrame([duplicate_record]),
    ],
    ignore_index=True
)

add_issue(
    duplicate_record["record_id"],
    "duplicate_monitoring_record",
    "record_id",
    duplicate_record["record_id"],
    "record_id + reporting_month + training_center_id + program_type should be unique",
    "HIGH",
)

# ============================================================
# REALISTIC VALID ANOMALIES
# ============================================================

# These are intentionally unusual but NOT invalid.
# They should later be detected by anomaly detection.

anomaly_records = []


# ------------------------------------------------------------
# ANOMALY 1 — HIGH BUT VALID ENROLLMENT
# ------------------------------------------------------------

idx = df.index[300]

df.loc[idx, "participants_enrolled"] = 450

# Keep participant totals valid.
df.loc[idx, "participants_completed"] = 300
df.loc[idx, "participants_in_progress"] = 120
df.loc[idx, "participants_dropped"] = 30

anomaly_records.append(
    {
        "record_id": df.loc[idx, "record_id"],
        "indicator": "participants_enrolled",
        "observed_value": 450,
        "expected_value_or_range": "Normally 50-150 for this center",
        "detection_method": "center_level_historical_baseline",
        "severity": "HIGH",
        "reason": "Unusual enrollment volume requiring verification.",
        "issue_category": "anomaly",
    }
)


# ------------------------------------------------------------
# ANOMALY 2 — HIGH VALID BUDGET
# ------------------------------------------------------------

idx = df.index[350]

allocated = 500000
spent = 480000

df.loc[idx, "budget_allocated"] = allocated
df.loc[idx, "budget_spent"] = spent

anomaly_records.append(
    {
        "record_id": df.loc[idx, "record_id"],
        "indicator": "budget_spent",
        "observed_value": spent,
        "expected_value_or_range": "Normally below 250000",
        "detection_method": "IQR",
        "severity": "MEDIUM",
        "reason": "Budget expenditure is unusually high compared with historical observations.",
        "issue_category": "anomaly",
    }
)


# ------------------------------------------------------------
# ANOMALY 3 — VALID TRAINER SPIKE
# ------------------------------------------------------------

idx = df.index[400]

df.loc[idx, "trainers_count"] = 25

anomaly_records.append(
    {
        "record_id": df.loc[idx, "record_id"],
        "indicator": "trainers_count",
        "observed_value": 25,
        "expected_value_or_range": "Normally 2-10 trainers",
        "detection_method": "center_level_historical_baseline",
        "severity": "HIGH",
        "reason": "Trainer count is unusually high for this center and requires verification.",
        "issue_category": "anomaly",
    }
)


# ------------------------------------------------------------
# ANOMALY 4 — VALID ENROLLMENT DROP
# ------------------------------------------------------------

idx = df.index[450]

df.loc[idx, "participants_enrolled"] = 25
df.loc[idx, "participants_completed"] = 18
df.loc[idx, "participants_in_progress"] = 6
df.loc[idx, "participants_dropped"] = 1

anomaly_records.append(
    {
        "record_id": df.loc[idx, "record_id"],
        "indicator": "participants_enrolled",
        "observed_value": 25,
        "expected_value_or_range": "Normally 70-120",
        "detection_method": "historical_percentage_change",
        "severity": "MEDIUM",
        "reason": "Enrollment decreased substantially compared with the center's historical pattern.",
        "issue_category": "anomaly",
    }
)


# ============================================================
# ADD ANOMALIES TO ISSUE DOCUMENTATION
# ============================================================

for anomaly in anomaly_records:

    issues.append(
        {
            "issue_id": len(issues) + 1,
            "record_id": anomaly["record_id"],
            "issue_type": anomaly["indicator"],
            "field_name": anomaly["indicator"],
            "actual_value": str(anomaly["observed_value"]),
            "expected_condition": anomaly[
                "expected_value_or_range"
            ],
            "severity": anomaly["severity"],
            "issue_category": "anomaly",
        }
    )


# ============================================================
# REORDER MAIN TABLE
# ============================================================

column_order = [
    "record_id",
    "reporting_month",
    "reporting_date",
    "submission_date",
    "district",
    "training_center_id",
    "program_type",
    "participants_enrolled",
    "participants_completed",
    "participants_in_progress",
    "participants_dropped",
    "employment_outcomes",
    "trainers_count",
    "training_hours",
    "budget_allocated",
    "budget_spent",
    "data_source",
]

df = df[column_order]


# ============================================================
# SAVE FILES
# ============================================================

df.to_csv(
    MONITORING_OUTPUT,
    index=False
)

training_centers.to_csv(
    CENTERS_OUTPUT,
    index=False
)

issues_df = pd.DataFrame(issues)

issues_df.to_csv(
    ISSUES_OUTPUT,
    index=False
)


# ============================================================
# FINAL SAFETY CHECKS
# ============================================================

print("\n" + "=" * 70)
print("DATA PREPARATION COMPLETE")
print("=" * 70)

print(f"\nOriginal records: {original_row_count}")
print(f"Prepared records: {len(df)}")

print(
    "\nNote: one controlled duplicate was added "
    "for validation testing."
)

print(f"\nMonitoring table:")
print(f"  {MONITORING_OUTPUT}")

print(f"\nTraining center table:")
print(f"  {CENTERS_OUTPUT}")

print(f"\nIssue documentation:")
print(f"  {ISSUES_OUTPUT}")

print("\nFiles created successfully.")

print("\nPrepared columns:")
for column in df.columns:
    print(f"  - {column}")

print("\nControlled issues:")
print(
    issues_df["issue_category"]
    .value_counts()
)

print("\nFirst 5 monitoring records:")
print(
    df.head().to_string(index=False)
)