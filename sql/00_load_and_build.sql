-- Run after schema.sql and after loading the CSVs (see sql/README.md).
-- Builds the two small dimensions from the fact table and the business rules in src/roip/config.py.

INSERT INTO dim_operation_type (operation_type, sla_target_hours, is_financial)
SELECT operation_type,
       MAX(sla_target_hours),
       BOOL_OR(transaction_amount > 0)       -- non-financial types always carry a 0 amount
FROM fact_operations
GROUP BY operation_type
ON CONFLICT (operation_type) DO NOTHING;

INSERT INTO dim_priority (priority, priority_rank)
VALUES ('Critical', 1), ('High', 2), ('Medium', 3), ('Low', 4)
ON CONFLICT (priority) DO NOTHING;
