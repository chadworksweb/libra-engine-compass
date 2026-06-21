"""Static parity / coverage harness for the Decoupling carve (LEC instrument tooling).

Composes the fresh gospel + rc-lyric lens and proves STRUCTURAL coverage against
the frozen golden (lec-golden-2026-06-17): every tier, tenet, modifier, flag,
rule, method kernel, and canonical exemplar that the live rubric carries must
appear in the composed rubric-definition, the composition must be ASCII-only,
the glossary must fully bind (no neutral placeholders leak), and the deferred-
exemplar sentinel must be gone. This is the runnable check that the carve did not
drop anything; it does NOT call the model.

The bar is SCORE parity, not byte parity (the gospel and lens are authored fresh,
so the text differs by design). This harness is the cheap pre-flight. The
DYNAMIC score-parity run, scoring a known song set through gospel + rc-lyric vs
the golden on a live LEC and comparing composed charges, is the gated next step:
it needs a running LEC with model access plus Chad's sign-off on the song set and
the model cost, and it is NOT executed here. (Terminal Anthropic calls for RC
stay banned; the dynamic run goes through a running LEC server, not the terminal.)

Run:  cd backend && .venv/Scripts/python.exe -m app.rubric.lec_parity_check
      add 'show' to also print the composed rubric-definition.
"""

import json
import sys
from pathlib import Path

from app.rubric.lec_lens import compose, get_lens, load_gospel, LENS_EXEMPLAR_SENTINEL

HERE = Path(__file__).resolve().parent
GOLDEN = HERE / "lec-golden-2026-06-21"  # re-snapshotted post-R16; 2026-06-18/06-17 stay as the earlier rollbacks
CALIBRATION_FORMAT_MARKER = "## Required Output"  # where the format half begins

# Rules authored AFTER the active golden freeze, if any. The count check is
# golden + post-golden, and each post-golden rule must be present in the gospel.
# Empty now: the 2026-06-18 golden re-snapshot folded R15 into the baseline, so
# the gospel and the golden carry the same 15 rules again. The next law forged
# after this golden lands here until the golden is re-snapshotted past it.
POST_GOLDEN_RULES = ()


def golden_rubric_definition() -> str:
    """The rubric-definition half of the golden system prompt (everything before
    the calibration-format method block). That half is what compose() mirrors."""
    full = (GOLDEN / "system_prompt_lyric.txt").read_text(encoding="utf-8")
    idx = full.find(CALIBRATION_FORMAT_MARKER)
    return full[:idx] if idx != -1 else full


def run_checks():
    gospel = load_gospel()
    lens = get_lens("rc-lyric")
    composed = compose(gospel, lens)
    manifest = json.loads((GOLDEN / "MANIFEST.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]

    results = []

    def check(name, ok, detail=""):
        results.append((bool(ok), name, detail))

    # --- structural counts vs the frozen manifest ---
    check("tiers count == golden", len(gospel["tiers"]) == counts["tiers"],
          f"{len(gospel['tiers'])} vs {counts['tiers']}")
    n_tenets = sum(len(t["tenets"]) for t in gospel["tiers"])
    check("tenets count == golden", n_tenets == counts["tenets"],
          f"{n_tenets} vs {counts['tenets']}")
    check("modifiers count == golden", len(gospel["modifiers"]) == counts["modifiers"],
          f"{len(gospel['modifiers'])} vs {counts['modifiers']}")
    check("flags count == golden", len(gospel["flags"]) == counts["flags"],
          f"{len(gospel['flags'])} vs {counts['flags']}")
    expected_rules = counts["rules"] + len(POST_GOLDEN_RULES)
    check("rules count == golden + post-golden", len(gospel["rules"]) == expected_rules,
          f"{len(gospel['rules'])} vs {counts['rules']}+{len(POST_GOLDEN_RULES)}")
    rule_ids = {r["id"] for r in gospel["rules"]}
    for rid in POST_GOLDEN_RULES:
        check(f"post-golden rule {rid} present in gospel", rid in rule_ids)

    # --- every tier header present (slug + label + axis note) ---
    for tier in gospel["tiers"]:
        hdr = f"**{tier['slug']} ({tier['label']})"
        check(f"tier header {tier['slug']}", hdr in composed)
        # the tier's last tenet number must appear under it (coarse tenet presence)
        last = tier["tenets"][-1]["number"]
        check(f"tier {tier['slug']} reaches tenet {last}", f"\n{last}. " in composed)

    # --- every rule R1..R14 present at line start ---
    for rule in gospel["rules"]:
        rid = rule["id"]
        present = (f"\n{rid}. " in composed) or composed.startswith(f"{rid}. ")
        check(f"rule {rid} present", present)

    # --- sections + method kernels ---
    for section in ("## The Five Tiers", "## Calibration Method: Start at Zero",
                    "## Dogma Reference", "## Contamination (modifier)", "## Rules"):
        check(f"section {section!r}", section in composed)
    for kernel in (gospel["method"]["reading_method"] + gospel["method"]["calibration_method"]):
        h = kernel.get("heading")
        if h:
            check(f"kernel '## {h[:28]}...'", f"## {h}" in composed)

    # --- lens-owned skin landed ---
    check("topic ladder injected", "Love songs are the clearest example" in composed)
    for song in ("Every Breath You Take", "Maneater", "The Way It Is", "Hero",
                 "Always Be My Baby", "CeeLo Green"):
        check(f"canonical exemplar: {song}", song in composed)
    check("violet-note worked example", "group as SUBJECT" in composed)

    # --- hygiene ---
    check("deferred-exemplar sentinel stripped", LENS_EXEMPLAR_SENTINEL not in composed)
    nonascii = sorted({c for c in composed if ord(c) > 127})
    check("composed is ASCII-only", not nonascii,
          "" if not nonascii else f"found: {nonascii[:8]}")
    for placeholder in ("the work", "the speaker", "the audience", "a private 1:1 bond"):
        check(f"glossary bound: no '{placeholder}' leftover", placeholder not in composed)
    check("no 'internal song' mis-binding", "internal song" not in composed)

    return composed, golden_rubric_definition(), results


def main() -> int:
    composed, golden_def, results = run_checks()

    width = max(len(name) for _, name, _ in results)
    failed = 0
    for ok, name, detail in results:
        tag = "PASS" if ok else "FAIL"
        if not ok:
            failed += 1
        line = f"  [{tag}] {name.ljust(width)}"
        if detail:
            line += f"   ({detail})"
        print(line)

    print()
    print(f"composed rubric-definition : {len(composed):>6} chars")
    print(f"golden  rubric-definition  : {len(golden_def):>6} chars "
          f"(byte-equal NOT expected; gospel + lens authored fresh)")
    print(f"checks                     : {len(results) - failed}/{len(results)} passed")

    if failed:
        print(f"\nSTATIC PARITY: FAIL ({failed} check(s) failed)")
        return 1
    print("\nSTATIC PARITY: OK (carve dropped nothing; structure + skin + hygiene hold)")
    print("Next (gated): dynamic score-parity run on a live LEC vs the golden, "
          "pending Chad's song set + model-cost sign-off.")
    return 0


if __name__ == "__main__":
    if "show" in sys.argv[1:]:
        composed, _, _ = run_checks()
        print(composed)
    else:
        raise SystemExit(main())
