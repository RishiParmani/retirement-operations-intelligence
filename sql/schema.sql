-- ROIP warehouse schema (PostgreSQL syntax; also runs unchanged on DuckDB, which the tests use).
-- Column order of fact_operations matches data/processed/operations_clean.csv exactly, so
--   \copy fact_operations FROM 'data/processed/operations_clean.csv' CSV HEADER
-- works as-is. (The original schema omitted received_date and could not load the CSV.)

CREATE TABLE IF NOT EXISTS fact_operations (
    operation_id         VARCHAR(20) PRIMARY KEY,
    customer_id          VARCHAR(20),
    account_id           VARCHAR(20),
    plan_id              VARCHAR(20),
    operation_type       VARCHAR(80)  NOT NULL,
    priority             VARCHAR(20)  NOT NULL,
    channel              VARCHAR(30),
    region               VARCHAR(30),
    processing_team      VARCHAR(30),
    team_workload        INTEGER,
    customer_segment     VARCHAR(40),
    received_at          TIMESTAMP    NOT NULL,
    assigned_at          TIMESTAMP,
    started_at           TIMESTAMP,
    completed_at         TIMESTAMP,
    status               VARCHAR(30)  NOT NULL,
    exception_flag       BOOLEAN,
    exception_type       VARCHAR(50),
    exception_severity   VARCHAR(20),
    root_cause           VARCHAR(50),
    rework_flag          BOOLEAN,
    sla_target_hours     INTEGER      NOT NULL,
    processing_hours     NUMERIC(10,2),
    sla_breached         INTEGER,
    transaction_amount   NUMERIC(14,2),
    currency             VARCHAR(3),
    missing_info_flag    BOOLEAN,
    received_date        DATE,
    received_year        INTEGER,
    received_month       INTEGER,
    received_week        INTEGER,
    received_day_of_week VARCHAR(20),
    data_quality_score   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ops_received   ON fact_operations (received_at);
CREATE INDEX IF NOT EXISTS idx_ops_type_prio  ON fact_operations (operation_type, priority);
CREATE INDEX IF NOT EXISTS idx_ops_status_sla ON fact_operations (status, sla_breached);

-- Small dimensions (give the queries real joins and a place for business rules).
CREATE TABLE IF NOT EXISTS dim_operation_type (
    operation_type   VARCHAR(80) PRIMARY KEY,
    sla_target_hours INTEGER NOT NULL,
    is_financial     BOOLEAN NOT NULL
);
CREATE TABLE IF NOT EXISTS dim_priority (
    priority      VARCHAR(20) PRIMARY KEY,
    priority_rank INTEGER NOT NULL      -- 1 = most urgent
);

-- Pipeline outputs (loaded from reports/data_quality/*.csv).
CREATE TABLE IF NOT EXISTS dq_rejected_records (
    operation_id     VARCHAR(20),
    rejection_rule   VARCHAR(10),
    rejection_reason VARCHAR(80),
    operation_type   VARCHAR(80),
    received_at      TIMESTAMP,
    status           VARCHAR(30)
);
CREATE TABLE IF NOT EXISTS dq_rule_results (
    rule_id       VARCHAR(10),
    rule_name     VARCHAR(100),
    stage         VARCHAR(10),
    severity      VARCHAR(10),
    rows_affected INTEGER,
    pct_of_raw    NUMERIC(10,4),
    action        VARCHAR(100),
    description   VARCHAR(1000)
);
