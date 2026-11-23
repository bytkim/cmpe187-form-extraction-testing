"""Recompute the measurements quoted in the written report."""
import ast
import json
from pathlib import Path
import statistics
import timeit
from oracle import assess
from score import evaluate

ROOT = Path(__file__).resolve().parent


def complexity(script):
    text=(ROOT / script).read_text()
    tree=ast.parse(text)
    # Explicit branch-count convention for this project.
    funcs=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef)]
    result={}
    for f in funcs:
        stack=list(f.body)
        decisions=0
        while stack:
            n=stack.pop()
            if isinstance(n,ast.FunctionDef):
                continue
            decisions+=isinstance(n,(ast.If,ast.For,ast.While,ast.IfExp,ast.ExceptHandler,ast.comprehension))
            if isinstance(n,ast.BoolOp):
                decisions+=len(n.values)-1
            if isinstance(n,ast.comprehension):
                decisions+=len(n.ifs)
            stack.extend(ast.iter_child_nodes(n))
        result[f.name]=1+decisions
    return dict(nonblank_noncomment_lines=sum(bool(s.strip()) and not s.lstrip().startswith("#") for s in text.splitlines()),function_branch_scores=result)


def measure():
    fix=ROOT/"fixtures"
    evidence=ROOT.parent/"evidence"
    cases=json.loads((fix/"manifest.json").read_text())
    cli=list((evidence/"codex-cli").rglob("TC*-*.json"))
    records=[json.loads(p.read_text()) for p in cli]
    scored,_,_=evaluate(fix,evidence/"codex-cli")
    sample=[(c,(evidence/"chatgpt-web"/(c["id"]+"-1.json"))) for c in (cases[0],cases[3])]
    sample=[(c,json.loads(p.read_text())["raw"]) for c,p in sample]
    bench=timeit.repeat(lambda:[assess(c,r) for c,r in sample],number=1000,repeat=5)
    return dict(codex=scored, median_request_s=statistics.median(r["elapsed_s"] for r in records),
                batch_wall_s={p.parent.name:json.loads(p.read_text())["wall_s"] for p in (evidence/"codex-cli").rglob("run.json")},
                token_totals={k:sum(r["usage"][k] for r in records) for k in records[0]["usage"]},
                unique_images=len({c["sha256"] for c in cases}),unique_pairs=len({(c["context"],c["input"]) for c in cases}),
                two_case_grading_ms=statistics.median(bench),scripts={s:complexity(s) for s in ["generate.py","run_codex.py","oracle.py","score.py"]})


if __name__=="__main__":
    print(json.dumps(measure(),indent=2))
