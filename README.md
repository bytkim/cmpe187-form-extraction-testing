# Form extraction test automation

CMPE 187/287 · Project 1 · Deliverable 3 · FORM-CVS 1

Thomas Kim and Sai Thaw Di Nine · November 22, 2026

This local repository tests whether an image reader can extract two fictional forms into structured data under 16 conditions from the team's Deliverable 2(A). Native Codex CLI is the primary execution path. A separate browser cohort exercised ChatGPT web. The selected product in the earlier design is ChatGPT mobile. This repository measures the two named execution paths.

## Submission files

| File or folder | Contents |
| --- | --- |
| [Report PDF](Test_Automation_Report.pdf) / [Word original](Test_Automation_Report.docx) | Six-page report and editable original |
| Presentation.pptx | Seven slides with presenter notes |
| [Watch the execution demo](Execution_Demo.mp4) | Chaptered screen recording with a live terminal, a before-and-after augmentation, five fresh Codex requests, the simulator, cost and script complexity. Includes English captions. |
| [Demo script and commands](Demo_Script.txt) | Timestamped script and exact demo commands |
| automation/ | Executable Python scripts, public data sample, fonts, case table and generated fixtures |
| evidence/ | Original answer text and individual request receipts. The filmed take is separate. |
| statistics/ | Per-field and per-attempt CSV files, summaries and measured script complexity |
| manual_review.html | Timed two-case worksheet for an independent human comparison |

## Open in Codex CLI

From this repository's root, run `codex` for an interactive session. A practical first request is `Run make test and make replay, then explain the TC04 difference using the saved field rows.` AGENTS.md describes the evidence layout. The Python runner also invokes native `codex exec --image` directly, with a fresh working directory for each request.

## Offline execution

Python 3.10 or later supports the scorer, validation controls and simulator. Scoring the included fixtures requires only the Python standard library. The Makefile is optional.

```sh
make test
make replay
make gui
```

Open the loopback URL printed by the simulator. The saved-result view presents each image next to its per-field checks. The live button sends the selected fictional form to Codex and writes a new receipt in a temporary folder. The CLI command line below offers an explicit output location.

## Regenerate the fixtures

The repository includes the ten sampled glyphs, three redistributable fonts, two source records and all frozen PNGs. To render images again, install Pillow in a local virtual environment.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python automation/generate.py --out runs/generated
```

The optional discovery demo refetches the UCI source archive, reconstructs the first sample of each digit and compares the complete selection to the packaged one.

```sh
python automation/demo.py setup --work runs/source-demo
```

Font rasterization can vary with the underlying FreeType build. The frozen-input replay always verifies the submitted image hashes. Use the new manifest together with its corresponding images for fresh tests on regenerated fixtures.

## Fresh model execution

Install and sign into Codex CLI. The recorded campaign used codex-cli 0.171.0-alpha.13, gpt-6.2-sol, low reasoning effort and the account's ChatGPT login. Fresh runs use account access and network service. The runner creates an isolated, read-only CLI session per image, sends the image and prompt, and captures the final answer plus event and token metadata.

```sh
codex login status
python3 automation/run_codex.py --repeat 3 --jobs 3 --out runs/new-suite
python3 automation/score.py runs/new-suite --out runs/new-statistics
```

For a shorter run, add `--case TC04 --repeat 1` to the runner. TC16 always requests at least three independent sessions. Use a new output path each time. A model discrepancy returns exit code 1 and an infrastructure block returns 2. Scoring a completed run remains available in either case.

For the optional web adapter, install the Python `playwright` package and Google Chrome. Run `python3 automation/run_web.py --profile runs/browser-profile --out runs/new-web` and sign into that dedicated profile. The recorded web observations were collected with browser automation against the signed-in ChatGPT web interface. The adapter follows the same upload and extraction flow. The browser reached its upload allowance before TC16. Browser receipt labels record the intended temporary-chat setting. Temporary mode was not independently verified for every earlier receipt, and TC11 completed after an upload failure in a fresh standard chat.

## Reported results

| Cohort | Scored attempts | Strict passes | Correct field assertions |
| --- | ---: | ---: | ---: |
| Codex CLI | 48 | 45 | 447 / 450 |
| ChatGPT web | 15 | 14 | 142 / 143 |

The main CLI batch runs TC01–TC15 three times and the consistency batch runs TC16 three times. A single invocation of the runner can run the same 48-case plan. The evaluator rejects duplicate identities, matches prompts and image digests, and distinguishes a blocked upload from a returned answer. TC16 scored 7/7 matching and correct fields across its three sessions. Only TC04 failed. The separate filmed TC14 take and synthetic grader controls are excluded from campaign statistics.

Two additional Codex reviewer calls assessed the saved web responses for TC01 and TC04 without the answer key. They matched both binary verdicts in 8.404 seconds, but the reviewer proposed null for the obscured mark. The project oracle requires [illegible]. Receipts appear in `evidence/visual-review/` and the repeatable script is `automation/review_visual.py`. These calls are separate from the extraction totals.

The public data, generated capture proxies and two-record evaluation limit generalization. The timed worksheet supplies a human comparison protocol. No observed student labor time or human speedup is claimed.

## Data and provenance

- The attached team's Deliverable 2(A), sections 2–3, supplies the 16-case design, original prompts and fictional form values. Additional email and insurance fields make the blank-field case testable.
- E. Alpaydin and C. Kaynak, *Optical Recognition of Handwritten Digits*, UCI Machine Learning Repository, 1998. CC BY 4.0. TC11 scales the selected grayscale samples and composes them with punctuation. Source row numbers and the full member digest are in `automation/data/digits.json`. [Dataset](https://doi.org/10.24432/C50P49) · [License](https://creativecommons.org/licenses/by/4.0/)
- Lato, Kalam and Dancing Script are distributed with their OFL notices in `automation/data/fonts/`. The two handwriting styles approximate lettering. The phone digits are sampled handwriting. [Google Fonts source](https://github.com/google/fonts)
- The current demo records the terminal and the local simulator. It downloads the UCI samples, generates the fixtures, verifies two augmentations, runs five fresh Codex requests, inspects field discrepancies, replays the campaign, and computes cost and complexity. Four of the five new requests passed and TC04 failed. The new receipts and seven console commands are in `evidence/demo-v2/`. The original one-request take remains in `evidence/demo-take/`. Both are separate from the 48-request campaign. Narration is synthesized, and receipt times are UTC.
