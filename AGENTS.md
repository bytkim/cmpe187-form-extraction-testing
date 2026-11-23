# Working in this repository with Codex CLI

The project root contains the submission artifacts. Use `make test` for oracle controls and `make replay` to independently verify the frozen campaign without another model call. The checked-in report and deck describe those frozen measurements.

For fresh execution, use `automation/run_codex.py`. Run a single named case or the full 16-case suite, and pass a new directory under `runs/` to `--out`. The script starts a clean native CLI process for every individual attempt. The runner sees the synthetic PNG and its prompt. Answer keys belong to the external grader.

Keep the Codex CLI, ChatGPT web and demo-take results identifiable by execution path. A blocked request has no scored output. A failed field check is a recorded outcome. The fixture generator draws from `automation/data/` and writes a manifest linking every case to its PNG, prompt and expected fields. `automation/score.py` reconstructs both granular CSVs from receipts and verifies the fingerprints.
