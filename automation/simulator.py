"""Serve the local case browser, scorer and single-case Codex runner on loopback."""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import urlparse, parse_qs
from oracle import assess

ROOT = Path(__file__).resolve().parent
CASES = {c["id"]: c for c in json.loads((ROOT/"fixtures/manifest.json").read_text())}


class Simulator(BaseHTTPRequestHandler):
    def send_data(self, mime, body, status=200):
        self.send_response(status)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/":
            return self.send_data("text/html; charset=utf-8", (ROOT/"simulator.html").read_bytes())
        if url.path == "/cases":
            return self.send_data("application/json", json.dumps(list(CASES.values())).encode())
        q = parse_qs(url.query)
        c = CASES.get(q.get("id", [""])[0])
        if not c:
            return self.send_error(404)
        if url.path == "/image":
            return self.send_data("image/png", (ROOT/"fixtures"/c["image"]).read_bytes())
        if url.path == "/inspect":
            backend = q.get("backend",["codex-cli"])[0]
            if backend not in ("codex-cli","chatgpt-web"):
                return self.send_error(400)
            results = []
            for p in sorted((ROOT.parent/"evidence"/backend).rglob(c["id"]+"-*.json")):
                r=json.loads(p.read_text())
                results.append(dict(rep=r["rep"],raw=r.get("raw"),blocked=r.get("infrastructure_error"),
                                    score=assess(c,r["raw"]) if "raw" in r else None))
            return self.send_data("application/json",json.dumps(results).encode())
        self.send_error(404)

    def do_POST(self):
        url = urlparse(self.path)
        if self.headers.get("X-Form-Simulator") != "1" or self.headers.get("Host") != f"127.0.0.1:{self.server.server_port}":
            return self.send_error(403)
        case = parse_qs(url.query).get("id",[""])[0]
        if url.path != "/run" or case not in CASES:
            return self.send_error(400)
        target = Path(tempfile.mkdtemp(prefix="form-cvs-demo-")) / "new-run"
        result = subprocess.run([sys.executable,"-u",str(ROOT/"run_codex.py"),"--case",case,
                                 "--repeat","1","--out",str(target)],capture_output=True,text=True)
        logs = [json.loads(p.read_text()) for p in sorted(target.glob("TC*.json"))]
        self.send_data("application/json",json.dumps(dict(log=result.stdout+result.stderr,receipts=logs,
                                                         directory=str(target))).encode())


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--port",type=int,default=18780)
    a=p.parse_args()
    print(f"Open http://127.0.0.1:{a.port}  (Ctrl+C to stop)",flush=True)
    ThreadingHTTPServer(("127.0.0.1",a.port),Simulator).serve_forever()
