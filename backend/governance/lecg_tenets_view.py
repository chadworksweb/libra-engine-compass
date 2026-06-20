"""The tenets view -- the render-ready shape of the canonical constitution (lecg-).

The public /tenets/ page (served BY the lecg- venue) renders window.TENETS_DATA.
This module maps the canonical governed constitution to that shape and serializes
it as the JS the page loads. The tenets are the LEC tenets: they live ON LEC and
are served live from here, never a hand-maintained static snapshot.

`build_view()` -> the render-ready dict; `render_data_js()` -> the
`window.TENETS_DATA = {...};` string lecg serves at /tenets/tenets-data.js.

Mapping to the renderer's shape: tier.definition_core -> definition ; tenet.core
-> text ; note.title_core -> title ; modifier/flag/rule .core -> definition/text.
Governance fields (per-item version + ratified_at, the changelog, the governed
constitution_version) ride along for the renderer to surface.
"""

from __future__ import annotations

import json

from governance.lecg_constitution import load_constitution


def _gov(item: dict) -> dict:
    return {"version": item.get("version"), "ratified_at": item.get("ratified_at")}


def build_view() -> dict:
    """Map the canonical constitution to the public tenets-view (TENETS_DATA) shape."""
    c = load_constitution()
    tiers = []
    for t in c["tiers"]:
        tiers.append({
            "slug": t["slug"],
            "color_hex": t["color_hex"],
            "code": t["code"],
            "label": t["label"],
            "definition": t["definition_core"],
            "tenets": [
                {"id": x["id"], "number": x["number"], "text": x["core"], **_gov(x)}
                for x in t["tenets"]
            ],
            "notes": [
                {"title": n.get("title_core", ""), "text": n["core"], **_gov(n)}
                for n in t["notes"]
            ],
        })
    return {
        "constitution_version": c["constitution_version"],
        "schema_version": c["schema_version"],
        "ratified_at": c["ratified_at"],
        "tiers": tiers,
        "modifiers": [
            {"id": m["id"], "label": m["label"], "definition": m["core"], **_gov(m)}
            for m in c["modifiers"]
        ],
        "flags": [
            {"id": f["id"], "label": f["label"], "definition": f["core"], **_gov(f)}
            for f in c["flags"]
        ],
        "rules": [
            {"id": r["id"], "text": r["core"], **_gov(r)}
            for r in c["rules"]
        ],
        "changelog": c["changelog"],
    }


def render_data_js() -> str:
    """The window.TENETS_DATA assignment lecg serves at /tenets/tenets-data.js."""
    body = json.dumps(build_view(), ensure_ascii=True, separators=(",", ":"))
    return f"window.TENETS_DATA = {body};\n"


if __name__ == "__main__":
    v = build_view()
    print(f"constitution_version: {v['constitution_version']}")
    print(f"{len(v['tiers'])} tiers, "
          f"{sum(len(t['tenets']) for t in v['tiers'])} tenets, "
          f"{len(v['rules'])} rules ({v['rules'][-1]['id']} last), "
          f"{len(v['changelog'])} changelog entries")
    print(f"render_data_js bytes: {len(render_data_js())}")
