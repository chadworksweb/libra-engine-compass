"""The compass-evolution view -- the public "How the Compass Changed Its Mind"
timeline (lecg-).

The public /evolution/ page (governance-owned, hosted on the lec instrument)
renders window.EVOLUTION_DATA: the story of how the LAW matured. It is sourced
ENTIRELY from LEC's own governed data -- the le-scaffold changelog (the ratified
rule/law changes) plus the reading-lens additions -- never from Rising Compass.
The per-song calibration history is RC product data and lives in RC; this page is
the compass changing ITS mind (how to read), not a song's score changing.

build_evolution() -> the render-ready dict; render_data_js() -> the
window.EVOLUTION_DATA = {...}; string served at /evolution/evolution-data.js.
"""

from __future__ import annotations

import json

from governance.lecg_constitution import load_constitution


# Reading-lens + modifier additions are not in the le-scaffold changelog (that is
# the LAW/rules changelog). They are curated here with explicit provenance until a
# machine-readable lens_changelog exists; dates are the ratification dates in the
# lens/modifier source files.
LENS_TIMELINE = [
    {
        "date": "2026-06-19",
        "kind": "lens",
        "headline": "Satire reading modifier",
        "body": "A universal clip-on lens. Apply the standard rubric first, then "
                "re-read the same words asking a different question: do they expose "
                "the behavior they depict, or endorse it? Depiction is not "
                "endorsement when the structure inverts the surface meaning (S1-S8). "
                "If the words still endorse with the lens applied, the calibration "
                "does not move.",
        "source": "le-satire.json (authored 2026-06-19, register A, universal)",
    },
    {
        "date": "2026-06-21",
        "kind": "lens",
        "headline": "Inhabited-voice reading lens",
        "body": "The earnest sibling of satire. Some works inhabit a degraded or "
                "suffering state in order to witness it, with no irony. The gate is "
                "an in-the-words turn: the chorus or ending shifts from inhabiting "
                "the state to reflecting on it. No turn, and the literal reading "
                "stands. Witness with no exit caps at Decent; witness plus a named "
                "path reaches low Elevated.",
        "source": "rc-lyric-inhabited-voice.md (ratified 2026-06-21, lyric lens)",
    },
]


def _headline(summary: str) -> str:
    """A short title from a changelog summary: the first clause (to the first
    colon if it comes early) or the first sentence."""
    s = (summary or "").strip()
    if not s:
        return "Law change"
    head = s.split(":", 1)[0] if (":" in s[:100]) else s.split(". ", 1)[0]
    return head[:140]


def _changelog_entry(e: dict) -> dict:
    """Map one le-scaffold changelog entry to the public timeline shape."""
    return {
        "date": e.get("at", ""),
        "kind": "law",
        "headline": _headline(e.get("summary", "")),
        "body": e.get("summary", ""),
        "source": e.get("source", ""),
    }


def build_evolution() -> dict:
    """The render-ready compass-evolution timeline, newest first."""
    c = load_constitution()
    entries = [_changelog_entry(e) for e in c.get("changelog", [])]
    entries += [dict(x) for x in LENS_TIMELINE]
    # Newest first. Dates are ISO (YYYY-MM-DD), so a string sort orders them.
    entries.sort(key=lambda x: x.get("date", ""), reverse=True)
    return {
        "constitution_version": c["constitution_version"],
        "schema_version": c.get("schema_version"),
        "ratified_at": c.get("ratified_at"),
        "rule_count": len(c.get("rules", [])),
        "tenet_count": sum(len(t["tenets"]) for t in c.get("tiers", [])),
        "entries": entries,
    }


def render_data_js() -> str:
    """The window.EVOLUTION_DATA assignment served at /evolution/evolution-data.js."""
    body = json.dumps(build_evolution(), ensure_ascii=True, separators=(",", ":"))
    return f"window.EVOLUTION_DATA = {body};\n"


if __name__ == "__main__":
    v = build_evolution()
    print(f"constitution_version: {v['constitution_version']}")
    print(f"{len(v['entries'])} timeline entries; "
          f"{v['rule_count']} rules, {v['tenet_count']} tenets")
    for e in v["entries"]:
        print(f"  {e['date']}  [{e['kind']:4}]  {e['headline']}")
    print(f"render_data_js bytes: {len(render_data_js())}")
