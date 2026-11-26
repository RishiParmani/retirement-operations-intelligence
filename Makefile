.PHONY: setup pipeline eda model test validate-pbi all
setup:        ; pip install -r requirements.txt
pipeline:     ; python scripts/run_pipeline.py
eda:          ; python scripts/run_eda.py
model:        ; python scripts/train_model.py
test:         ; python -m pytest -q
validate-pbi: ; python scripts/validate_powerbi.py
all: pipeline eda model test validate-pbi
