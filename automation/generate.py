"""Compile the team's 16 decision-table rows into images, prompts and field oracles."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
LABELS = {"name": "Full name", "dob": "Date of birth", "medication_1": "Medication 1",
          "medication_2": "Medication 2", "work_authorized": "Authorized to work",
          "start_date": "Available start date"}
PROMPT = ("Extract every field from this form and return JSON. Use null for blank fields "
          "and write [illegible] for anything you can't read.")
SUMMARY_KEYS = ["name", "dob", "allergy", "medication_1", "medication_2"]


def read(path):
    return json.loads(path.read_text())


def font(family, size):
    return ImageFont.truetype(str(DATA / "fonts" / (family + ".ttf")), size)


def print_phone(image, text, y):
    digits = read(DATA / "digits.json")["digits"]
    pen = ImageDraw.Draw(image)
    x = 354
    for ch in text:
        if ch.isdigit():
            tile = Image.new("L", (8, 8))
            tile.putdata([255 - round(230 * p / 16) for p in digits[ch]["pixels"]])
            image.paste(tile.resize((26, 32), Image.Resampling.BICUBIC), (x, y))
            x += 27
        else:
            pen.text((x, y), ch, font=font("kalam", 27), fill="#22374a")
            x += 14


def make_page(form, fields, variant):
    width, height = 1080, 202 + 62 * len(fields)
    page = Image.new("RGB", (width, height), "#ffffff")
    pen = ImageDraw.Draw(page)
    pen.text((50, 30), "JOB APPLICATION" if form == "job" else "MEDICAL INTAKE",
             font=font("lato", 49), fill="#162e46")
    pen.text((52, 96), "Applicant information" if form == "job" else "Patient information",
             font=font("lato", 23), fill="#4c606f")
    pen.line((50, 140, width - 50, 140), fill="#526a7c", width=3)
    face = {"print": "kalam", "cursive": "dancingscript"}.get(variant, "lato")
    for index, (key, value) in enumerate(fields.items()):
        y = 162 + 62 * index
        pen.text((52, y), LABELS.get(key, key.replace("_", " ").capitalize()), font=font("lato", 27), fill="#304454")
        pen.line((51, y + 48, width - 50, y + 48), fill="#d3dce0", width=1)
        if isinstance(value, bool):
            pen.rectangle((356, y + 4, 384, y + 32), outline="#172e3e", width=2)
            if value or (key == "asthma" and variant == "correct"):
                pen.line([(360, y + 17), (367, y + 25), (381, y + 8)], fill="#162a3d", width=4)
            if variant == "correct" and key == "asthma":
                pen.line((350, y - 1, 389, y + 38), fill="#7b372e", width=4)
                pen.line((389, y - 1, 350, y + 38), fill="#7b372e", width=4)
                pen.text((405, y), "void", font=font("kalam", 27), fill="#7b372e")
        elif variant == "print" and key == "phone":
            print_phone(page, value, y)
        elif value is not None:
            pen.text((354, y - 1), value, font=font(face, 31), fill="#132839")
        if variant == "severe":
            box = (344, y - 2, 1026, y + 45)
            area = page.crop(box).filter(ImageFilter.GaussianBlur(25))
            page.paste(area, box)
        if variant == "glare" and key == "asthma":
            pen.ellipse((345, y - 5, 403, y + 42), fill="white")
        if variant == "crease" and key == "medication_2":
            pen.line([(300, y + 38), (591, y + 22), (1000, y + 1)], width=4, fill="#b9b8b5")
    return page


def transform(page, v):
    if v == "scan":
        return page
    if v == "dark":
        page = ImageEnhance.Brightness(page).enhance(0.42)
    if v == "blur":
        page = page.filter(ImageFilter.GaussianBlur(1.6))
    if v == "glare":
        page = page.rotate(10, Image.Resampling.BICUBIC, expand=True, fillcolor="#73787a")
    if v == "rotate":
        page = page.transpose(Image.Transpose.ROTATE_180)
    canvas = Image.new("RGB", (page.width + 36, page.height + 36), "#687177")
    canvas.paste(page, (18, 18))
    return canvas


def generate(out):
    out.mkdir(parents=True, exist_ok=True)
    records = read(DATA / "records.json")
    cases = read(DATA / "scenarios.json")
    for case in cases:
        v = case["variant"]
        fields = dict(records[case["form"]])
        if v == "blank":
            fields.update(email=None, secondary_insurance=None)
        if v == "accent":
            fields["name"] = "José Muñoz-Ortega"
        if v == "correct":
            fields["heart_disease"] = True
        page = transform(make_page(case["form"], fields, v), v)
        path = out / (case["id"] + ".png")
        page.save(path)
        case["image"] = path.name
        case["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        case["dimensions"] = list(page.size)
        case["prompt"] = (PROMPT + " Use one flat object with these keys: " + ", ".join(fields) +
                          ". Use true/false for boxes. Preserve printed text and punctuation.")
        case["oracle"] = fields.copy()
        case["allow_illegible"] = []
        if v == "summary":
            case["prompt"] = "What does this form say?"
            case["oracle"] = {k: fields[k] for k in SUMMARY_KEYS}
        if v == "severe":
            case["oracle"] = dict.fromkeys(fields, "[illegible]")
        if v == "glare":
            case["oracle"]["asthma"] = "[illegible]"  # Flash erased the whole mark.
        print(f'{case["id"]}  {case["context"]} x {case["input"]:3}  {case["target"]:15} {path.name}  {case["sha256"][:10]}')
    (out / "manifest.json").write_text(json.dumps(cases, indent=2, ensure_ascii=False) + "\n")
    return cases


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "fixtures")
    generate(parser.parse_args().out)
