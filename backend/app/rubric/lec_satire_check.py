"""Static carve-coverage harness for the satire modifier (LEC instrument tooling).

Composes the universal satire modifier (le-baseline/le-satire.json) through the
rc-lyric lens and proves STRUCTURAL coverage against the live fused overlay
(services/agents/rc-lyric-live/rc-lyric-satire.md): every S-tenet, both reading
modes, the run procedure, and all five output fields the live overlay carries
must appear in the composed modifier; the composition must be ASCII-only; the
glossary must fully bind (no neutral placeholders leak); and the lens's own
satire skin example must land. It also checks compose_satire_prompt splices the
modifier between the rubric-definition and the verbatim calibration-format halves
in the right order, and rejects a lens that offers no satire.

The bar is SCORE parity, not byte parity. le-satire is authored FRESH in register
A (domain-neutral, definite-article discipline), exactly like the gospel cores, so
its text differs from the live overlay by design and cannot byte-recombine. This
harness is the cheap pre-flight that the carve dropped nothing; it does NOT call
the model. The DYNAMIC satire score-parity run -- scoring a known satire set
through LEC's satire modifier vs RC's in-process recalibrate_song_satire, on a
live LEC -- is the gated equivalence proof (terminal Anthropic for RC stays
banned; the run goes through a running LEC server). It is NOT executed here.

Run:  cd backend && .venv/Scripts/python.exe -m app.rubric.lec_satire_check
      add 'show' to also print the composed satire modifier.
"""

import re
import sys
from pathlib import Path

from app.rubric.lec_full_prompt import compose_satire_prompt
from app.rubric.lec_lens import (
    Lens, compose_satire, get_lens, load_gospel, load_satire,
)

HERE = Path(__file__).resolve().parent
LIVE_OVERLAY = (
    HERE.parent / "services" / "agents" / "rc-lyric-live" / "rc-lyric-satire.md"
)

# The five required pre-JSON reasoning fields the satire read must emit.
OUTPUT_FIELDS = (
    "LITERAL_SUMMARY", "FLIPPED_SUMMARY_TEST", "MODE_BREAKDOWN",
    "SATIRE_READING", "CEILING_CHECK",
)


def _live_satire_tenet_ids() -> list[str]:
    """The S-tenet ids the live fused overlay carries (### S1. ... ### S8.)."""
    text = LIVE_OVERLAY.read_text(encoding="utf-8")
    return re.findall(r"^### (S\d+)\.", text, flags=re.MULTILINE)


def run_checks():
    gospel = load_gospel()
    satire = load_satire()
    lens = get_lens("rc-lyric")
    composed = compose_satire(satire, lens)
    prompt = compose_satire_prompt(gospel, lens)

    results = []

    def check(name, ok, detail=""):
        results.append((bool(ok), name, detail))

    # --- coverage vs the live fused overlay ---
    live_ids = _live_satire_tenet_ids()
    carved_ids = [t["id"] for t in satire["tenets"]]
    check("tenet count == live overlay", len(carved_ids) == len(live_ids),
          f"{len(carved_ids)} vs {len(live_ids)}")
    for sid in live_ids:
        check(f"tenet {sid} present in composed", f"\n### {sid}. " in composed)

    # --- both reading modes (S8) ---
    check("depiction mode present", "Satirical depiction mode" in composed)
    check("commentary mode present", "Commentary mode" in composed)

    # --- run procedure ---
    check("run procedure heading", "## How to Run a Satire Recalibration" in composed)
    n_steps = len(satire["procedure"]["steps"])
    check("run procedure last step numbered", f"\n{n_steps}. " in composed,
          f"expected {n_steps} steps")

    # --- the five output fields ---
    for fld in OUTPUT_FIELDS:
        check(f"output field {fld}", f"{fld}: [" in composed)

    # --- sections ---
    for section in ("## What Stays the Same", "## What Changes",
                    "## The Satire Tenets", "## Output Format"):
        check(f"section {section!r}", section in composed)

    # --- lens skin landed ---
    check("rc-lyric satire skin example present", "This Is A Raid" in composed)

    # --- hygiene ---
    nonascii = sorted({c for c in composed if ord(c) > 127})
    check("composed is ASCII-only", not nonascii,
          "" if not nonascii else f"found: {nonascii[:8]}")
    check("no em-dash sub '--' in composed", "--" not in composed)
    for placeholder in ("the work", "the speaker", "the text", "the audience"):
        check(f"glossary bound: no '{placeholder}' leftover", placeholder not in composed)
    # The binding actually happened (the domain nouns are present).
    for noun in ("the song", "the narrator", "the lyrics", "the listener"):
        check(f"glossary bound to domain: '{noun}' present", noun in composed)

    # --- compose_satire_prompt: order + brackets + reuse of the verbatim format ---
    check("prompt: standard rubric first",
          prompt.index("## The Five Tiers") < prompt.index("SATIRE RECALIBRATION LENS"))
    check("prompt: modifier before the format half",
          prompt.index("SATIRE RECALIBRATION LENS") < prompt.index("## Required Output"))
    check("prompt: the full modifier is spliced in", "## The Satire Tenets" in prompt)

    # --- rejects a lens with no satire skin ---
    no_satire = Lens(content_type="x-none", label="none", product_framing="")
    try:
        compose_satire_prompt(gospel, no_satire)
        check("rejects a non-satire lens (raises)", False, "did not raise")
    except ValueError:
        check("rejects a non-satire lens (raises)", True)

    return composed, prompt, results


def main() -> int:
    composed, prompt, results = run_checks()

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
    print(f"composed satire modifier : {len(composed):>6} chars")
    print(f"composed satire prompt   : {len(prompt):>6} chars")
    print(f"checks                   : {len(results) - failed}/{len(results)} passed")

    if failed:
        print(f"\nSATIRE CARVE: FAIL ({failed} check(s) failed)")
        return 1
    print("\nSATIRE CARVE: OK (modifier carved; coverage + binding + hygiene hold; "
          "prompt splices rubric -> modifier -> format)")
    print("Next (gated): dynamic satire score-parity run on a live LEC vs RC's "
          "recalibrate_song_satire, pending Chad's satire set + model-cost sign-off.")
    return 0


if __name__ == "__main__":
    if "show" in sys.argv[1:]:
        composed, _, _ = run_checks()
        print(composed)
    else:
        raise SystemExit(main())
