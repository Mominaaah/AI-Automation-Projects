import os
import sys
from datetime import datetime

import pandas as pd
import psycopg2


# ============================================================
# CONFIGURATION
# ============================================================

DATA_FILE = "data/processed/validated_monitoring_data.csv"

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "development_monitoring",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "postgres"),
}


# ============================================================
# HELPERS
# ============================================================

def safe_rate(numerator, denominator):
    """Return a percentage safely."""
    if denominator == 0:
        return 0.0

    return (numerator / denominator) * 100


def calculate_data_quality_score(group):
    """
    Project-defined data quality methodology.

    Completeness = 25%
    Validity     = 25%
    Consistency  = 20%
    Uniqueness   = 15%
    Timeliness   = 15%

    NOTE:
    This is a methodology defined specifically for this project.
    It is NOT an official UNDP methodology.
    """

    required_columns = [
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

    # --------------------------------------------------------
    # Completeness
    # --------------------------------------------------------

    completeness = (
        group[required_columns]
        .notna()
        .mean()
        .mean()
        * 100
    )

    # --------------------------------------------------------
    # Validity
    # --------------------------------------------------------

    validity_checks = pd.Series(True, index=group.index)

    validity_checks &= group["participants_enrolled"] >= 0
    validity_checks &= group["participants_completed"] >= 0
    validity_checks &= group["participants_in_progress"] >= 0
    validity_checks &= group["participants_dropped"] >= 0
    validity_checks &= group["employment_outcomes"] >= 0
    validity_checks &= group["trainers_count"] > 0
    validity_checks &= group["training_hours"] >= 0
    validity_checks &= group["budget_allocated"] >= 0
    validity_checks &= group["budget_spent"] >= 0

    validity = validity_checks.mean() * 100

    # --------------------------------------------------------
    # Consistency
    # --------------------------------------------------------

    consistency_checks = pd.Series(True, index=group.index)

    consistency_checks &= (
        group["participants_completed"]
        + group["participants_in_progress"]
        + group["participants_dropped"]
        <= group["participants_enrolled"]
    )

    consistency_checks &= (
        group["employment_outcomes"]
        <= group["participants_completed"]
    )

    reporting_dates = pd.to_datetime(
        group["reporting_date"],
        errors="coerce"
    )

    submission_dates = pd.to_datetime(
        group["submission_date"],
        errors="coerce"
    )

    consistency_checks &= (
        submission_dates >= reporting_dates
    )

    consistency = consistency_checks.mean() * 100

    # --------------------------------------------------------
    # Uniqueness
    # --------------------------------------------------------

    if len(group) == 0:
        uniqueness = 0.0
    else:
        uniqueness = (
            group["record_id"].nunique()
            / len(group)
            * 100
        )

    # --------------------------------------------------------
    # Timeliness
    # --------------------------------------------------------

    days_to_submission = (
        submission_dates - reporting_dates
    ).dt.days

    timeliness_checks = (
        (days_to_submission >= 0)
        & (days_to_submission <= 30)
    )

    timeliness = timeliness_checks.mean() * 100

    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------

    score = (
        completeness * 0.25
        + validity * 0.25
        + consistency * 0.20
        + uniqueness * 0.15
        + timeliness * 0.15
    )

    return score


# ============================================================
# KPI CALCULATION
# ============================================================

def calculate_group_kpi(group):

    total_enrolled = int(
        group["participants_enrolled"].sum()
    )

    total_completed = int(
        group["participants_completed"].sum()
    )

    total_dropped = int(
        group["participants_dropped"].sum()
    )

    total_employment = int(
        group["employment_outcomes"].sum()
    )

    completion_rate = safe_rate(
        total_completed,
        total_enrolled
    )

    dropout_rate = safe_rate(
        total_dropped,
        total_enrolled
    )

    employment_outcome_rate = safe_rate(
        total_employment,
        total_completed
    )

    avg_training_hours = float(
        group["training_hours"].mean()
    )

    total_trainers = group["trainers_count"].sum()

    trainer_participant_ratio = (
        total_enrolled / total_trainers
        if total_trainers > 0
        else 0.0
    )

    budget_allocated = float(
        group["budget_allocated"].sum()
    )

    budget_spent = float(
        group["budget_spent"].sum()
    )

    budget_utilization_rate = safe_rate(
        budget_spent,
        budget_allocated
    )

    data_quality_score = calculate_data_quality_score(
        group
    )

    reporting_month = pd.to_datetime(
        group["reporting_month"].iloc[0],
        errors="coerce"
    )

    return {
        "reporting_month": (
            reporting_month.date()
            if not pd.isna(reporting_month)
            else None
        ),

        "district": str(group["district"].iloc[0]),

        "training_center_id": str(
            group["training_center_id"].iloc[0]
        ),

        "total_enrolled": int(total_enrolled),

        "total_completed": int(total_completed),

        "total_dropped": int(total_dropped),

        "completion_rate": float(completion_rate),

        "dropout_rate": float(dropout_rate),

        "employment_outcome_rate": float(
            employment_outcome_rate
        ),

        "avg_training_hours": float(
            avg_training_hours
        ),

        "trainer_participant_ratio": float(
            trainer_participant_ratio
        ),

        "budget_allocated": float(
            budget_allocated
        ),

        "budget_spent": float(
            budget_spent
        ),

        "budget_utilization_rate": float(
            budget_utilization_rate
        ),

        "data_quality_score": float(
            data_quality_score
        ),

        "calculated_at": datetime.now(),
    }

# ============================================================
# DATABASE INSERT
# ============================================================

def insert_kpis(kpi_rows):

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        cursor = connection.cursor()

        # Make the script safely re-runnable.
        cursor.execute(
            "DELETE FROM kpi_results;"
        )

        insert_query = """
            INSERT INTO kpi_results (
                reporting_month,
                district,
                training_center_id,
                total_enrolled,
                total_completed,
                total_dropped,
                completion_rate,
                dropout_rate,
                employment_outcome_rate,
                avg_training_hours,
                trainer_participant_ratio,
                budget_allocated,
                budget_spent,
                budget_utilization_rate,
                data_quality_score,
                calculated_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            );
        """

        values = [
            (
                row["reporting_month"],
                row["district"],
                row["training_center_id"],
                row["total_enrolled"],
                row["total_completed"],
                row["total_dropped"],
                row["completion_rate"],
                row["dropout_rate"],
                row["employment_outcome_rate"],
                row["avg_training_hours"],
                row["trainer_participant_ratio"],
                row["budget_allocated"],
                row["budget_spent"],
                row["budget_utilization_rate"],
                row["data_quality_score"],
                row["calculated_at"],
            )
            for row in kpi_rows
        ]

        cursor.executemany(
            insert_query,
            values
        )

        connection.commit()

        print(
            f"KPI RESULTS INSERTED: {cursor.rowcount} rows"
        )

    except Exception:
        connection.rollback()
        raise

    finally:
        cursor.close()
        connection.close()


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("AI-POWERED DEVELOPMENT MONITORING")
    print("KPI CALCULATION ENGINE")
    print("=" * 65)

    # --------------------------------------------------------
    # Load validated data
    # --------------------------------------------------------

    if not os.path.exists(DATA_FILE):

        print(
            f"ERROR: File not found: {DATA_FILE}"
        )

        sys.exit(1)

    print(
        f"\nReading validated data: {DATA_FILE}"
    )

    df = pd.read_csv(DATA_FILE)

    print(
        f"Validated records loaded: {len(df)}"
    )

    if len(df) == 0:

        print(
            "ERROR: No validated records found."
        )

        sys.exit(1)

    # --------------------------------------------------------
    # Convert numeric fields
    # --------------------------------------------------------

    numeric_columns = [
        "participants_enrolled",
        "participants_completed",
        "participants_in_progress",
        "participants_dropped",
        "employment_outcomes",
        "trainers_count",
        "training_hours",
        "budget_allocated",
        "budget_spent",
    ]

    for column in numeric_columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce"
        )

    # --------------------------------------------------------
    # Calculate KPIs by month + district + center
    # --------------------------------------------------------

    group_columns = [
        "reporting_month",
        "district",
        "training_center_id",
    ]

    grouped = df.groupby(
        group_columns,
        dropna=False
    )

    print(
        f"KPI groups identified: {len(grouped)}"
    )

    kpi_rows = []

    for _, group in grouped:

        kpi = calculate_group_kpi(group)

        kpi_rows.append(kpi)

    # --------------------------------------------------------
    # Insert into PostgreSQL
    # --------------------------------------------------------

    print(
        "\nLoading KPI results into PostgreSQL..."
    )

    insert_kpis(kpi_rows)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nKPI ENGINE COMPLETE")
    print("-" * 40)

    print(
        f"Validated records: {len(df)}"
    )

    print(
        f"KPI rows generated: {len(kpi_rows)}"
    )

    print(
        "KPI grain: reporting_month + district + training_center_id"
    )

    print(
        "\nData-quality methodology:"
    )

    print(
        "Completeness  25%"
    )

    print(
        "Validity      25%"
    )

    print(
        "Consistency   20%"
    )

    print(
        "Uniqueness    15%"
    )

    print(
        "Timeliness    15%"
    )

    print(
        "\nNOTE: Data-quality scoring is project-defined "
        "and is not an official UNDP methodology."
    )


if __name__ == "__main__":
    main()