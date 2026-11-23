"""Re-score saved responses and export auditable field and attempt statistics."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
from oracle import assess, parse, MISSING

ROOT = Path(__file__).resolve().parent


def write_csv(path, rows):
    if rows:
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)


def evaluate(fixtures, evidence):
    cases = json.loads((fixtures / "manifest.json").read_text())
    by_id = {c["id"]: c for c in cases}
    records, attempts, fields = [], [], []
    seen = set()
    for c in cases:
        assert hashlib.sha256((fixtures / c["image"]).read_bytes()).hexdigest() == c["sha256"]
    for path in sorted(evidence.rglob("TC*-*.json")):
        r = json.loads(path.read_text())
        c = by_id[r["id"]]
        identity = (r["id"], r["rep"])
        if identity in seen:
            raise ValueError("Duplicate attempt in " + str(path))
        if r["sha256"] != c["sha256"] or r["prompt"] != c["prompt"]:
            raise ValueError("Fixture or prompt mismatch in " + str(path))
        seen.add(identity)
        records.append(r)
        base = dict(id=c["id"], rep=r["rep"])
        result = {"pass": False, "checks": [], "issues": [r.get("infrastructure_error", "")]}
        status = "BLOCKED"
        smoke = None
        if "raw" in r:
            result = assess(c, r["raw"])
            status = "PASS" if result["pass"] else "FAIL"
            if c["variant"] == "summary":
                smoke = bool(r["raw"].strip())
            else:
                try:
                    smoke = bool(parse(r["raw"]))
                except ValueError:
                    smoke = False
        attempts.append(dict(**base, status=status, conventional_pass=smoke,
                             correct=sum(x["ok"] for x in result["checks"]), total=len(result["checks"]),
                             seconds=r.get("elapsed_s"), issues=" | ".join(result["issues"])))
        fields.extend(dict(**base, **x) for x in result["checks"])
    repeats = [r for r in records if r["id"] == "TC16" and "raw" in r]
    agreement = None
    if len(repeats) >= 3:
        objects = []
        for r in sorted(repeats, key=lambda x: x["rep"])[:3]:
            try:
                objects.append(parse(r["raw"]))
            except ValueError:
                objects.append({})
        keys = by_id["TC16"]["oracle"]
        common = sum(all(k in o for o in objects) and len({json.dumps(o[k],sort_keys=True) for o in objects}) == 1 for k in keys)
        agreement = dict(identical=common, total=len(keys), meets_95=common/len(keys)>=0.95,
                         all_three_correct=all(a["status"]=="PASS" for a in attempts if a["id"]=="TC16" and a["rep"]<=3))
    done = [a for a in attempts if a["status"] != "BLOCKED"]
    summary = dict(status=dict(Counter(a["status"] for a in attempts)),
                   scenario_ids=sorted({a["id"] for a in done}), correct_fields=sum(f["ok"] for f in fields),
                   total_fields=len(fields), errors=dict(Counter(f["class"] for f in fields if not f["ok"])),
                   observed_classes=sorted({f["class"] for f in fields} | {s.split(":")[0] for a in done for s in a["issues"].split(" | ") if s}),
                   conventional_pass=sum(a["conventional_pass"] for a in done),
                   seconds=sum(a["seconds"] or 0 for a in done), agreement=agreement)
    return summary, attempts, fields


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("evidence",type=Path)
    p.add_argument("--fixtures",type=Path,default=ROOT/"fixtures")
    p.add_argument("--out",type=Path,required=True,help="new statistics directory")
    a=p.parse_args()
    summary, attempts, fields = evaluate(a.fixtures, a.evidence)
    a.out.mkdir(parents=True,exist_ok=False)
    write_csv(a.out/"attempts.csv",attempts)
    write_csv(a.out/"fields.csv",fields)
    (a.out/"summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    for row in attempts:
        print(f'{row["id"]}  #{row["rep"]}  {row["status"]:7} {row["correct"]:2}/{row["total"]:<2}  fields')
    print(json.dumps(summary,indent=2))
