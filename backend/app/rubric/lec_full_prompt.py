"""Full-prompt composer (Decoupling Part 1, next-in-order step 1).

`compose()` in lec_lens emits only the RUBRIC-DEFINITION half of the live system
prompt. The complete prompt the calibrator sends is two halves joined:

    RUBRIC_DEFINITION  (the law: tiers, tenets, dogma, contamination, rules)
  + CALIBRATION_FORMAT (the method: anonymous read, visceral, the seven-route
                        tree, two-axis read, precedent placement + the precedent
                        TABLE, the intensity vernier, contamination/summary
                        checks, verdict, reconciliation, the JSON schema, the
                        charge scale, and the summary-voice rules)

This module joins them so the full prompt can be assembled from gospel + lens.

Per the locked decision, the calibration-format METHOD stays verbatim in
`compass_agent_rubric` (it is NOT re-authored into the gospel like the rubric-
definition half was). This composer reuses that method as the universal skeleton
and PARAMETRIZES the one piece the method already exposes cleanly:

  - the precedent TABLE, sourced via `lens.precedents_key` (the live
    render_precedent_table selector; rc-lyric -> the song corpus).

Because the method text is verbatim and rc-lyric's precedents_key is "lyric",
the calibration-format half this composer emits is BYTE-IDENTICAL to the live
CALIBRATION_FORMAT (main() asserts it). The full prompt therefore differs from
the live lyric prompt ONLY in the rubric-definition half, which is the
established score-parity delta (gospel + lens authored fresh in register A, plus
post-golden law). A different lens with a different precedents_key swaps the
table by construction, which is what proves the seam works for more than lyric.

STILL LENS SKIN, not yet lifted (the next focused sub-step, parity-delicate
because it edits the verbatim method): the music-specific summary-voice lines
(genre labels / production descriptors / profanity censoring / song title --
lens.summary_voice already holds these three; the UNIVERSAL hygiene rules stay
in the method) and the per-route worked examples (the +28 / +55 / +74 / +8 /
-24 / -42 / -45 precedent references and the song framing baked into the seven-
route tree). Templatizing the method to source those from the lens is the work
that makes the format half lens-driven rather than verbatim; tracked for the
pass that precedes the gated dynamic score-parity run.

Scope: this builds the SYSTEM prompt. The per-call user prompt ("Calibrate this
song ...") is built by `build_calibration_prompt` and is already artifact-type
framed; it is out of this composer's scope.

Run:  cd backend && .venv/Scripts/python.exe -m app.rubric.lec_full_prompt
      add 'show' to print the composed full prompt.
"""

from __future__ import annotations

import sys

from app.rubric.lec_lens import Lens, compose, get_lens, load_gospel
from app.services.agents.lec_compass_agent_rubric import (
    CALIBRATION_FORMAT,
    CALIBRATION_FORMAT_POST,
    CALIBRATION_FORMAT_PRE,
    SUMMARY_VOICE_RULES,
)
from app.services.agents.lec_rubric_builder import render_precedent_table

# The domain-specific lines in the method's summary-voice block, matched by a
# stable ASCII substring so the em-dash in the title rule never needs to be
# hardcoded here. Everything else in SUMMARY_VOICE_RULES is universal output
# hygiene and stays in the verbatim method; these three are lens-owned and come
# from lens.summary_voice instead.
MUSIC_SUMMARY_VOICE_MARKERS = (
    "Never use the song title",
    "Profanity censoring:",
    "Never use genre labels",
)


def _render_summary_voice(lens: Lens) -> str:
    """The summary-voice block, lens-sourced for its domain lines. The UNIVERSAL
    output-hygiene rules stay in the method's SUMMARY_VOICE_RULES (reused verbatim
    minus the lens-owned lines); the lens supplies its own domain lines via
    lens.summary_voice. Prose-only: this governs charge_summary wording, not the
    charge, so it does not affect score parity."""
    universal = "\n".join(
        ln for ln in SUMMARY_VOICE_RULES.splitlines()
        if not any(m in ln for m in MUSIC_SUMMARY_VOICE_MARKERS)
    ).rstrip()
    lens_lines = "\n".join(f"- {rule}" for rule in lens.summary_voice)
    return universal + (("\n" + lens_lines) if lens_lines else "") + "\n"


def compose_calibration_format(lens: Lens) -> str:
    """The calibration-format half, lens-driven where it should be:
      - the precedent TABLE via lens.precedents_key,
      - the summary-voice domain lines via lens.summary_voice (universal output
        hygiene stays in the verbatim method).

    The universal method skeleton (anonymous read, visceral, the seven-route tree,
    two-axis, precedent placement, vernier, the checks, JSON schema, charge scale)
    is reused verbatim from compass_agent_rubric. The per-route worked examples
    inside the route tree are still verbatim here; lifting them to the lens is the
    score-affecting sub-step that needs a dynamic re-validation pass, tracked
    separately. For rc-lyric the only difference from the live CALIBRATION_FORMAT
    is the summary-voice block (lens-distilled), which is prose-only."""
    post_without_sv = CALIBRATION_FORMAT_POST.replace(SUMMARY_VOICE_RULES, "")
    return (
        CALIBRATION_FORMAT_PRE
        + render_precedent_table(lens.precedents_key)
        + post_without_sv
        + _render_summary_voice(lens)
    )


def compose_full_prompt(gospel: dict, lens: Lens) -> str:
    """Assemble the complete calibrator system prompt from gospel + lens.

    rubric-definition half (compose, fresh + score-parity) joined to the
    calibration-format half (the verbatim method with the precedent table
    parametrized). The join mirrors build_calibration_prompt's
    `"\\n".join([RUBRIC_DEFINITION, CALIBRATION_FORMAT])` with no few-shot block
    (the v2 path hard-codes examples="")."""
    rubric_def = compose(gospel, lens)
    return rubric_def + "\n" + compose_calibration_format(lens)


def compose_cutover_prompt(gospel: dict, lens: Lens) -> str:
    """The VALIDATED cutover system prompt: the fresh rubric-definition
    (`compose`) joined to the VERBATIM calibration-format method. This is exactly
    arm A from the dynamic score-parity run -- no summary-voice or route lift --
    so it is the version proven equivalent-or-better against the golden (9 songs,
    all five tiers, 2026-06-18). Use THIS for the live cutover.

    `compose_full_prompt` (with the lens-sourced summary-voice, and later the
    route lift) is for the multi-lens future and is NOT yet score-validated; do
    not point the live calibrator at it until those lifts are re-validated."""
    rubric_def = compose(gospel, lens)
    verbatim_format = (
        CALIBRATION_FORMAT_PRE
        + render_precedent_table(lens.precedents_key)
        + CALIBRATION_FORMAT_POST
    )
    return rubric_def + "\n" + verbatim_format


def run_checks():
    gospel = load_gospel()
    lens = get_lens("rc-lyric")

    composed_format = compose_calibration_format(lens)
    composed_full = compose_full_prompt(gospel, lens)

    results = []

    def check(name, ok, detail=""):
        results.append((bool(ok), name, detail))

    # Everything in the calibration-format half EXCEPT the summary-voice block
    # must be byte-identical to the live CALIBRATION_FORMAT: same method skeleton,
    # same verbatim route tree (worked examples not yet lifted), same precedent
    # table (rc-lyric precedents_key == lyric). Strip each side's summary-voice
    # block; the remainders must match exactly.
    composed_no_sv = composed_format.replace(_render_summary_voice(lens), "")
    live_no_sv = CALIBRATION_FORMAT.replace(SUMMARY_VOICE_RULES, "")
    check("format minus summary-voice == live (byte-equal)",
          composed_no_sv == live_no_sv,
          "" if composed_no_sv == live_no_sv
          else f"composed {len(composed_no_sv)} vs live {len(live_no_sv)}")
    # Summary-voice lifted: universal hygiene preserved, lens domain lines present.
    check("summary-voice universal hygiene preserved",
          "Summarize, do not evaluate" in composed_format)
    check("summary-voice lens lines present",
          all(rule in composed_format for rule in lens.summary_voice))
    check("route worked-examples present (verbatim, not yet lifted)",
          "(the +28 precedent)" in composed_format)

    # The full prompt carries both halves end to end.
    for marker in ("## The Five Tiers", "## Rules", "## Required Output",
                   "VISCERAL READ", "ROUTE:", "TWO-AXIS READ",
                   "PRECEDENT PLACEMENT", "INTENSITY VERNIER",
                   "CONTAMINATION CHECK", "## The Charge Scale",
                   "## charge_summary Voice"):
        check(f"full prompt contains {marker!r}", marker in composed_full)

    # R15 (the post-golden reverence-halo rule) rides through into the full
    # prompt via the rubric-definition half.
    check("R15 present in full prompt", "\nR15. " in composed_full)

    return composed_full, results


def main() -> int:
    composed_full, results = run_checks()

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
    print(f"composed full prompt : {len(composed_full):>6} chars")
    print(f"checks               : {len(results) - failed}/{len(results)} passed")

    if failed:
        print(f"\nFULL-PROMPT COMPOSER: FAIL ({failed} check(s) failed)")
        return 1
    print("\nFULL-PROMPT COMPOSER: OK (halves join; everything but summary-voice "
          "byte-equal to live; summary-voice now lens-sourced)")
    print("Next (sub-step): lift the per-route worked examples (the +28 / +55 / "
          "+74 / +8 / -24 / -42 / -45 precedent refs + song framing in the seven-"
          "route tree) into the lens. That is score-affecting (re-author ASCII + "
          "dynamic re-validation), unlike the prose-only summary-voice lift.")
    return 0


if __name__ == "__main__":
    if "show" in sys.argv[1:]:
        composed, _ = run_checks()
        print(composed)
    else:
        raise SystemExit(main())
