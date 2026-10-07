-- ============================================================
-- AI-POWERED DEVELOPMENT MONITORING PLATFORM
-- PostgreSQL Database Schema
-- ============================================================

-- ============================================================
-- 1. TRAINING CENTERS
-- ============================================================

CREATE TABLE IF NOT EXISTS training_centers (
    training_center_id VARCHAR(50) PRIMARY KEY,
    district VARCHAR(100) NOT NULL,
    center_name VARCHAR(150) NOT NULL,
    center_type VARCHAR(50),
    capacity INTEGER,
    active_status BOOLEAN DEFAULT TRUE,

    CONSTRAINT chk_center_capacity
        CHECK (capacity IS NULL OR capacity > 0)
);


-- ============================================================
-- 2. PROGRAM MONITORING
-- ============================================================

CREATE TABLE IF NOT EXISTS program_monitoring (
    record_id INTEGER PRIMARY KEY,

    reporting_month DATE NOT NULL,
    reporting_date DATE,
    submission_date DATE,

    district VARCHAR(100),
    training_center_id VARCHAR(50),
    program_type VARCHAR(100),

    participants_enrolled INTEGER,
    participants_completed INTEGER,
    participants_in_progress INTEGER,
    participants_dropped INTEGER,
    employment_outcomes INTEGER,

    trainers_count INTEGER,
    training_hours NUMERIC(10,2),

    budget_allocated NUMERIC(14,2),
    budget_spent NUMERIC(14,2),

    data_source VARCHAR(50),

    data_quality_status VARCHAR(20) DEFAULT 'PASS',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_monitoring_training_center
        FOREIGN KEY (training_center_id)
        REFERENCES training_centers(training_center_id),

    CONSTRAINT chk_enrolled_nonnegative
        CHECK (
            participants_enrolled IS NULL
            OR participants_enrolled >= 0
        ),

    CONSTRAINT chk_completed_nonnegative
        CHECK (
            participants_completed IS NULL
            OR participants_completed >= 0
        ),

    CONSTRAINT chk_in_progress_nonnegative
        CHECK (
            participants_in_progress IS NULL
            OR participants_in_progress >= 0
        ),

    CONSTRAINT chk_dropped_nonnegative
        CHECK (
            participants_dropped IS NULL
            OR participants_dropped >= 0
        ),

    CONSTRAINT chk_employment_nonnegative
        CHECK (
            employment_outcomes IS NULL
            OR employment_outcomes >= 0
        ),

    CONSTRAINT chk_trainers_nonnegative
        CHECK (
            trainers_count IS NULL
            OR trainers_count >= 0
        ),

    CONSTRAINT chk_training_hours_nonnegative
        CHECK (
            training_hours IS NULL
            OR training_hours >= 0
        ),

    CONSTRAINT chk_budget_allocated_nonnegative
        CHECK (
            budget_allocated IS NULL
            OR budget_allocated >= 0
        ),

    CONSTRAINT chk_budget_spent_nonnegative
        CHECK (
            budget_spent IS NULL
            OR budget_spent >= 0
        )
);


-- ============================================================
-- 3. VALIDATION RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS validation_results (
    validation_id BIGSERIAL PRIMARY KEY,

    record_id INTEGER,

    validation_rule VARCHAR(20) NOT NULL,

    issue_type VARCHAR(150) NOT NULL,

    severity VARCHAR(20),

    field_name VARCHAR(100),

    actual_value TEXT,

    expected_condition TEXT,

    status VARCHAR(20) DEFAULT 'FAIL',

    validation_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_validation_record
        FOREIGN KEY (record_id)
        REFERENCES program_monitoring(record_id)
);


-- ============================================================
-- 4. ANOMALIES
-- ============================================================

CREATE TABLE IF NOT EXISTS anomalies (
    anomaly_id BIGSERIAL PRIMARY KEY,

    record_id INTEGER,

    indicator VARCHAR(100),

    observed_value NUMERIC,

    expected_value_or_range TEXT,

    detection_method VARCHAR(100),

    severity VARCHAR(20),

    reason TEXT,

    review_status VARCHAR(30) DEFAULT 'PENDING',

    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_anomaly_record
        FOREIGN KEY (record_id)
        REFERENCES program_monitoring(record_id)
);


-- ============================================================
-- 5. KPI RESULTS
-- ============================================================

CREATE TABLE IF NOT EXISTS kpi_results (
    kpi_id BIGSERIAL PRIMARY KEY,

    reporting_month DATE NOT NULL,

    district VARCHAR(100),

    training_center_id VARCHAR(50),

    total_enrolled INTEGER,
    total_completed INTEGER,
    total_dropped INTEGER,

    completion_rate NUMERIC(8,4),
    dropout_rate NUMERIC(8,4),
    employment_outcome_rate NUMERIC(8,4),

    avg_training_hours NUMERIC(10,2),

    trainer_participant_ratio NUMERIC(10,4),

    budget_allocated NUMERIC(14,2),
    budget_spent NUMERIC(14,2),

    budget_utilization_rate NUMERIC(8,4),

    data_quality_score NUMERIC(8,4),

    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_kpi_training_center
        FOREIGN KEY (training_center_id)
        REFERENCES training_centers(training_center_id)
);


-- ============================================================
-- 6. AUDIT LOG
-- ============================================================

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id BIGSERIAL PRIMARY KEY,

    process_name VARCHAR(100) NOT NULL,

    record_id INTEGER,

    action VARCHAR(100) NOT NULL,

    status VARCHAR(30),

    details TEXT,

    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- ============================================================
-- INDEXES
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_monitoring_month
    ON program_monitoring(reporting_month);

CREATE INDEX IF NOT EXISTS idx_monitoring_district
    ON program_monitoring(district);

CREATE INDEX IF NOT EXISTS idx_monitoring_center
    ON program_monitoring(training_center_id);

CREATE INDEX IF NOT EXISTS idx_validation_record
    ON validation_results(record_id);

CREATE INDEX IF NOT EXISTS idx_validation_rule
    ON validation_results(validation_rule);

CREATE INDEX IF NOT EXISTS idx_anomaly_record
    ON anomalies(record_id);

CREATE INDEX IF NOT EXISTS idx_anomaly_status
    ON anomalies(review_status);

CREATE INDEX IF NOT EXISTS idx_kpi_month
    ON kpi_results(reporting_month);

CREATE INDEX IF NOT EXISTS idx_kpi_district
    ON kpi_results(district);


-- ============================================================
-- SCHEMA COMPLETE
-- ============================================================