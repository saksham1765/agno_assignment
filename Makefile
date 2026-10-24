# Valura — common targets (Windows: use `make` from Git Bash, or run the python lines directly)

.PHONY: eval audit test prove8 prove9

eval:
	python -m evals.run_all

audit:
	python scripts/audit_phases.py

test:
	python -m pytest tests -q

prove8:
	python scripts/prove_phase8.py

prove9:
	python scripts/prove_phase9.py
