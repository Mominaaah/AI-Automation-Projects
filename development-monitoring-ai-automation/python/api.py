import os
from datetime import datetime

import psycopg2
from fastapi import FastAPI, HTTPException


# ============================================================
# CONFIGURATION
# ============================================================

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "database": "development_monitoring",
    "user": "postgres",
    "password": os.getenv("PGPASSWORD", "postgres"),
}


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="Development Monitoring Automation API",
    description=(
        "API for KPIs, anomalies, and monitoring data "
        "from the AI-Powered Development Program "
        "Monitoring & Reporting Automation Platform."
    ),
    version="1.0.0",
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    return psycopg2.connect(
        **DB_CONFIG
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():

    return {
        "application": (
            "AI-Powered Development Program "
            "Monitoring & Reporting Automation Platform"
        ),
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health():

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            "SELECT 1;"
        )

        cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "status": "healthy",
            "database": "connected",
            "timestamp": datetime.now().isoformat(),
        }

    except Exception as error:

        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "unavailable",
                "error": str(error),
            },
        )


# ============================================================
# SUMMARY
# ============================================================

@app.get("/api/summary")
def get_summary():

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS kpi_rows,
                COALESCE(SUM(total_enrolled), 0),
                COALESCE(SUM(total_completed), 0),
                COALESCE(SUM(total_dropped), 0),
                COALESCE(SUM(budget_allocated), 0),
                COALESCE(SUM(budget_spent), 0),
                COALESCE(AVG(completion_rate), 0),
                COALESCE(AVG(dropout_rate), 0),
                COALESCE(AVG(employment_outcome_rate), 0),
                COALESCE(AVG(data_quality_score), 0)
            FROM kpi_results;
            """
        )

        row = cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "kpi_rows": row[0],
            "total_enrolled": row[1],
            "total_completed": row[2],
            "total_dropped": row[3],
            "budget_allocated": float(row[4]),
            "budget_spent": float(row[5]),
            "average_completion_rate": float(row[6]),
            "average_dropout_rate": float(row[7]),
            "average_employment_outcome_rate": float(row[8]),
            "average_data_quality_score": float(row[9]),
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# KPIs
# ============================================================

@app.get("/api/kpis")
def get_kpis(
    limit: int = 100,
    district: str | None = None,
    training_center_id: str | None = None,
):

    try:

        connection = get_connection()

        cursor = connection.cursor()

        query = """
            SELECT
                kpi_id,
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
            FROM kpi_results
            WHERE 1=1
        """

        params = []

        if district:

            query += """
                AND district = %s
            """

            params.append(district)

        if training_center_id:

            query += """
                AND training_center_id = %s
            """

            params.append(
                training_center_id
            )

        query += """
            ORDER BY reporting_month DESC,
                     district,
                     training_center_id
            LIMIT %s;
        """

        params.append(limit)

        cursor.execute(
            query,
            params
        )

        rows = cursor.fetchall()

        columns = [
            "kpi_id",
            "reporting_month",
            "district",
            "training_center_id",
            "total_enrolled",
            "total_completed",
            "total_dropped",
            "completion_rate",
            "dropout_rate",
            "employment_outcome_rate",
            "avg_training_hours",
            "trainer_participant_ratio",
            "budget_allocated",
            "budget_spent",
            "budget_utilization_rate",
            "data_quality_score",
            "calculated_at",
        ]

        results = []

        for row in rows:

            item = dict(
                zip(columns, row)
            )

            if item["reporting_month"]:
                item["reporting_month"] = str(
                    item["reporting_month"]
                )

            if item["calculated_at"]:
                item["calculated_at"] = (
                    item["calculated_at"].isoformat()
                )

            for field in [
                "completion_rate",
                "dropout_rate",
                "employment_outcome_rate",
                "avg_training_hours",
                "trainer_participant_ratio",
                "budget_allocated",
                "budget_spent",
                "budget_utilization_rate",
                "data_quality_score",
            ]:

                if item[field] is not None:
                    item[field] = float(
                        item[field]
                    )

            results.append(item)

        cursor.close()
        connection.close()

        return {
            "count": len(results),
            "data": results,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# ANOMALIES
# ============================================================

@app.get("/api/anomalies")
def get_anomalies(
    limit: int = 100,
    severity: str | None = None,
    review_status: str | None = None,
):

    try:

        connection = get_connection()

        cursor = connection.cursor()

        query = """
            SELECT
                anomaly_id,
                record_id,
                indicator,
                observed_value,
                expected_value_or_range,
                detection_method,
                severity,
                reason,
                review_status,
                detected_at
            FROM anomalies
            WHERE 1=1
        """

        params = []

        if severity:

            query += """
                AND severity = %s
            """

            params.append(
                severity.upper()
            )

        if review_status:

            query += """
                AND review_status = %s
            """

            params.append(
                review_status.upper()
            )

        query += """
            ORDER BY
                CASE severity
                    WHEN 'HIGH' THEN 1
                    WHEN 'MEDIUM' THEN 2
                    WHEN 'LOW' THEN 3
                    ELSE 4
                END,
                detected_at DESC
            LIMIT %s;
        """

        params.append(limit)

        cursor.execute(
            query,
            params
        )

        rows = cursor.fetchall()

        columns = [
            "anomaly_id",
            "record_id",
            "indicator",
            "observed_value",
            "expected_value_or_range",
            "detection_method",
            "severity",
            "reason",
            "review_status",
            "detected_at",
        ]

        results = []

        for row in rows:

            item = dict(
                zip(columns, row)
            )

            if item["observed_value"] is not None:

                item["observed_value"] = float(
                    item["observed_value"]
                )

            if item["detected_at"]:

                item["detected_at"] = (
                    item["detected_at"].isoformat()
                )

            results.append(item)

        cursor.close()
        connection.close()

        return {
            "count": len(results),
            "data": results,
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# ============================================================
# ANOMALY SUMMARY
# ============================================================

@app.get("/api/anomalies/summary")
def get_anomaly_summary():

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (
                    WHERE severity = 'HIGH'
                ) AS high,
                COUNT(*) FILTER (
                    WHERE severity = 'MEDIUM'
                ) AS medium,
                COUNT(*) FILTER (
                    WHERE severity = 'LOW'
                ) AS low,
                COUNT(*) FILTER (
                    WHERE review_status = 'PENDING'
                ) AS pending
            FROM anomalies;
            """
        )

        row = cursor.fetchone()

        cursor.close()
        connection.close()

        return {
            "total": row[0],
            "high": row[1],
            "medium": row[2],
            "low": row[3],
            "pending_review": row[4],
        }

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )