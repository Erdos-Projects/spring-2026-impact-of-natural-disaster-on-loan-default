.PHONY: qc nb-clean

qc:
	ruff check src/ notebooks/
	ruff format --check src/
	ty check

nb-clean:
	jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
