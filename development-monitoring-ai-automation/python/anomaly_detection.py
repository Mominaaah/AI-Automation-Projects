import os
import sys
from datetime import datetime

import numpy as np
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

def add_anomaly(
    anomalies,
    record_id,
    indicator,
    observed_value,
    expected_value_or_range,
    detection_method,
    severity,
    reason,
):
    """Add one anomaly finding."""

    anomalies.append(
        {
            "record_id": int(record_id),
            "indicator": indicator,
            "observed_value": float(observed_value),
            "expected_value_or_range": expected_value_or_range,
            "detection_method": detection_method,
            "severity": severity,
            "reason": reason,
            "review_status": "PENDING",
            "detected_at": datetime.now(),
        }
    )


def calculate_iqr_bounds(series):
    """Calculate robust IQR-based lower and upper bounds."""

    clean = pd.to_numeric(
        series,
        errors="coerce"
    ).dropna()

    if len(clean) < 10:
        return None, None

    q1 = clean.quantile(0.25)
    q3 = clean.quantile(0.75)

    iqr = q3 - q1

    lower = q1 - (1.5 * iqr)
    upper = q3 + (1.5 * iqr)

    return lower, upper


# ============================================================
# BUSINESS-RULE ANOMALIES
# ============================================================

def detect_business_anomalies(df, anomalies):

    for _, row in df.iterrows():

        record_id = row["record_id"]

        enrolled = row["participants_enrolled"]
        completed = row["participants_completed"]
        dropped = row["participants_dropped"]
        employment = row["employment_outcomes"]
        trainers = row["trainers_count"]
        training_hours = row["training_hours"]
        budget_allocated = row["budget_allocated"]
        budget_spent = row["budget_spent"]

        # ----------------------------------------------------
        # 1. Budget utilization
        # ----------------------------------------------------

        if (
            pd.notna(budget_allocated)
            and pd.notna(budget_spent)
            and budget_allocated > 0
        ):

            budget_utilization = (
                budget_spent
                / budget_allocated
                * 100
            )

            if budget_utilization > 110:

                add_anomaly(
                    anomalies,
                    record_id,
                    "budget_utilization_rate",
                    budget_utilization,
                    "<= 110%",
                    "Business threshold",
                    "HIGH",
                    (
                        f"Budget utilization is "
                        f"{budget_utilization:.2f}%, "
                        "which exceeds the 110% monitoring threshold."
                    ),
                )

            elif budget_utilization > 100:

                add_anomaly(
                    anomalies,
                    record_id,
                    "budget_utilization_rate",
                    budget_utilization,
                    "<= 100%",
                    "Business threshold",
                    "MEDIUM",
                    (
                        f"Budget spending is "
                        f"{budget_utilization:.2f}% of allocation, "
                        "indicating an overrun."
                    ),
                )

        # ----------------------------------------------------
        # 2. Low completion rate
        # ----------------------------------------------------

        if pd.notna(enrolled) and enrolled > 0:

            completion_rate = (
                completed
                / enrolled
                * 100
            )

            if completion_rate < 50:

                add_anomaly(
                    anomalies,
                    record_id,
                    "completion_rate",
                    completion_rate,
                    ">= 50%",
                    "Business threshold",
                    "MEDIUM",
                    (
                        f"Completion rate is "
                        f"{completion_rate:.2f}%, "
                        "below the 50% monitoring threshold."
                    ),
                )

        # ----------------------------------------------------
        # 3. High dropout rate
        # ----------------------------------------------------

        if pd.notna(enrolled) and enrolled > 0:

            dropout_rate = (
                dropped
                / enrolled
                * 100
            )

            if dropout_rate > 20:

                add_anomaly(
                    anomalies,
                    record_id,
                    "dropout_rate",
                    dropout_rate,
                    "<= 20%",
                    "Business threshold",
                    "HIGH",
                    (
                        f"Dropout rate is "
                        f"{dropout_rate:.2f}%, "
                        "above the 20% monitoring threshold."
                    ),
                )

        # ----------------------------------------------------
        # 4. High trainer-participant ratio
        # ----------------------------------------------------

        if pd.notna(trainers) and trainers > 0:

            trainer_ratio = (
                enrolled / trainers
            )

            if trainer_ratio > 50:

                add_anomaly(
                    anomalies,
                    record_id,
                    "trainer_participant_ratio",
                    trainer_ratio,
                    "<= 50 participants per trainer",
                    "Business threshold",
                    "MEDIUM",
                    (
                        f"There are approximately "
                        f"{trainer_ratio:.2f} participants "
                        "per trainer, above the 50:1 "
                        "monitoring threshold."
                    ),
                )

        # ----------------------------------------------------
        # 5. Very low training hours
        # ----------------------------------------------------

        if pd.notna(training_hours):

            if training_hours < 5:

                add_anomaly(
                    anomalies,
                    record_id,
                    "training_hours",
                    training_hours,
                    ">= 5 hours",
                    "Business threshold",
                    "MEDIUM",
                    (
                        f"Training hours are only "
                        f"{training_hours:.2f}, below the "
                        "5-hour monitoring threshold."
                    ),
                )


# ============================================================
# STATISTICAL ANOMALIES
# ============================================================

def detect_statistical_anomalies(df, anomalies):

    statistical_metrics = {
        "budget_spent": "budget_spent",
        "training_hours": "training_hours",
        "participants_enrolled": "participants_enrolled",
    }

    for indicator, column in statistical_metrics.items():

        lower, upper = calculate_iqr_bounds(
            df[column]
        )

        if lower is None:
            continue

        for _, row in df.iterrows():

            value = row[column]

            if pd.isna(value):
                continue

            # ------------------------------------------------
            # Upper outlier
            # ------------------------------------------------

            if value > upper:

                # Avoid duplicating an already obvious
                # business-rule anomaly where possible.
                existing = any(
                    item["record_id"] == row["record_id"]
                    and item["indicator"] == indicator
                    and item["detection_method"]
                    == "Business threshold"
                    for item in anomalies
                )

                if existing:
                    continue

                add_anomaly(
                    anomalies,
                    row["record_id"],
                    indicator,
                    value,
                    f"IQR upper bound <= {upper:.2f}",
                    "IQR statistical outlier",
                    "MEDIUM",
                    (
                        f"{indicator} value "
                        f"{value:.2f} is above the "
                        f"IQR upper bound of {upper:.2f}."
                    ),
                )

            # ------------------------------------------------
            # Lower outlier
            # ------------------------------------------------

            elif value < lower:

                existing = any(
                    item["record_id"] == row["record_id"]
                    and item["indicator"] == indicator
                    and item["detection_method"]
                    == "Business threshold"
                    for item in anomalies
                )

                if existing:
                    continue

                add_anomaly(
                    anomalies,
                    row["record_id"],
                    indicator,
                    value,
                    f"IQR lower bound >= {lower:.2f}",
                    "IQR statistical outlier",
                    "LOW",
                    (
                        f"{indicator} value "
                        f"{value:.2f} is below the "
                        f"IQR lower bound of {lower:.2f}."
                    ),
                )


# ============================================================
# DATABASE INSERT
# ============================================================

def insert_anomalies(anomalies):

    connection = psycopg2.connect(**DB_CONFIG)

    try:

        cursor = connection.cursor()

        # Safe to rerun during development.
        cursor.execute(
            "DELETE FROM anomalies;"
        )

        if not anomalies:
            connection.commit()
            print("No anomalies detected.")
            return

        insert_query = """
            INSERT INTO anomalies (
                record_id,
                indicator,
                observed_value,
                expected_value_or_range,
                detection_method,
                severity,
                reason,
                review_status,
                detected_at
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s
            );
        """

        values = [
            (
                anomaly["record_id"],
                anomaly["indicator"],
                float(anomaly["observed_value"]),
                anomaly["expected_value_or_range"],
                anomaly["detection_method"],
                anomaly["severity"],
                anomaly["reason"],
                anomaly["review_status"],
                anomaly["detected_at"],
            )
            for anomaly in anomalies
        ]

        cursor.executemany(
            insert_query,
            values
        )

        connection.commit()

        print(
            f"ANOMALIES INSERTED: {cursor.rowcount}"
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
    print("ANOMALY DETECTION ENGINE")
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
    # Numeric conversion
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
    # Detection
    # --------------------------------------------------------

    anomalies = []

    print("\nRunning business-rule detection...")

    detect_business_anomalies(
        df,
        anomalies
    )

    business_count = len(anomalies)

    print(
        f"Business-rule anomalies: {business_count}"
    )

    print(
        "\nRunning statistical IQR detection..."
    )

    detect_statistical_anomalies(
        df,
        anomalies
    )

    statistical_count = (
        len(anomalies) - business_count
    )

    print(
        f"Statistical anomalies: {statistical_count}"
    )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    print(
        "\nLoading anomalies into PostgreSQL..."
    )

    insert_anomalies(anomalies)

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    print("\nANOMALY DETECTION COMPLETE")
    print("-" * 45)

    print(
        f"Validated records: {len(df)}"
    )

    print(
        f"Total anomalies: {len(anomalies)}"
    )

    if anomalies:

        anomaly_df = pd.DataFrame(
            anomalies
        )

        print("\nSeverity breakdown:")

        print(
            anomaly_df["severity"]
            .value_counts()
            .to_string()
        )

        print("\nIndicator breakdown:")

        print(
            anomaly_df["indicator"]
            .value_counts()
            .to_string()
        )

        print(
            "\nAll anomalies are created with "
            "review_status = PENDING."
        )

        print(
            "Anomalies are monitoring signals, "
            "not automatic data deletions."
        )


if __name__ == "__main__":
    main()