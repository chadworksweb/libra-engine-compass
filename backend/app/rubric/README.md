# app/rubric -- Decoupling Part 1 (baseline / lens carve)

The Decoupling tears the rubric into a universal **baseline** (Libra Engine's)
and a domain **lens** (each product's). The first lens is the **lyric** lens
(content type = lyrics; the thing RC consumes). "Lyric" is the content type, not
"music": the lens reads the text on the page, not the medium around it.
Design + classification + open decisions:
`Dropbox/Libra Engine/Libra Engine Compass (LEC)/plans and docs/LEC-DECOUPLING-PART1-BOUNDARY-MAP.md`.
Hub: `Libra Engine - Entity/LIBRA-ENGINE-ALTITUDE-PLAN.md`.

## Ownership prefixes (Chad, 2026-06-17)

Ownership is structural in the names. `le-` = Libra Engine baseline/gospel
(universal LAW: cores, scaffold, rules), `lec-` = the instrument (the composer +
its tooling), `lecg-` = the governance venue, `<lens>-` = domain lenses
(`rc-lyric` = the lyric lens / Rising Compass's application, `cc-essay`, `lt-`).
Data files and folders use the hyphen form; Python modules use `lec_` with an
underscore so they stay importable. The frozen golden snapshot's INTERNAL files keep their verbatim live
names (it is a faithful freeze of what RC runs), only its directory is prefixed.

## Layout

    lec_lens.py              the Lens contract + registry + compose() (the composer)
    lec_carve.py             lossless split of services/agents/tenets/rc-lyric-rubric.json
    lec_parity_check.py      static coverage harness: compose() vs the golden
    lec_snapshot_golden.py   freezes today's live calibrator as the golden reference

    le-baseline/
      le-cores.json          HAND-AUTHORED: domain-neutral moral cores (the gospel law)
      le-scaffold.json       GENERATED: structure + governance (axes, labels, ranges,
                             ids, tenet numbers, rule layers, versioning, changelog)
      le-method.json         HAND-AUTHORED: universal read-method kernels (the procedure)
      le-satire.json         universal le- satire modifier (shipped as gospel law)

    rc-lyric/                the lyric lens
      rc-lyric-bundle.json   HAND-AUTHORED: the lyric lens (the contract, filled fresh)
      rc-lyric-text.json     GENERATED: the exact lyric strings (reference only)

    cc-essay/                the second lens (essay), a real domain lens

    lec-golden-<date>/       IMMUTABLE reference data: frozen live system prompt +
                             tenet files + manifest (internal files keep verbatim
                             names; the parity baseline). Multiple snapshots kept.

## The two layers, and how parity is held

**The gospel = three LE files.** `le-cores.json` is the neutral law text (the
public ratifies it once); `le-scaffold.json` is the structure/governance carved
out of the live `rc-lyric-rubric.json`; `le-method.json` is the universal reading procedure.
`lec_lens.load_gospel()` merges the three into one gospel dict by id.

**The lens = one RC file.** `rc-lyric-bundle.json` carries everything
domain-specific keyed to gospel ids: the product identity opener, the
work/speaker/text/audience glossary, the topic ladder, the violet-note worked
example, per-rule canonical exemplars (R4/R5/R10/R11/R13), the full operative
text for the lyric-only rules (R1, R12), the contamination + dogma worked
examples, the music-bound summary-voice rules, and the verbatim-guard config.

**compose(gospel, lens)** (`lec_lens.py`) joins them into the rubric-definition,
mirroring `lec_rubric_builder.build_rubric_definition()`. It renders the law through
the lens glossary, attaches the lens skin by id, substitutes the lens's full R1/R12
for their thin gospel siblings, and splices each rule's canonical exemplar in
where the gospel core left the deferred-exemplar sentinel. It emits ONLY the
rubric-definition half; the calibration-format method (route tree, two-axis read,
precedent table, vernier, checks, JSON schema, summary-voice) still lives in
`lec_compass_agent_rubric.CALIBRATION_FORMAT` and is joined downstream.

**Two parity bars.**

1. *Carve parity (RC is untouched).* `lec_carve.py` losslessly splits the live
   `rc-lyric-rubric.json` into `le-scaffold.json` + `rc-lyric-text.json`; recombining them
   reproduces `rc-lyric-rubric.json` exactly. Because RC still renders from the live
   `rc-lyric-rubric.json`, its prompt is unchanged.

       cd backend && .venv/Scripts/python.exe -m app.rubric.lec_carve
       # -> PARITY OK: recombine(scaffold, lyric_text) == rc-lyric-rubric.json (deep-equal)

2. *Score parity (the fresh path matches the old one).* The gospel and the lyric
   lens are authored FRESH, so compose() will NOT be byte-identical to the
   golden. The bar is SCORE parity. `lec_parity_check.py` is the cheap static
   pre-flight: it proves the composition drops nothing (every tier, tenet,
   modifier, flag, rule, kernel, exemplar present), is ASCII-only, binds the
   glossary fully, and strips the sentinel.

       cd backend && .venv/Scripts/python.exe -m app.rubric.lec_parity_check
       # add 'show' to print the composed rubric-definition
       # -> STATIC PARITY: OK (57/57)

   The DYNAMIC score-parity run (scoring a known song set through gospel +
   rc-lyric vs the golden on a live LEC and comparing composed charges) is the
   gated next step: it needs a running LEC with model access and Chad's sign-off
   on the song set + model cost. Terminal Anthropic calls for RC stay banned; the
   dynamic run goes through the LEC server, not the terminal.

## Status (Part 1 COMPLETE + LIVE)

The baseline/lens carve is complete and the lyric cutover is LIVE. The composer
composes gospel + lens; satire shipped as a universal `le-` modifier
(`le-baseline/le-satire.json`); `cc-essay` is a real second lens
(`rc-lyric/` and `cc-essay/` both present). The live rubric module dir is
`backend/app/services/agents/rc-lyric-live/` (renamed from `agents/tenets/`).
Golden snapshots `lec-golden-*` are kept as reference data.

- Carve mechanism: DONE, parity-proven (5 tiers, 58 tenets, 1 modifier, 1 flag,
  14 rules).
- Gospel (le-cores.json + le-scaffold.json + le-method.json): COMPLETE. All five
  tiers + 58 tenets, the contamination modifier, the dogma flag, and every rule
  in register A; the universal read-method kernels de-musked into le-method.json.
  R1/R12 carry only their thin universal sibling in the gospel; their full
  case-bound text lives in the lyric lens. Satire lives in `le-satire.json` as a
  universal modifier.
- Composer (lec_lens.compose): DONE. Contract + registry + load_gospel +
  load_lens_bundle + compose, all rendering through the glossary.
- Lyric lens (rc-lyric-bundle.json): AUTHORED FRESH against the contract; the
  lyric cutover is LIVE (the live module is `services/agents/rc-lyric-live/`).
- Second lens (`cc-essay/`): a real second lens, present alongside `rc-lyric/`.
- Static parity harness (lec_parity_check): DONE, 57/57.
