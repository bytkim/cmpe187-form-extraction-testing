"""Score a response independently from the model. Return individual field checks."""
import json
import re
import unicodedata

MISSING = "<missing>"
SUMMARY = {
    "name": r"\bjames\s+okafor\b",
    "dob": r"\b(?:07/22/1988|july\s+22,?\s+1988|22\s+july\s+1988)\b",
    "allergy": r"\bpenicillin\b",
    "medication_1": r"\blisinopril\s*[,:(-]?\s*10\s*mg\b[\s,():-]*(?:once\s+)?(?:daily|a\s+day|per\s+day)\b",
    "medication_2": r"\bmetformin\s*[,:(-]?\s*500\s*mg\b[\s,():-]*(?:twice\s+(?:daily|a\s+day|per\s+day)|two\s+times\s+(?:daily|a\s+day))\b",
}


def unique_pairs(pairs):
    obj = dict(pairs)
    if len(obj) != len(pairs):
        raise ValueError("duplicate JSON key")
    return obj


def parse(raw):
    raw = raw.strip()
    fenced = re.fullmatch(r"\x60{3}(?:json)?\s*(.*?)\s*\x60{3}", raw, re.DOTALL | re.I)
    data = json.loads(fenced.group(1) if fenced else raw, object_pairs_hook=unique_pairs)
    if not isinstance(data, dict):
        raise ValueError("expected a flat JSON object")
    return data


def field_check(key, expected, observed):
    if observed == MISSING:
        error = "O3"
    elif observed == expected and type(observed) is type(expected):
        error = "O5" if observed == "[illegible]" else "O1"
    elif expected is None and observed is not None:
        error = "O4"
    else:
        error = "O2"
    return {"key": key, "expected": expected, "observed": observed,
            "class": error, "ok": error in {"O1", "O5"}}


def assess(case, raw):
    expected = case["oracle"]
    issues = []
    if case["variant"] == "summary":
        prose = unicodedata.normalize("NFC", raw.lower()).replace("*", "").replace("–", "-").replace("—", "-")
        checks = [field_check(k, v, v if re.search(SUMMARY[k], prose) else MISSING)
                  for k, v in expected.items()]
    else:
        try:
            data = parse(raw)
        except ValueError as error:
            # Accept a whole-image abstention only when it cannot contain extracted guesses.
            abstains = re.fullmatch(r"(?:the |this )?(?:image|form|text) (?:is|appears) "
                                    r"(?:completely |too )?(?:unreadable|illegible|blurry to read)[.!]?",
                                    raw.strip(), re.I)
            if case["variant"] == "severe" and abstains:
                data = dict.fromkeys(expected, "[illegible]")
            else:
                data = {}
                issues.append("O6: no parseable extraction (" + str(error) + ")")
        checks = [field_check(k, v, data.get(k, MISSING)) for k, v in expected.items()]
        for key in sorted(data.keys() - expected.keys()):
            issues.append("O2: unexpected field " + key)
    labels = sorted({c["class"] for c in checks})
    return {"pass": all(c["ok"] for c in checks) and not issues, "checks": checks,
            "issues": issues, "classes": labels}
