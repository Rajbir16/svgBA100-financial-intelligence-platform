.PHONY: install test validate load ratios all clean

PYTHON ?= python

install:
	$(PYTHON) -m pip install -r requirements.txt

load:
	$(PYTHON) -m src.etl.loader --db nifty100.db --data-dir "./data" --output-dir output

validate:
	$(PYTHON) -m src.etl.validator --db nifty100.db --output output/validation_failures.csv

ratios:
	$(PYTHON) -m src.analytics.ratios --db nifty100.db --output-dir output

test:
	$(PYTHON) -m pytest tests/ -v

all: install load validate ratios test

clean:
	-del /f /q nifty100.db output\load_audit.csv output\validation_failures.csv 2>nul



