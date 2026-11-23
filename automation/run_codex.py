"""Execute independent image tests through the native Codex CLI and retain receipts."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
from oracle import assess

ROOT = Path(__file__).resolve().parent
MODEL = "gpt-6.2-sol"
DISABLE = ["shell_tool", "unified_exec", "apps", "plugins", "memories", "multi_agent"]


def invoke(case, rep, image, out, model):
    start = time.perf_counter()
    rec = dict(id=case["id"], rep=rep, sha256=case["sha256"], prompt=case["prompt"],
               backend="Codex CLI", model=model, started_utc=datetime.now(timezone.utc).isoformat())
    status = "BLOCKED"
    try:
        data = image.read_bytes()
        if hashlib.sha256(data).hexdigest() != case["sha256"]:
            raise ValueError("Image digest differs from case manifest")
        with tempfile.TemporaryDirectory(prefix="form-test-") as scratch:
            work = Path(scratch)
            (work / "form.png").write_bytes(data)
            cmd = ["codex", "exec", "--ignore-user-config", "--ephemeral", "--skip-git-repo-check",
                   "--sandbox", "read-only", "-C", scratch, "-m", model, "--json",
                   "-c", 'model_reasoning_effort="low"', "-c", 'web_search="disabled"']
            for feature in DISABLE:
                cmd.extend(["--disable", feature])
            cmd.extend(["--image", "form.png", "--output-last-message", str(work / "answer.txt"), "-"])
            result = subprocess.run(cmd, cwd=work, input=case["prompt"], capture_output=True,
                                    text=True, timeout=180)
            events = [json.loads(s) for s in result.stdout.splitlines() if s.lstrip().startswith("{")]
            items = [e["item"].get("type") for e in events if "item" in e]
            rec["event_types"] = [e.get("type") for e in events]
            rec["item_types"] = items
            rec["usage"] = next((e.get("usage") for e in events if e.get("type") == "turn.completed"), None)
            if result.returncode or not (work / "answer.txt").is_file():
                errors = [e.get("message") or e.get("error") for e in events if e.get("type") in ("turn.failed","error")]
                raise RuntimeError(str(errors or result.stderr[-500:]))
            if any(kind not in ("agent_message","reasoning") for kind in items):
                raise RuntimeError("Non-message action detected in isolated extraction")
            rec["raw"] = (work / "answer.txt").read_text()
            if not rec["raw"].strip():
                raise RuntimeError("CLI produced an empty result")
            status = "PASS" if assess(case, rec["raw"])["pass"] else "FAIL"
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        rec.pop("raw", None)
        rec["infrastructure_error"] = str(error)
    rec["elapsed_s"] = round(time.perf_counter() - start, 3)
    with (out / f'{case["id"]}-{rep}.json').open("x") as stream:
        json.dump(rec, stream, indent=2, ensure_ascii=False)
    print(f'{case["id"]}  run {rep}  {status:7}  {rec["elapsed_s"]:6.2f} s  {case["title"]}', flush=True)
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, required=True, help="new directory for frozen responses")
    p.add_argument("--case", nargs="+")
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--jobs", type=int, default=1)
    p.add_argument("--model", default=MODEL)
    p.add_argument("--fixtures", type=Path, default=ROOT / "fixtures")
    a = p.parse_args()
    cases = json.loads((a.fixtures/"manifest.json").read_text())
    if min(a.repeat,a.jobs) < 1 or a.case and set(a.case) - {c["id"] for c in cases}:
        p.error("Choose valid case IDs and positive repetition/worker counts")
    if not shutil.which("codex"):
        p.error("Install and sign into Codex CLI")
    plan = [(c,r) for c in cases if not a.case or c["id"] in a.case
            for r in range(1,max(a.repeat,3 if c["id"]=="TC16" else 1)+1)]
    a.out.mkdir(parents=True,exist_ok=False)
    version = subprocess.check_output(["codex","--version"],text=True).strip()
    start = time.perf_counter()
    print(f"{version}  |  {a.model}  |  {len(plan)} fresh requests", flush=True)
    def execute(pair):
        c,r = pair
        return invoke(c,r,a.fixtures/c["image"],a.out,a.model)
    with ThreadPoolExecutor(a.jobs) as pool:
        outcomes = list(pool.map(execute,plan))
    metadata = dict(cli=version,model=a.model,workers=a.jobs,attempts=len(plan),
                    wall_s=round(time.perf_counter()-start,3),disabled_features=DISABLE)
    (a.out/"run.json").write_text(json.dumps(metadata,indent=2)+"\n")
    return 2 if "BLOCKED" in outcomes else int("FAIL" in outcomes)


if __name__ == "__main__":
    raise SystemExit(main())
