"""Run the image tests using a dedicated local Playwright browser profile."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
from oracle import assess

ROOT = Path(__file__).resolve().parent


def prepare(page):
    page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
    page.get_by_role("textbox", name="Ask ChatGPT").wait_for(timeout=45000)
    page.get_by_role("button", name="Temporary chat", exact=True).click()
    dialog = page.get_by_role("dialog", name="Temporary chat")
    if dialog.is_visible():
        dialog.get_by_role("button", name="Continue").click()
    page.get_by_role("button", name="Turn off temporary chat").wait_for()


def extract(page, case, image):
    prepare(page)
    page.get_by_role("button", name="Add files and more").click()
    if page.get_by_role("button", name="Get Plus for more uploads", exact=False).is_visible():
        raise RuntimeError("Account upload allowance exhausted")
    with page.expect_file_chooser() as chooser:
        page.get_by_role("button", name="Add photos & files", exact=False).click()
    chooser.value.set_files(str(image))
    page.get_by_role("img", name=image.name, exact=True).wait_for(timeout=45000)
    page.get_by_role("textbox", name="Ask ChatGPT").fill(case["prompt"])
    page.get_by_role("button", name="Send", exact=True).click()
    page.get_by_role("button", name="Copy", exact=True).wait_for(timeout=120000)
    # Consumer UI selectors can change. Preserve the complete displayed answer.
    answer = page.locator('[class*="DilResponseRoot-"], [data-message-author-role="assistant"]')
    raw = answer.last.inner_text()
    return raw.removeprefix("JSON\n"), raw


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--profile", type=Path, required=True, help="separate Chrome test profile")
    p.add_argument("--out", type=Path, required=True, help="new evidence directory")
    p.add_argument("--case", nargs="+")
    p.add_argument("--repeat", type=int, default=1)
    a = p.parse_args()
    cases = json.loads((ROOT / "fixtures/manifest.json").read_text())
    if a.repeat < 1 or a.case and set(a.case) - {c["id"] for c in cases}:
        p.error("Choose valid case IDs and a positive repeat count")
    a.out.mkdir(parents=True, exist_ok=False)
    failed = False
    with sync_playwright() as pw:
        ctx = pw.chromium.launch_persistent_context(str(a.profile), channel="chrome", headless=False)
        page = ctx.new_page()
        page.goto("https://chatgpt.com/")
        input("Sign into this test profile, dismiss welcome dialogs, then press Enter here. ")
        for c in cases:
            if a.case and c["id"] not in a.case:
                continue
            image = ROOT / "fixtures" / c["image"]
            assert hashlib.sha256(image.read_bytes()).hexdigest() == c["sha256"]
            for r in range(1, max(a.repeat, 3 if c["id"] == "TC16" else 1) + 1):
                started = time.perf_counter()
                rec = dict(id=c["id"], rep=r, prompt=c["prompt"], sha256=c["sha256"],
                           backend="ChatGPT web", started_utc=datetime.now(timezone.utc).isoformat())
                try:
                    rec["raw"], rec["visible_text"] = extract(page, c, image)
                    status = "PASS" if assess(c, rec["raw"])["pass"] else "FAIL"
                except (BrowserTimeout, RuntimeError) as error:
                    rec["infrastructure_error"] = str(error)
                    status = "BLOCKED"
                rec["elapsed_s"] = round(time.perf_counter() - started, 3)
                (a.out / f'{c["id"]}-{r}.json').write_text(json.dumps(rec, indent=2))
                print(c["id"], r, status, flush=True)
                if status == "BLOCKED":
                    ctx.close()
                    return 2
                failed |= status == "FAIL"
        ctx.close()
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
