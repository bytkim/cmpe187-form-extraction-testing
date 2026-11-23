PYTHON ?= python3
ifndef RUN
RUN := runs/$(shell date +%Y%m%d-%H%M%S)
endif
.PHONY: test fixtures live replay gui
test:
	$(PYTHON) automation/test_oracle.py
fixtures:
	$(PYTHON) automation/generate.py --out $(RUN)/fixtures
live:
	$(PYTHON) automation/run_codex.py --repeat 3 --jobs 3 --out $(RUN)/evidence
replay:
	$(PYTHON) automation/score.py evidence/codex-cli --out $(RUN)/codex
	$(PYTHON) automation/score.py evidence/chatgpt-web --out $(RUN)/web
gui:
	$(PYTHON) automation/simulator.py
