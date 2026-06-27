"""Decoupling Part 1 carve: losslessly split the canonical, lyric-skinned
rc-lyric-rubric.json into two layers.

  le-baseline/le-scaffold.json  structure + governance metadata (tiers, axes,
                           ranges, ids, numbers, rule layer tags, versioning, changelog)
  rc-lyric/rc-lyric-text.json   the exact human-readable strings (tier definitions,
                           tenet text, note title+text, rule text, modifier and
                           flag prose) -- the lyric lens, lifted verbatim

Recombining scaffold + lyric text must reproduce the original rc-lyric-rubric.json exactly
(deep dict equality). That equality is the parity proof: because RC renders from
the recombined structure, its prompt is byte-for-byte unchanged.

The baseline's domain-neutral cores are a SEPARATE layer (le-baseline/le-cores.json),
authored by hand and reviewed as data. They do not participate in the lyric
render, so introducing them cannot move RC's output. New lenses (Lyric
Transformer, Creative Charger) derive their own text from the neutral cores via
their own glossary.

Run:  cd backend && .venv/Scripts/python.exe -m app.rubric.lec_carve
"""
import json
from pathlib import Path

# NOTE: this script lives in app/rubric/_snapshots/, so paths climb one extra level.
AGENTS = Path(__file__).resolve().parent.parent.parent / "services" / "agents"
CORE_PATH = AGENTS / "rc-lyric-live" / "rc-lyric-rubric.json"

OUT = Path(__file__).resolve().parent.parent  # app/rubric (holds le-baseline/ + rc-lyric/)
SCAFFOLD_PATH = OUT / "le-baseline" / "le-scaffold.json"
LYRIC_PATH = OUT / "rc-lyric" / "rc-lyric-text.json"

# Rule layer classification, from the boundary map Section 5. R2/R3 are pure
# baseline; R1 (pop-romance hyperbole) and R12 (pop-era conventions) are
# lyric-lens rules; the rest are universal cores wearing lyric examples (the
# core/example separation is a later authoring step, like the tenet cores).
RULE_LAYER = {
    "R1": "lyric", "R2": "baseline", "R3": "baseline", "R4": "baseline",
    "R5": "baseline", "R6": "baseline", "R7": "baseline", "R8": "baseline",
    "R9": "baseline", "R10": "baseline", "R11": "baseline", "R12": "lyric",
    "R13": "baseline", "R14": "baseline", "R15": "baseline",
    "R16": "baseline",
}


def split(core: dict):
    scaffold = {
        "schema_version": core["schema_version"],
        "ratified_at": core["ratified_at"],
        "changelog": core["changelog"],  # constitution governance; moves in Part 2
        "tiers": [],
        "modifiers": [],
        "flags": [],
        "rules": [],
    }
    text = {
        "lens": "rc-lyric",
        "artifact_type": "lyric",
        "glossary": {
            "the work": "the song",
            "the speaker": "the narrator",
            "the text": "the lyrics",
            "a private 1:1 bond": "1:1 romance",
        },
        "tiers": [],
        "modifiers": [],
        "flags": [],
        "rules": [],
    }

    for t in core["tiers"]:
        scaffold["tiers"].append({
            "slug": t["slug"],
            "axis": t["axis"],
            "label": t["label"],
            "code": t["code"],
            "color_hex": t["color_hex"],
            "charge_range": t["charge_range"],
            "tenets": [
                {"id": x["id"], "number": x["number"], "version": x["version"],
                 "ratified_at": x["ratified_at"], "status": x["status"]}
                for x in t["tenets"]
            ],
            "notes": [
                {"id": n["id"], "version": n["version"],
                 "ratified_at": n["ratified_at"], "status": n["status"]}
                for n in t.get("notes", [])
            ],
        })
        text["tiers"].append({
            "slug": t["slug"],
            "definition": t["definition"],
            "tenets": [{"id": x["id"], "text": x["text"]} for x in t["tenets"]],
            "notes": [{"id": n["id"], "title": n["title"], "text": n["text"]}
                      for n in t.get("notes", [])],
        })

    for m in core["modifiers"]:
        scaffold["modifiers"].append({
            "id": m["id"], "label": m["label"], "version": m["version"],
            "ratified_at": m["ratified_at"], "status": m["status"],
        })
        text["modifiers"].append({
            "id": m["id"], "definition": m["definition"], "body": m["body"],
            "examples": m["examples"], "closing": m["closing"],
        })

    for f in core["flags"]:
        scaffold["flags"].append({
            "id": f["id"], "label": f["label"], "version": f["version"],
            "ratified_at": f["ratified_at"], "status": f["status"],
        })
        text["flags"].append({
            "id": f["id"], "definition": f["definition"], "body": f["body"],
            "examples": f["examples"], "closing": f["closing"],
            "prompt_block": f["prompt_block"],
        })

    for r in core["rules"]:
        scaffold["rules"].append({
            "id": r["id"], "layer": RULE_LAYER.get(r["id"], "baseline"),
            "version": r["version"], "ratified_at": r["ratified_at"], "status": r["status"],
        })
        entry = {"id": r["id"]}
        if "title" in r:
            entry["title"] = r["title"]
        entry["text"] = r["text"]
        text["rules"].append(entry)

    return scaffold, text


def recombine(scaffold: dict, text: dict) -> dict:
    tx_tiers = {t["slug"]: t for t in text["tiers"]}
    tx_mods = {m["id"]: m for m in text["modifiers"]}
    tx_flags = {f["id"]: f for f in text["flags"]}
    tx_rules = {r["id"]: r for r in text["rules"]}

    core = {
        "schema_version": scaffold["schema_version"],
        "ratified_at": scaffold["ratified_at"],
        "changelog": scaffold["changelog"],
        "tiers": [], "modifiers": [], "flags": [], "rules": [],
    }

    for st in scaffold["tiers"]:
        tt = tx_tiers[st["slug"]]
        tt_ten = {x["id"]: x["text"] for x in tt["tenets"]}
        tt_notes = {n["id"]: n for n in tt["notes"]}
        core["tiers"].append({
            "slug": st["slug"], "axis": st["axis"], "label": st["label"],
            "code": st["code"], "color_hex": st["color_hex"],
            "charge_range": st["charge_range"], "definition": tt["definition"],
            "tenets": [
                {"id": x["id"], "number": x["number"], "text": tt_ten[x["id"]],
                 "version": x["version"], "ratified_at": x["ratified_at"], "status": x["status"]}
                for x in st["tenets"]
            ],
            "notes": [
                {"id": n["id"], "title": tt_notes[n["id"]]["title"],
                 "text": tt_notes[n["id"]]["text"], "version": n["version"],
                 "ratified_at": n["ratified_at"], "status": n["status"]}
                for n in st["notes"]
            ],
        })

    for sm in scaffold["modifiers"]:
        tm = tx_mods[sm["id"]]
        core["modifiers"].append({
            "id": sm["id"], "label": sm["label"], "version": sm["version"],
            "ratified_at": sm["ratified_at"], "status": sm["status"],
            "definition": tm["definition"], "body": tm["body"],
            "examples": tm["examples"], "closing": tm["closing"],
        })

    for sf in scaffold["flags"]:
        tf = tx_flags[sf["id"]]
        core["flags"].append({
            "id": sf["id"], "label": sf["label"], "version": sf["version"],
            "ratified_at": sf["ratified_at"], "status": sf["status"],
            "definition": tf["definition"], "body": tf["body"],
            "examples": tf["examples"], "closing": tf["closing"],
            "prompt_block": tf["prompt_block"],
        })

    for sr in scaffold["rules"]:
        tr = tx_rules[sr["id"]]
        entry = {"id": sr["id"]}
        if "title" in tr:
            entry["title"] = tr["title"]
        entry["text"] = tr["text"]
        entry["version"] = sr["version"]
        entry["ratified_at"] = sr["ratified_at"]
        entry["status"] = sr["status"]
        core["rules"].append(entry)

    return core


def main() -> int:
    with open(CORE_PATH, encoding="utf-8") as f:
        original = json.load(f)

    scaffold, text = split(original)
    rebuilt = recombine(scaffold, text)

    if rebuilt != original:
        # Surface the first divergence for debugging.
        print("PARITY FAIL: recombined core != original rc-lyric-rubric.json")
        for key in original:
            if original.get(key) != rebuilt.get(key):
                print(f"  divergent top-level key: {key}")
        return 1

    SCAFFOLD_PATH.parent.mkdir(parents=True, exist_ok=True)
    LYRIC_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SCAFFOLD_PATH, "w", encoding="utf-8") as f:
        json.dump(scaffold, f, indent=2, ensure_ascii=True)
        f.write("\n")
    with open(LYRIC_PATH, "w", encoding="utf-8") as f:
        json.dump(text, f, indent=2, ensure_ascii=True)
        f.write("\n")

    tiers = len(original["tiers"])
    tenets = sum(len(t["tenets"]) for t in original["tiers"])
    rules = len(original["rules"])
    print("PARITY OK: recombine(scaffold, lyric_text) == rc-lyric-rubric.json (deep-equal)")
    print(f"  carved {tiers} tiers, {tenets} tenets, "
          f"{len(original['modifiers'])} modifier(s), {len(original['flags'])} flag(s), {rules} rules")
    print(f"  wrote {SCAFFOLD_PATH.relative_to(OUT.parent)}")
    print(f"  wrote {LYRIC_PATH.relative_to(OUT.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
