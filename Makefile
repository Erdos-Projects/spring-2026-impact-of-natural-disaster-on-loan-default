.PHONY: qc nb-clean run-all run-preprocessing run-eda run-inference run-modeling

qc:
	ruff check src/ scripts/ notebooks/
	ruff format --check src/ scripts/
	ty check

nb-clean:
	jupyter nbconvert --clear-output --inplace notebooks/*.ipynb

run-all: run-preprocessing run-eda run-inference run-modeling

run-preprocessing:
	python scripts/preprocessing.py

run-eda:
	python scripts/eda.py

run-inference:
	python scripts/inference.py

run-modeling:
	python scripts/modeling.py
