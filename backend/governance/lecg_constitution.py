"""The canonical constitution -- governance-owned (lecg-).

This is the single source of truth for the Libra Engine constitution: the
domain-neutral le- LAW (the tiers, tenets, notes, the contamination modifier,
the dogma flag, the rules R1-R15, the read-method) MERGED WITH its governance
metadata (per-item version / ratified_at / status, and the amendment changelog).

It is assembled from the three le-baseline files that already exist:
  le-cores.json     the neutral moral cores (the law TEXT)
  le-scaffold.json  structure + GOVERNANCE metadata (axis/label/range, ids,
                    numbers, per-item version+ratified_at+status, changelog)
  le-method.json    the universal read-method kernels (the procedure)

Why a governance module and not just the instrument's load_gospel(): load_gospel
drops the governance metadata (it only needs number/layer/axis/core/method to
compose a prompt). Governance needs the FULL governed record -- the versions,
the ratification dates, the changelog -- because that is what the public governs
and what the tenets view renders. This module owns that view, and the governed
constitution_version that the instrument PINS.

constitution_version is the version of the LAW (governance-owned), distinct from
the instrument's rubric_version (a hash of the composed gospel+lens prompt). The
law changes only by ratified amendment; the instrument adopts a new law version
deliberately (Decision 1/4 -- shared-repo version pin, no inter-service HTTP).

NOTE (provisional path): the le-baseline files still live under the instrument's
tree (app/rubric/le-baseline/). The physical move to governance ownership rides
with the lecg- app-skeleton step; this module reads them in place for now.
"""

from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

# Provisional: le-baseline currently lives under the instrument tree. Resolve it
# relative to the repo's backend/ root so the move later is a one-line change.
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
BASELINE_DIR = _BACKEND_ROOT / "app" / "rubric" / "le-baseline"

CORES_PATH = BASELINE_DIR / "le-cores.json"
SCAFFOLD_PATH = BASELINE_DIR / "le-scaffold.json"
METHOD_PATH = BASELINE_DIR / "le-method.json"


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _governance(item: dict) -> dict:
    """Pull the three governance fields off a scaffold item, in a fixed order."""
    return {
        "version": item.get("version"),
        "ratified_at": item.get("ratified_at"),
        "status": item.get("status"),
    }


def _load_dicts(baseline_dir=None):
    """Load the three le-baseline files (cores, scaffold, method) as raw dicts.
    baseline_dir overrides the default location (the adoption round-trip reads a
    temp copy so the real law is never touched by a test)."""
    base = Path(baseline_dir) if baseline_dir else BASELINE_DIR
    return (
        _load_json(base / CORES_PATH.name),
        _load_json(base / SCAFFOLD_PATH.name),
        _load_json(base / METHOD_PATH.name),
    )


def _assemble_from_dicts(cores: dict, scaffold: dict, method: dict) -> dict:
    """Merge cores (text) + scaffold (structure + governance) + method (procedure)
    into one governed canonical constitution, keyed by id. Domain-neutral; carries
    NO lens. This is the full record the public governs."""
    sc_tiers = {t["slug"]: t for t in scaffold["tiers"]}
    sc_rules = {r["id"]: r for r in scaffold["rules"]}
    sc_mods = {m["id"]: m for m in scaffold.get("modifiers", [])}
    sc_flags = {f["id"]: f for f in scaffold.get("flags", [])}

    tiers = []
    for ct in cores["tiers"]:
        st = sc_tiers[ct["slug"]]
        st_ten = {x["id"]: x for x in st["tenets"]}
        st_notes = {x["id"]: x for x in st.get("notes", [])}
        tiers.append({
            "slug": ct["slug"],
            "axis": st["axis"],
            "label": st["label"],
            "code": st.get("code"),
            "color_hex": st.get("color_hex"),
            "charge_range": st["charge_range"],
            "definition_core": ct["definition_core"],
            "tenets": [
                {
                    "id": x["id"],
                    "number": st_ten[x["id"]]["number"],
                    "core": x["core"],
                    **_governance(st_ten[x["id"]]),
                }
                for x in ct["tenets"]
            ],
            "notes": [
                {
                    "id": n["id"],
                    "title_core": n.get("title_core", ""),
                    "core": n["core"],
                    **_governance(st_notes.get(n["id"], {})),
                }
                for n in ct.get("notes", [])
            ],
        })

    modifiers = []
    for cm in cores.get("modifiers", []):
        sm = sc_mods.get(cm["id"], {})
        modifiers.append({
            "id": cm["id"],
            "label": cm.get("label", sm.get("label")),
            "core": cm["core"],
            "lens_owned": cm.get("lens_owned"),
            **_governance(sm),
        })

    flags = []
    for cf in cores.get("flags", []):
        sf = sc_flags.get(cf["id"], {})
        flags.append({
            "id": cf["id"],
            "label": cf.get("label", sf.get("label")),
            "core": cf["core"],
            "lens_owned": cf.get("lens_owned"),
            "instrument_owned": cf.get("instrument_owned"),
            **_governance(sf),
        })

    rules = []
    for cr in cores["rules"]:
        sr = sc_rules.get(cr["id"], {})
        rule = {
            "id": cr["id"],
            "layer": sr.get("layer", cr.get("layer", "baseline")),
            "core": cr["core"],
            **_governance(sr),
        }
        if "kind" in cr:
            rule["kind"] = cr["kind"]
        if "operative_rule_layer" in cr:
            rule["operative_rule_layer"] = cr["operative_rule_layer"]
        rules.append(rule)

    return {
        "schema_version": scaffold.get("schema_version"),
        "ratified_at": scaffold.get("ratified_at"),
        "glossary_contract": cores.get("glossary_contract", {}),
        "tiers": tiers,
        "modifiers": modifiers,
        "flags": flags,
        "rules": rules,
        "method": method,
        "changelog": scaffold.get("changelog", []),
    }


def _assemble(baseline_dir=None) -> dict:
    """Assemble the canonical constitution from the le-baseline files (default
    location, or a baseline_dir override for the adoption round-trip)."""
    return _assemble_from_dicts(*_load_dicts(baseline_dir))


def _version_of(constitution: dict) -> str:
    """Stable short version of the operative LAW. Hashes everything that scores or
    is governed (the cores, structure, per-item governance versions, the method),
    but NOT the changelog (provenance) -- an amendment that changes the law already
    bumps a per-item version, so the law version tracks the law, not the prose log."""
    operative = {k: v for k, v in constitution.items() if k != "changelog"}
    blob = json.dumps(operative, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


@lru_cache(maxsize=1)
def load_constitution() -> dict:
    """The canonical governed constitution, with its constitution_version stamped
    in. Memoized: the le-baseline files do not change while the process runs."""
    constitution = _assemble()
    constitution["constitution_version"] = _version_of(constitution)
    return constitution


def constitution_version() -> str:
    """The governed law version the instrument pins. Changes only when the law
    changes (a ratified amendment)."""
    return load_constitution()["constitution_version"]


if __name__ == "__main__":
    # Self-test: invariants + determinism. No model call, no network, no DB.
    c = load_constitution()
    checks = []

    def check(name: str, ok: bool) -> None:
        checks.append((name, ok))

    tiers = c["tiers"]
    check("5 tiers", len(tiers) == 5)
    check("tier slugs", [t["slug"] for t in tiers] == ["violet", "blue", "green", "orange", "red"])

    tenet_total = sum(len(t["tenets"]) for t in tiers)
    check("58 tenets", tenet_total == 58)

    # every tenet carries text AND governance metadata
    gov_ok = True
    for t in tiers:
        for ten in t["tenets"]:
            if not ten.get("core") or not ten.get("version") or not ten.get("ratified_at") or not ten.get("status"):
                gov_ok = False
    check("every tenet has core + version + ratified_at + status", gov_ok)

    rule_ids = [r["id"] for r in c["rules"]]
    check("R1..R15 present", rule_ids == [f"R{i}" for i in range(1, 16)])
    check("every rule has core + governance", all(r.get("core") and r.get("version") and r.get("status") for r in c["rules"]))

    check("contamination modifier", any(m["id"] == "contamination" for m in c["modifiers"]))
    check("dogma_referenced flag", any(f["id"] == "dogma_referenced" for f in c["flags"]))

    check("method present", bool(c.get("method")))
    check("changelog present", len(c.get("changelog", [])) >= 8)
    check("changelog includes R15 add", any(e.get("target") == "R15" for e in c["changelog"]))

    check("glossary contract", set(c["glossary_contract"]) >= {"the work", "the speaker", "the text", "the audience"})

    # determinism: re-assemble (bypass cache) and re-hash -> identical version
    fresh = _assemble()
    fresh_ver = _version_of(fresh)
    check("version is deterministic", fresh_ver == c["constitution_version"])

    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\nconstitution_version = {c['constitution_version']}  (schema {c['schema_version']}, ratified {c['ratified_at']})")
    print(f"lecg_constitution self-test: {passed}/{len(checks)}")
    if passed != len(checks):
        raise SystemExit(1)
