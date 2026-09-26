import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path


# ============================================================
# CONFIGURATION
# ============================================================

INPUT_FILE = Path("data/processed/program_monitoring_prepared.csv")
OUTPUT_FILE = Path("data/processed/validation_results.csv")
CENTERS_FILE = Path("data/processed/training_centers.csv")

VALIDATION_TIMESTAMP = datetime.now().isoformat(timespec="seconds")


# ============================================================
# STORAGE FOR VALIDATION RESULTS
# ============================================================

validation_results = []


def add_validation(
    record_id,
    validation_rule,
    issue_type,
    severity,
    field_name,
    actual_value,
    expected_condition,
    status="FAIL",
):
    """
    Add one validation finding to the results list.
    """

    validation_results.append(
        {
            "record_id": record_id,
            "validation_rule": validation_rule,
            "issue_type": issue_type,
            "severity": severity,
            "field_name": field_name,
            "actual_value": str(actual_value),
            "expected_condition": expected_condition,
            "status": status,
            "validation_timestamp": VALIDATION_TIMESTAMP,
        }
    )


# ============================================================
# LOAD DATA
# ============================================================

print("=" * 70)
print("AI-POWERED DEVELOPMENT MONITORING PLATFORM")
print("VALIDATION ENGINE")
print("=" * 70)

print("\nLoading prepared monitoring data...")

if not INPUT_FILE.exists():
    raise FileNotFoundError(
        f"Input file not found: {INPUT_FILE}"
    )

if not CENTERS_FILE.exists():
    raise FileNotFoundError(
        f"Training center file not found: {CENTERS_FILE}"
    )

df = pd.read_csv(INPUT_FILE)

centers = pd.read_csv(CENTERS_FILE)

print(f"Monitoring records loaded: {len(df)}")
print(f"Training centers loaded: {len(centers)}")


# ============================================================
# PREPARE DATE COLUMNS
# ============================================================

# errors='coerce' converts invalid dates into NaT.
# This is essential because our prepared dataset intentionally
# contains an invalid date for validation testing.

df["reporting_month_parsed"] = pd.to_datetime(
    df["reporting_month"],
    errors="coerce"
)

df["reporting_date_parsed"] = pd.to_datetime(
    df["reporting_date"],
    errors="coerce"
)

df["submission_date_parsed"] = pd.to_datetime(
    df["submission_date"],
    errors="coerce"
)


# ============================================================
# V001 — REQUIRED FIELD MISSING
# ============================================================

required_fields = [
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

for field in required_fields:

    missing_mask = (
        df[field].isna()
        | df[field].astype(str).str.strip().eq("")
        | df[field].astype(str).str.lower().isin(
            ["nan", "none", "null"]
        )
    )

    for idx in df.index[missing_mask]:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V001",
            issue_type="required_field_missing",
            severity="HIGH",
            field_name=field,
            actual_value=df.loc[idx, field],
            expected_condition="Required field must contain a valid value",
        )


# ============================================================
# V002 — COMPLETED > ENROLLED
# ============================================================

mask = (
    df["participants_completed"].notna()
    & df["participants_enrolled"].notna()
    & (
        df["participants_completed"]
        > df["participants_enrolled"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V002",
        issue_type="completion_exceeds_enrollment",
        severity="HIGH",
        field_name="participants_completed",
        actual_value=df.loc[idx, "participants_completed"],
        expected_condition="participants_completed <= participants_enrolled",
    )


# ============================================================
# V003 — DROPPED > ENROLLED
# ============================================================

mask = (
    df["participants_dropped"].notna()
    & df["participants_enrolled"].notna()
    & (
        df["participants_dropped"]
        > df["participants_enrolled"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V003",
        issue_type="dropout_exceeds_enrollment",
        severity="HIGH",
        field_name="participants_dropped",
        actual_value=df.loc[idx, "participants_dropped"],
        expected_condition="participants_dropped <= participants_enrolled",
    )


# ============================================================
# V004 — EMPLOYMENT OUTCOMES > COMPLETED
# ============================================================

mask = (
    df["employment_outcomes"].notna()
    & df["participants_completed"].notna()
    & (
        df["employment_outcomes"]
        > df["participants_completed"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V004",
        issue_type="employment_outcomes_exceed_completed",
        severity="HIGH",
        field_name="employment_outcomes",
        actual_value=df.loc[idx, "employment_outcomes"],
        expected_condition="employment_outcomes <= participants_completed",
    )


# ============================================================
# V005 — BUDGET SPENT > ALLOCATED
# ============================================================

mask = (
    df["budget_spent"].notna()
    & df["budget_allocated"].notna()
    & (
        df["budget_spent"]
        > df["budget_allocated"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V005",
        issue_type="budget_spent_exceeds_allocated",
        severity="HIGH",
        field_name="budget_spent",
        actual_value=df.loc[idx, "budget_spent"],
        expected_condition="budget_spent <= budget_allocated",
    )


# ============================================================
# V006 — INVALID DATE
# ============================================================

date_columns = {
    "reporting_month": "reporting_month_parsed",
    "reporting_date": "reporting_date_parsed",
    "submission_date": "submission_date_parsed",
}

for original_field, parsed_field in date_columns.items():

    invalid_mask = (
        df[original_field].notna()
        & df[parsed_field].isna()
    )

    for idx in df.index[invalid_mask]:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V006",
            issue_type="invalid_date",
            severity="HIGH",
            field_name=original_field,
            actual_value=df.loc[idx, original_field],
            expected_condition="Field must contain a valid calendar date",
        )


# ============================================================
# V007 — UNKNOWN / INCONSISTENT DISTRICT
# ============================================================

known_districts = set(
    centers["district"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

for idx in df.index:

    district = df.loc[idx, "district"]

    if pd.isna(district):
        continue

    district = str(district).strip()

    if district not in known_districts:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V007",
            issue_type="unknown_district",
            severity="HIGH",
            field_name="district",
            actual_value=district,
            expected_condition="District must exist in the training center reference data",
        )


# ============================================================
# V008 — DUPLICATE BUSINESS RECORD
# ============================================================

business_key = [
    "record_id",
    "reporting_month",
    "training_center_id",
    "program_type",
]

duplicate_mask = df.duplicated(
    subset=business_key,
    keep=False
)

for idx in df.index[duplicate_mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V008",
        issue_type="duplicate_monitoring_record",
        severity="HIGH",
        field_name="record_id",
        actual_value=df.loc[idx, "record_id"],
        expected_condition=(
            "record_id + reporting_month + "
            "training_center_id + program_type "
            "should uniquely identify a monitoring record"
        ),
    )


# ============================================================
# V009 — PARTICIPANT COMPONENTS > ENROLLMENT
# ============================================================

participant_columns = [
    "participants_completed",
    "participants_in_progress",
    "participants_dropped",
]

participant_sum = df[participant_columns].sum(
    axis=1,
    skipna=False
)

mask = (
    participant_sum.notna()
    & df["participants_enrolled"].notna()
    & (
        participant_sum
        > df["participants_enrolled"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V009",
        issue_type="participant_components_exceed_enrollment",
        severity="HIGH",
        field_name="participant_status_counts",
        actual_value=(
            f"completed={df.loc[idx, 'participants_completed']}, "
            f"in_progress={df.loc[idx, 'participants_in_progress']}, "
            f"dropped={df.loc[idx, 'participants_dropped']}, "
            f"total={participant_sum.loc[idx]}"
        ),
        expected_condition=(
            "completed + in_progress + dropped "
            "<= participants_enrolled"
        ),
    )


# ============================================================
# V010 — INVALID TRAINER COUNT
# ============================================================

mask = (
    df["trainers_count"].notna()
    & (
        (df["trainers_count"] <= 0)
        | (df["trainers_count"] > 50)
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V010",
        issue_type="invalid_trainer_count",
        severity="MEDIUM",
        field_name="trainers_count",
        actual_value=df.loc[idx, "trainers_count"],
        expected_condition="trainers_count must be between 1 and 50",
    )


# ============================================================
# V011 — UNKNOWN TRAINING CENTER
# ============================================================

known_centers = set(
    centers["training_center_id"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

for idx in df.index:

    center_id = df.loc[idx, "training_center_id"]

    if pd.isna(center_id):
        continue

    center_id = str(center_id).strip()

    if center_id not in known_centers:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V011",
            issue_type="unknown_training_center",
            severity="HIGH",
            field_name="training_center_id",
            actual_value=center_id,
            expected_condition="training_center_id must exist in training_centers reference table",
        )


# ============================================================
# V012 — INVALID REPORTING MONTH
# ============================================================

mask = (
    df["reporting_month_parsed"].notna()
    & (
        df["reporting_month_parsed"].dt.day
        != 1
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V012",
        issue_type="invalid_reporting_month",
        severity="MEDIUM",
        field_name="reporting_month",
        actual_value=df.loc[idx, "reporting_month"],
        expected_condition="reporting_month must represent the first day of its calendar month",
    )


# ============================================================
# V013 — NEGATIVE PARTICIPANT VALUE
# ============================================================

for field in participant_columns + [
    "participants_enrolled",
    "employment_outcomes",
]:

    mask = (
        df[field].notna()
        & (df[field] < 0)
    )

    for idx in df.index[mask]:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V013",
            issue_type="negative_participant_value",
            severity="HIGH",
            field_name=field,
            actual_value=df.loc[idx, field],
            expected_condition=f"{field} must be >= 0",
        )


# ============================================================
# V014 — INVALID BUDGET
# ============================================================

for field in [
    "budget_allocated",
    "budget_spent",
]:

    mask = (
        df[field].notna()
        & (df[field] < 0)
    )

    for idx in df.index[mask]:

        add_validation(
            record_id=df.loc[idx, "record_id"],
            validation_rule="V014",
            issue_type="negative_budget",
            severity="HIGH",
            field_name=field,
            actual_value=df.loc[idx, field],
            expected_condition=f"{field} must be >= 0",
        )


# ============================================================
# V015 — SUBMISSION DATE BEFORE REPORTING PERIOD
# ============================================================

mask = (
    df["submission_date_parsed"].notna()
    & df["reporting_month_parsed"].notna()
    & (
        df["submission_date_parsed"]
        < df["reporting_month_parsed"]
    )
)

for idx in df.index[mask]:

    add_validation(
        record_id=df.loc[idx, "record_id"],
        validation_rule="V015",
        issue_type="submission_before_reporting_period",
        severity="HIGH",
        field_name="submission_date",
        actual_value=df.loc[idx, "submission_date"],
        expected_condition="submission_date must be on or after reporting_month",
    )


# ============================================================
# DATAFRAME CREATION
# ============================================================

results_df = pd.DataFrame(
    validation_results
)


# ============================================================
# ADD VALIDATION ID
# ============================================================

if len(results_df) > 0:

    results_df.insert(
        0,
        "validation_id",
        range(1, len(results_df) + 1)
    )

else:

    results_df = pd.DataFrame(
        columns=[
            "validation_id",
            "record_id",
            "validation_rule",
            "issue_type",
            "severity",
            "field_name",
            "actual_value",
            "expected_condition",
            "status",
            "validation_timestamp",
        ]
    )


# ============================================================
# SAVE RESULTS
# ============================================================

OUTPUT_FILE.parent.mkdir(
    parents=True,
    exist_ok=True
)

results_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# ============================================================
# SUMMARY
# ============================================================

print("\n" + "=" * 70)
print("VALIDATION COMPLETE")
print("=" * 70)

print(f"\nTotal validation findings: {len(results_df)}")

if len(results_df) > 0:

    print("\nFindings by validation rule:")
    print(
        results_df["validation_rule"]
        .value_counts()
        .sort_index()
        .to_string()
    )

    print("\nFindings by severity:")
    print(
        results_df["severity"]
        .value_counts()
        .to_string()
    )

    print("\nFindings by issue type:")
    print(
        results_df["issue_type"]
        .value_counts()
        .to_string()
    )

print(f"\nOutput file:")
print(f"  {OUTPUT_FILE}")

print("\nValidation engine finished successfully.")