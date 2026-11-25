CREATE TABLE IF NOT EXISTS fact_operations (
 operation_id VARCHAR(20) PRIMARY KEY, customer_id VARCHAR(20), account_id VARCHAR(20), plan_id VARCHAR(20),
 operation_type VARCHAR(80), priority VARCHAR(20), channel VARCHAR(30), region VARCHAR(30), processing_team VARCHAR(30),
 team_workload INTEGER, customer_segment VARCHAR(40), received_at TIMESTAMP, assigned_at TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP,
 status VARCHAR(30), exception_flag BOOLEAN, exception_type VARCHAR(50), exception_severity VARCHAR(20), root_cause VARCHAR(50),
 rework_flag BOOLEAN, sla_target_hours INTEGER, processing_hours NUMERIC(10,2), sla_breached INTEGER,
 transaction_amount NUMERIC(14,2), currency VARCHAR(3), missing_info_flag BOOLEAN,
 received_year INTEGER, received_month INTEGER, received_week INTEGER, received_day_of_week VARCHAR(20), data_quality_score INTEGER
);
CREATE INDEX IF NOT EXISTS idx_ops_received ON fact_operations(received_at);
CREATE INDEX IF NOT EXISTS idx_ops_team_type ON fact_operations(processing_team,operation_type);
CREATE INDEX IF NOT EXISTS idx_ops_status_sla ON fact_operations(status,sla_breached);
