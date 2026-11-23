"""Four short demonstrations for the recorded presentation or a live talk."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from generate import generate
from oracle import assess
from score import evaluate
from source_digits import discover

ROOT = Path(__file__).resolve().parent


def setup(work):
    print(subprocess.check_output(["codex","--version"],text=True).strip())
    print("Opening the UCI handwritten digit archive...",flush=True)
    discover(work/"digits.json")
    source=json.loads((work/"digits.json").read_text())
    assert source==json.loads((ROOT/"data/digits.json").read_text())
    print("Source member:",source["member"])
    print("Training rows:",source["rows_scanned"])
    print("Digit 4: source row",source["digits"]["4"]["row"])
    print("Verified the packaged ten-glyph sample against UCI.")


def live(work):
    out=work/"fresh"
    cmd=[sys.executable,"-u",str(ROOT/"run_codex.py"),"--case","TC14","--repeat","1","--out",str(out)]
    r=subprocess.run(cmd)
    if r.returncode not in (0,1):
        raise RuntimeError("CLI inference did not produce a scored response")
    case=json.loads((ROOT/"fixtures/manifest.json").read_text())[13]
    raw=json.loads((out/"TC14-1.json").read_text())["raw"]
    result=assess(case,raw)
    for field in result["checks"]:
        if field["key"] in ("medication_1","email","secondary_insurance"):
            print(field["key"],"=",json.dumps(field["observed"]),field["class"])
    print("Checks passed:",sum(f["ok"] for f in result["checks"]),"/",len(result["checks"]))


def results():
    for key in ("codex-cli","chatgpt-web"):
        summary,attempts,fields=evaluate(ROOT/"fixtures",ROOT.parent/"evidence"/key)
        print(key,summary["status"])
        print("  Correct field checks:",summary["correct_fields"],"/",summary["total_fields"])
        if summary["agreement"]:
            a=summary["agreement"]
            print("  TC16 agreement:",a["identical"],"/",a["total"])
        for f in fields:
            if f["id"]=="TC04" and not f["ok"]:
                print("  TC04 run",f["rep"],f["key"],"=",json.dumps(f["observed"]))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=["setup","generate","live","results"])
    p.add_argument("--work",type=Path,default=Path("demo-work"))
    a=p.parse_args()
    a.work.mkdir(exist_ok=True,parents=True)
    if a.stage=="setup":
        setup(a.work)
    elif a.stage=="generate":
        cases=generate(a.work/"images")
        print("Unique image digests:",len({c["sha256"] for c in cases}))
    elif a.stage=="live":
        live(a.work)
    else:
        results()
