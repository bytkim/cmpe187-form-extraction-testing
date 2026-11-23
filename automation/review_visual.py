"""Repeat the two-case visual review using a fresh CLI reviewer and no answer key."""
import argparse
import json
from pathlib import Path
import subprocess
import tempfile
import time
from run_codex import DISABLE, MODEL, ROOT


def review(out):
    out.mkdir(parents=True,exist_ok=False)
    for case_id in ["TC01","TC04"]:
        source=json.loads((ROOT.parent/"evidence/chatgpt-web"/(case_id+"-1.json")).read_text())
        prompt=("Visually review the response below against the attached form. For each field, confirm "
                "that the supplied answer is supported by visible evidence. Use the original prompt's "
                "rules. Check whether each checkbox border and its mark area are visible before accepting "
                "a Boolean. Return one JSON object with verdict PASS or FAIL and discrepancies, an array "
                "of field names and explanations. Do not use tools.\nOriginal prompt:\n"+source["prompt"]+
                "\nResponse to inspect:\n"+source["raw"])
        with tempfile.TemporaryDirectory() as scratch:
            work=Path(scratch)
            (work/"form.png").write_bytes((ROOT/"fixtures"/(case_id+".png")).read_bytes())
            cmd=["codex","exec","--ignore-user-config","--ephemeral","--skip-git-repo-check",
                 "--sandbox","read-only","-C",scratch,"-m",MODEL,"-c",'model_reasoning_effort="low"',
                 "-c",'web_search="disabled"',"--json"]
            for f in DISABLE:
                cmd.extend(["--disable",f])
            cmd.extend(["--image","form.png","-o","review.txt","-"])
            t=time.perf_counter()
            r=subprocess.run(cmd,input=prompt,text=True,capture_output=True,cwd=work,timeout=180,check=True)
            elapsed=round(time.perf_counter()-t,3)
            events=[json.loads(s) for s in r.stdout.splitlines() if s.startswith("{")]
            assert all(e["item"]["type"] in ("agent_message","reasoning") for e in events if "item" in e)
            ans=(work/"review.txt").read_text()
        receipt=dict(reviewer=MODEL,role="visual review of a saved web response",case=case_id,
                     sha256=source["sha256"],prompt=prompt,raw=ans,seconds=elapsed)
        (out/(case_id+".json")).write_text(json.dumps(receipt,indent=2))
        print(case_id,elapsed,ans,flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--out",type=Path,required=True)
    review(p.parse_args().out)
