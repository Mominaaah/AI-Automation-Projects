import pandas as pd
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

INPUT_FILE = BASE_DIR / "data" / "processed" / "program_monitoring_prepared.csv"
CENTERS_FILE = BASE_DIR / "data" / "processed" / "training_centers.csv"

OUTPUT_FILE = BASE_DIR / "data" / "processed" / "validated_monitoring_data.csv"
QUARANTINE_FILE = BASE_DIR / "data" / "processed" / "quarantined_records.csv"
LOG_FILE = BASE_DIR / "data" / "processed" / "cleaning_log.csv"


def main():

    print("Loading monitoring data...")
    df = pd.read_csv(INPUT_FILE)

    print("Loading training center reference...")
    centers = pd.read_csv(CENTERS_FILE)

    original_count = len(df)

    cleaning_log = []
    quarantined = []

    # ---------------------------------------------------------
    # 1. Standardize text fields
    # ---------------------------------------------------------

    text_columns = [
        "district",
        "training_center_id",
        "program_type",
        "data_source",
        "data_quality_status",
    ]

    for col in text_columns:
        if col in df.columns:
            df[col] = df[col].astype("string").str.strip()

    # ---------------------------------------------------------
    # 2. Numeric conversion
    # ---------------------------------------------------------

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

    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # ---------------------------------------------------------
    # 3. Date conversion
    # ---------------------------------------------------------

    date_columns = [
        "reporting_month",
        "reporting_date",
        "submission_date",
    ]

    for col in date_columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # ---------------------------------------------------------
    # 4. Quarantine unknown training centers
    # ---------------------------------------------------------

    valid_centers = set(
        centers["training_center_id"]
        .astype(str)
        .str.strip()
    )

    unknown_center_mask = ~df["training_center_id"].isin(valid_centers)

    unknown_centers = df[unknown_center_mask].copy()

    for _, row in unknown_centers.iterrows():

        cleaning_log.append({
            "record_id": row["record_id"],
            "issue_type": "unknown_training_center",
            "field_name": "training_center_id",
            "action": "quarantined",
            "old_value": row["training_center_id"],
            "new_value": None,
            "reason": "Training center does not exist in reference table"
        })

    if len(unknown_centers) > 0:
        quarantined.extend(
            unknown_centers.to_dict("records")
        )

    df = df[~unknown_center_mask].copy()

    # ---------------------------------------------------------
    # 5. Duplicate detection
    # ---------------------------------------------------------

    business_key = [
        "record_id",
        "reporting_month",
        "training_center_id",
        "program_type",
    ]

    duplicate_mask = df.duplicated(
        subset=business_key,
        keep="first"
    )

    duplicate_records = df[duplicate_mask].copy()

    for _, row in duplicate_records.iterrows():

        cleaning_log.append({
            "record_id": row["record_id"],
            "issue_type": "duplicate_record",
            "field_name": "business_key",
            "action": "quarantined",
            "old_value": str(
                tuple(row[col] for col in business_key)
            ),
            "new_value": None,
            "reason": "Duplicate business record; first occurrence retained"
        })

    if len(duplicate_records) > 0:
        quarantined.extend(
            duplicate_records.to_dict("records")
        )

    df = df[~duplicate_mask].copy()

    # ---------------------------------------------------------
    # 6. Negative participant values
    # ---------------------------------------------------------

    participant_columns = [
        "participants_enrolled",
        "participants_completed",
        "participants_in_progress",
        "participants_dropped",
        "employment_outcomes",
    ]

    for col in participant_columns:

        mask = df[col] < 0

        for _, row in df[mask].iterrows():

            cleaning_log.append({
                "record_id": row["record_id"],
                "issue_type": "negative_value",
                "field_name": col,
                "action": "set_null",
                "old_value": row[col],
                "new_value": None,
                "reason": "Participant count cannot be negative"
            })

        df.loc[mask, col] = pd.NA

    # ---------------------------------------------------------
    # 7. Negative budget values
    # ---------------------------------------------------------

    budget_columns = [
        "budget_allocated",
        "budget_spent",
    ]

    for col in budget_columns:

        mask = df[col] < 0

        for _, row in df[mask].iterrows():

            cleaning_log.append({
                "record_id": row["record_id"],
                "issue_type": "negative_value",
                "field_name": col,
                "action": "set_null",
                "old_value": row[col],
                "new_value": None,
                "reason": "Budget value cannot be negative"
            })

        df.loc[mask, col] = pd.NA

    # ---------------------------------------------------------
    # 8. Invalid dates
    # ---------------------------------------------------------

    for col in date_columns:

        invalid_mask = df[col].isna()

        for _, row in df[invalid_mask].iterrows():

            cleaning_log.append({
                "record_id": row["record_id"],
                "issue_type": "invalid_date",
                "field_name": col,
                "action": "set_null",
                "old_value": None,
                "new_value": None,
                "reason": "Date could not be parsed"
            })

    # ---------------------------------------------------------
    # 9. Data quality status
    # ---------------------------------------------------------

    review_record_ids = {
        item["record_id"]
        for item in cleaning_log
        if item["action"] in ["set_null", "quarantined"]
    }

    df["data_quality_status"] = "PASS"

    if review_record_ids:
        df.loc[
            df["record_id"].isin(review_record_ids),
            "data_quality_status"
        ] = "REVIEW"

    # ---------------------------------------------------------
    # 10. Save cleaned data
    # ---------------------------------------------------------

    df.to_csv(
        OUTPUT_FILE,
        index=False
    )

    # ---------------------------------------------------------
    # 11. Save quarantined records
    # ---------------------------------------------------------

    if quarantined:

        quarantine_df = pd.DataFrame(quarantined)

        quarantine_df.to_csv(
            QUARANTINE_FILE,
            index=False
        )

    else:

        pd.DataFrame(
            columns=df.columns
        ).to_csv(
            QUARANTINE_FILE,
            index=False
        )

    # ---------------------------------------------------------
    # 12. Save cleaning log
    # ---------------------------------------------------------

    pd.DataFrame(cleaning_log).to_csv(
        LOG_FILE,
        index=False
    )

    print()
    print("CLEANING COMPLETE")
    print("------------------")
    print(f"Original records:   {original_count}")
    print(f"Validated records:  {len(df)}")
    print(f"Quarantined:        {len(quarantined)}")
    print(f"Cleaning log rows:  {len(cleaning_log)}")
    print()
    print("Quality status:")
    print(df["data_quality_status"].value_counts())
    print()
    print(f"Output: {OUTPUT_FILE}")
    print(f"Quarantine: {QUARANTINE_FILE}")
    print(f"Log: {LOG_FILE}")


if __name__ == "__main__":
    main()