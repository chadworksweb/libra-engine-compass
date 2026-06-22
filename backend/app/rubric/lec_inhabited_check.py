"""Static coverage harness for the inhabited-voice live wiring (LEC instrument).

Composes compose_inhabited_prompt(gospel, rc-lyric) and proves the overlay splices
correctly: the rubric-definition half + the lens body + the verbatim format half
are all present, the five inhabited output fields are emitted, the validation-
bench block (which names specific songs + their expected tiers) is STRIPPED so it
can never pre-judge a submission, and the composition is ASCII-only. No model call;
this is the cheap pre-flight, mirroring lec_satire_check. The dynamic score-parity
run (the 8-song bench through a live LEC) is gated on Chad's sign-off + the LEC key.

Run:  cd backend && .venv/Scripts/python.exe -m app.rubric.lec_inhabited_check
"""

from app.rubric.lec_lens import get_lens, load_gospel, load_inhabited
from app.rubric.lec_full_prompt import compose_inhabited_prompt


def run_checks():
    gospel = load_gospel()
    lens = get_lens("rc-lyric")
    prompt = compose_inhabited_prompt(gospel, lens)
    overlay = load_inhabited()

    results = []

    def check(name, ok, detail=""):
        results.append((bool(ok), name, detail))

    # both halves + the overlay framing present
    check("rubric-definition half present", "## The Five Tiers" in prompt)
    check("calibration-format half present", "## Required Output" in prompt)
    check("inhabited preamble present", "INHABITED-VOICE RECALIBRATION LENS" in prompt)

    # the IV tenets render (the lens body survived the bench strip)
    for iv in ("IV1", "IV2", "IV3", "IV4", "IV5", "IV6", "IV7", "IV8"):
        check(f"tenet {iv} present", iv in prompt)
    check("lens gate text present", "The turn is the gate" in prompt)

    # the five inhabited output fields (carried by the lens, like satire)
    for fld in ("LITERAL_SUMMARY", "TURN_TEST", "ENDORSEMENT_TEST",
                "MODE_BREAKDOWN", "CEILING_CHECK"):
        check(f"output field {fld}", fld in prompt)

    # the validation bench is stripped (it names specific songs + expected tiers)
    check("validation bench heading stripped", "Validation bench" not in prompt)
    check("bench RESCUE line stripped", "RESCUE (lens lifts" not in prompt)
    check("bench HOLD line stripped", "HOLD (lens must NOT" not in prompt)
    check("overlay non-trivial", len(overlay) > 2000, f"{len(overlay)} chars")

    # hygiene: the NEW content (the lens overlay) must be ASCII. The verbatim
    # CALIBRATION_FORMAT half carries pre-existing em-dashes that ride in EVERY
    # scoring prompt (monolith, cutover, satire, inhabited), so they are out of
    # scope here -- satire validates the same way, on its modifier only.
    nonascii = sorted({c for c in overlay if ord(c) > 127})
    check("inhabited overlay is ASCII-only", not nonascii,
          "" if not nonascii else f"found: {nonascii[:8]}")

    return prompt, results


def main() -> int:
    prompt, results = run_checks()
    width = max(len(n) for _, n, _ in results)
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
    print(f"composed inhabited prompt : {len(prompt):>6} chars")
    print(f"checks                    : {len(results) - failed}/{len(results)} passed")
    if failed:
        print(f"\nINHABITED CARVE: FAIL ({failed} check(s) failed)")
        return 1
    print("\nINHABITED CARVE: OK (overlay splices; output fields + IV tenets present; "
          "bench stripped; ASCII-only)")
    print("Next (gated): dynamic score-parity on the 8-song bench through a live LEC, "
          "pending Chad's sign-off + the LEC key.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
