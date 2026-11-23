"""Run individual stages of the recorded form-extraction demonstration."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from PIL import __version__ as pillow_version
from generate import generate, make_page, transform, DATA
from oracle import assess
from metrics import measure
from score import evaluate
from source_digits import discover

ROOT = Path(__file__).resolve().parent


def setup(work):
    print(f"Python {sys.version.split()[0]} / Pillow {pillow_version}")
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



def augment(work):
    """Rebuild two derived images and verify the pixels and their field oracles."""
    cases = {c["id"]: c for c in json.loads((work / "images/manifest.json").read_text())}
    fields = json.loads((DATA / "records.json").read_text())["medical"]
    for cid, recipe in [("TC03", "Brightness x 0.42"), ("TC04", "Hide asthma mark; rotate 10 degrees")]:
        case = cases[cid]
        output = work / f"{cid}-augmented.png"
        transform(make_page("medical", fields, case["variant"]), case["variant"]).save(output)
        digest = hashlib.sha256(output.read_bytes()).hexdigest()
        if digest != case["sha256"]:
            raise ValueError(f"{cid} does not match the generated image")
        changes = [k for k, v in case["oracle"].items() if v != cases["TC02"]["oracle"][k]]
        print(f"TC02 -> {cid}   {recipe}")
        print(f"  Image SHA-256  {digest[:16]}...  matches manifest")
        if changes:
            for k in changes:
                print(f"  {k}: {json.dumps(cases['TC02']['oracle'][k])} -> {json.dumps(case['oracle'][k])}")
        else:
            print("  All 12 expected values preserved")


def inspect_take(work):
    cases = {c["id"]: c for c in json.loads((work / "images/manifest.json").read_text())}
    for case_id, keys in [("TC04", ("asthma",)), ("TC14", ("email", "secondary_insurance"))]:
        receipt = json.loads((work / "fresh" / f"{case_id}-1.json").read_text())
        checks = assess(cases[case_id], receipt["raw"])["checks"]
        print(f"{case_id}  {sum(f['ok'] for f in checks)}/{len(checks)} field checks passed")
        for field in checks:
            if field["key"] in keys:
                print(f"  {field['key']}  expected {json.dumps(field['expected'])}  returned {json.dumps(field['observed'])}")
    summary, _, _ = evaluate(work / "images", work / "fresh")
    print("Fresh take:", summary["status"])
    a = summary["agreement"]
    if a:
        print(f"TC16: {a['identical']}/{a['total']} fields identical across three fresh runs")


def costs():
    m = measure()
    s = m["codex"]
    print("MEASURED COST / frozen Codex campaign")
    print(f"{sum(s['status'].values())} requests; {s['seconds']:.3f} aggregate request seconds")
    print(f"Median {m['median_request_s']:.3f} seconds per request")
    print("Input tokens {:,}   cached {:,}   output {:,}".format(
        m["token_totals"]["input_tokens"], m["token_totals"]["cached_input_tokens"], m["token_totals"]["output_tokens"]))
    print("No per-request dollar charge or labor time was measured.")
    print()
    print("SCRIPT                 SOURCE LINES    MAX BRANCH SCORE")
    for name, stats in m["scripts"].items():
        print(f"{name:<23} {stats['nonblank_noncomment_lines']:>4}             {max(stats['function_branch_scores'].values()):>2}")
    print()
    print(f"Coverage: {len(s['scenario_ids'])} scenarios, {m['unique_pairs']} context/input pairs, {m['unique_images']} images.")


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
    p.add_argument("stage",choices=["setup","generate","augment","live","inspect","results","costs"])
    p.add_argument("--work",type=Path,default=Path("demo-work"))
    a=p.parse_args()
    a.work.mkdir(exist_ok=True,parents=True)
    if a.stage=="setup":
        setup(a.work)
    elif a.stage=="generate":
        cases=generate(a.work/"images")
        print("Unique image digests:",len({c["sha256"] for c in cases}))
    elif a.stage=="augment":
        augment(a.work)
    elif a.stage=="inspect":
        inspect_take(a.work)
    elif a.stage=="costs":
        costs()
    elif a.stage=="live":
        live(a.work)
    else:
        results()
