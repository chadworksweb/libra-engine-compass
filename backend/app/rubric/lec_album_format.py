"""The ALBUM calibration-format half: the v3 procedure for a whole release.

The song method (`lec_compass_agent_rubric.CALIBRATION_FORMAT`) is reused
verbatim by every lens whose procedure differs from the song's only in
vocabulary. The album's differs in KIND, so it gets its own skeleton, selected by
`lens.method_key == "album"`. The song method stays byte-identical, which keeps
lyric score-parity untouched.

Three structural departures from the song method, each deliberate:

1. NO PRECEDENT PLACEMENT. Chad's ruling 2026-08-12: the scores are on the songs,
   the songs are approved, and a release composes over approved data rather than
   placing itself against a corpus. The song method's placement step and its
   precedent table are absent here, and the center is built from the track rows
   instead.
2. THE VERNIER RE-ANCHORS. In the song method every vernier component is judged
   "relative to the precedent you placed against." With no precedent, the track
   rows supply the center and the vernier measures what the RECORD's own
   structure does to it: consistency across the tracklist, the closing track's
   landing, and the reach and register of the body of work. These are the facts
   the per-track charges cannot express.
3. NO SEVEN-ROUTE TREE. The routes classify a narrator's relationship to a text.
   Every track on the release already ran that classification and carries its
   result. Re-running it at release scale would re-litigate settled work (lens
   rule A5). The album's structural question is coherence, which A3 supplies.

Everything else holds the song method's shape and order, because the order IS the
procedure: anonymous read, visceral, dominant arc, start at zero, the two-axis
read, the checks, verdict, reconciliation, JSON, charge scale.
"""

from __future__ import annotations

ALBUM_CALIBRATION_FORMAT_PRE = """
## Required Output

Before any reasoning, perform the anonymous read.

ANONYMOUS READ: Whatever you know about the artist, the release, its reception, its sales, its place in a catalog, or any discourse around it, set it to zero. You are reading a set of approved song rows and nothing else. If at any point in the reasoning you catch yourself reaching for something that is not in those rows, name it explicitly and discard it.

You have no lyrics and you do not need them. Every track was read from its lyrics by this same instrument and the result is in front of you, finished and approved. Your evidence is those rows.

Then write your reasoning in this exact structure. The order IS the procedure: intuition first, then the structural facts, then deliberation, then reconciliation against the intuition. Never reorder or skip a step.

VISCERAL READ: Your immediate first-impression placement of the RELEASE on the -100..+100 charge scale, recorded BEFORE any analysis. One line, in these exact words: "Visceral: [signed integer]" -- you may append at most five words naming the register (e.g. "Visceral: +40. Witness, then retreat."). NO justification, no hedging, no analysis. This is the gut verdict; the deliberation below either confirms it or must account for leaving it (see RECONCILIATION).

DOMINANT ARC: [Read the song rows top to bottom IN RUNNING ORDER. In 2-3 sentences, state what this release is fundamentally about: its overall message, its movement across the tracklist, and where it ends up. This is the album's identity. Everything below must be evaluated against it.]

STARTING POSITION: Decent (0)

You do NOT have the release's aggregate charge and you must not compute one. An average of the track charges is not the release's charge and never was: it discards the governing axis, it cannot see the running order, and it averages a degraded track into invisibility. Start at zero and build the case from the rows.

EVIDENCE RULES: Cite tracks by POSITION and by what their approved readings say ("the third position carries...", "the closing track's reading names..."). Never quote a song row's prose verbatim; paraphrase what it found. Never reproduce the proper name of any real public figure that appears in a row; replace it with a bracketed descriptor. Naming track titles in the reasoning is fine; the summary is where titles are forbidden.

COHERENCE CHECK: Lens rule A3, and it comes first because the two checks below both depend on it. State whether the release argues one thing across its tracks or collects works that do not answer each other, and say what the argument is if there is one. State it in these exact words: "Coherence: [coherent|anthology]" followed by one sentence of ground.

TWO-AXIS READ: Score BOTH axes, every release. Moral content is two-dimensional, harm and ego-service on one axis and transcendence and internal work on the other, and a release can score on both at once. One scale cannot hold both; the server composes the public charge. Your job is the two honest reads.

HARM AXIS: How much ego-service, objectification, contempt, substance celebration, or destruction the running order carries, drawn from what the track readings already found; cite the tracks by position. Then settle pervasiveness under lens rule A2, which is REQUIRED and is counted in TRACKS, not passages: none (no harm content anywhere in the running order), discrete (one track or a short run, riding an album that genuinely stays higher -- strike those tracks and a coherent higher album remains), or pervasive (the harm content recurs across the tracklist, or the tracks carrying it are the album's spine). A PERVASIVE payload governs the charge no matter what the transcendence axis shows, and the release is NOT contaminated because it calibrates at the payload's own level. A DISCRETE artifact is the contamination case. Never average a degraded track away. State in these exact words: "Harm: [0 or negative integer, 0 to -100]. Pervasiveness: [none|discrete|pervasive]."

TRANSCENDENCE AXIS: How much internal work, collective witness, encouragement, surrender, or universal address the running order carries, drawn from what the track readings already found; cite the tracks by position. Read it under the release-scale caps: closing stance (A1), the raised bar that load-bearing doctrine imposes (R14), inherited sanctity the album did not earn (R15), and the demand that vocabulary deliver rather than merely invoke (R3). Tier vocabulary maps onto the value: an Elevated-strength read sits +25..+74, Ascended +75 and above. State in these exact words: "Transcendence: [0 or positive integer, 0 to +100]."

CLOSING-STANCE CHECK: Lens rule A1. Read the FINAL position's approved reading as the album's own last word and state what it leaves the listener in. A body that names a condition and refuses it, closing on a track that relands inside that same condition, caps below Ascended and may cap lower. A body that works through hardship or witness and closes on affirmation, refusal, or resolve earns what that closing delivers. On an anthology the final position is the last item rather than a thesis, and this check softens accordingly. State the outcome in one line.
"""

ALBUM_CALIBRATION_FORMAT_POST = """
CENTER: Build the release's placement from the track rows under the governing axis. The governing axis is the dominant arc's axis; a pervasive harm payload governs regardless of the transcendence claim. This is a case built from the rows, the way a song's case is built from its passages: name which positions carry the read, which dilute it, and where the weight actually sits. It is NOT an average, and a center that merely recites the arithmetic mean of the track charges has skipped the work. State the result in these exact words: "Center: [signed integer]".

INTENSITY VERNIER: Rate the four components below, each -2..+2, each RELATIVE to the center the track rows produced, each POLE-AGNOSTIC: positive means the album's own structure pushes markedly MORE intense than that center, negative markedly LESS, regardless of which direction the axis runs (the server applies the governing axis's sign). These four are where the facts the per-track charges cannot express get their weight. One line per component with a reason of ten words or fewer.
- Saturation: how consistently the governing read fires across the tracklist, as against concentrating in a few positions.
- Resolution: how decisively the closing track lands the album (the A1 finding, valued).
- Register: new-language or redefining across the body of work, as against rhetorical, repetitive, or derivative.
- Reach: intimate and personal, as against universal and collective, across the running order.
Mixed signs are MANDATORY: if every nonzero component leans the same direction, you skipped the relative judgment -- re-judge each component independently. All-zero is allowed and means the album sits exactly where its rows put it. You NEVER name the final charge; the server composes it from your center and these components.

CONTAMINATION CHECK: Run this every time, as its own step, AFTER the two-axis read and INDEPENDENT of the center. Contamination is a binary flag, never a function of the charge. Your HARM AXIS read already settled discrete-vs-pervasive: a PERVASIVE payload governs the charge (the release calibrates at the payload's level and is NOT contaminated), while a DISCRETE harm artifact on a read the harm axis does not govern IS the contamination case. Only reads landing in violet/blue/green territory can be contaminated. Apply lens rule A4: settle the flag against the tracks whose own approved readings already carry a contamination finding, never against a bare count, and name what contaminates THE RECORD in your own words rather than concatenating the per-track notes. State the outcome on this line every time, in these exact words: "Contamination: none" or "Contamination: <artifact>".

DOGMA CHECK: Run the flag at release scale. A release can carry a doctrinal arc that no single track carries alone, and several tracks each carrying an allusion do not add up to a doctrinal release unless the album's dominant arc IS the doctrine. When it fires, R14's raised bar applies to the release and dogma_note must name the framework and describe the arc in your own words. State: "Dogma: none" or "Dogma: <framework>".

SUMMARY CHECK: Run this every time, right before the VERDICT. Draft the charge_summary and verify it is PURE POSITIVE DESCRIPTION of what the release IS and what its tracks actually do: subject, stance, movement, the moves across the running order. State ONLY what is present. NEVER say what the release does NOT do, lacks, fails at, or falls short of, and NEVER judge whether it works, earns its claim, or goes deep enough (that reasoning lives in the sections above, never in the summary). If your draft contains an absence clause, a contrast-with-what-it-lacks, or a verdict word, REWRITE it as positive description before emitting the JSON. State the outcome on this line: "Summary check: clean" once it holds.

VERDICT: State the governing read in tier vocabulary and say what the running order does to earn it -- "[Decent/Elevated/Ascended/Degraded/Corrupted] territory" -- because [1-sentence reason based on the DOMINANT ARC and the closing stance, not on one outlying track]. Do NOT name a final number anywhere in the verdict; the server composes it.

RECONCILIATION: Compare your Center against your VISCERAL READ. If they differ by more than 25 points, name exactly what deliberation found that the gut missed: the specific structural fact, the closing-stance finding, the pervasiveness call, or the coherence finding that justifies leaving the first impression. If you cannot name a concrete finding, the gut was right and you reasoned yourself out of the obvious read: go back and re-place the center. State one of, in these exact words: "Reconciliation: aligned" or "Reconciliation: [what deliberation found]".

THEN, output the JSON object on a new line starting with {

JSON fields:
{
    "visceral_charge": signed integer from your VISCERAL READ line,
    "coherence": "coherent|anthology",
    "harm": {"value": integer 0 to -100, "pervasive": true only if Pervasiveness was pervasive, else false},
    "transcendence": {"value": integer 0 to 100},
    "center": signed integer from your Center line,
    "vernier": {"sat": -2..2, "res": -2..2, "reg": -2..2, "reach": -2..2},
    "contaminated": true/false,
    "contamination_note": "A brief description, IN YOUR OWN WORDS, of what contaminates the release: the specific track content, move, or stance that does it, and why the rest of the album stays higher. Not a restatement of charge_summary, and not a concatenation of the per-track notes. Null if not contaminated.",
    "dogma_referenced": true|false,
    "dogma_note": "Which framework (Christian/Islamic/Karmic/Dharmic/Institutional-<name>) and a brief note IN YOUR OWN WORDS describing how it carries the release's dominant arc. Null if not referenced.",
    "charge_summary": "What the release IS: its subject and its stance, taken whole. 1 sentence preferred, 2 max.",
    "arc_prose": "How the release moves across its running order. Write it as a CONTINUOUS ACCOUNT of an album in motion, the way a serious critic narrates the shape of a work: what it sets up, where it turns, what it answers, where it arrives. NEVER walk the tracklist in order announcing each stop. Enumerating positions ('the second position does X, the third does Y, the two that follow do Z') is a LIST, not an arc, and it is the failure mode of this field: it reports sequence while saying nothing about movement. Name the album's turns instead, especially where it contradicts, answers, or undercuts itself, and let the order be implied by the telling. Track titles stay out. CRITICAL, do not drift into what a music review actually reviews: you have not heard this album and never will. Sound, production, performance, delivery, arrangement and vocal are all outside what you can see. You are narrating the movement of what the readings SAY. Borrow the critic's narrative command, never the critic's subject. Keep the clinical register throughout; the prohibition is on the list cadence, not on precision. If the readings hold one register from end to end, say the album stays put and say what it stays put on, rather than inventing a journey. EXACTLY TWO paragraphs separated by one blank line, each 2 to 3 tight sentences, under 130 words total. The first establishes what the release sets up and the first real turn it takes; the second carries that through to where it finally lands.",
    "listener_effects_prose": "What taking in the WHOLE release does to a listener, compiled from the per-track listener readings: the dominant pulls a person absorbs across the running order and what repeat listening reinforces. EXACTLY TWO paragraphs separated by one blank line, each 2 to 3 tight sentences, under 130 words total. The first names what the release installs; the second names what repeated exposure produces.",
    "societal_effects_prose": "What happens when many people take this whole release in, compiled from the per-track societal readings. Speak to possibility, not prophecy. EXACTLY TWO paragraphs separated by one blank line, each 2 to 3 tight sentences, under 150 words total. The first names the pattern at scale; the second names the symptoms it produces.",
    "deadpan_line": "A FLAT museum-placard naming of the WHOLE release, about as long as the artist and title together. Naming, not commenting: no verdict, no terminal period, no leading article. Descriptive adjectives are allowed, evaluative ones are not. It names the album's content, never the artist.",
    "topics": [0 to 3 taxonomy slugs, most-dominant-first by share of the release's content],
    "topic_audit": null when topics is non-empty; otherwise {"reason", "proposed_tag", "rationale"},
    "psyche_facts": {"purpose", "indicated_for" (exactly four short noun phrases), "do_not_use_if", "directions", "onset", "duration", "warning"},
    "effects_pl": [1 to 4 slugs from the closed per-listen vocabulary, naming what one pass through the whole release does],
    "confidence": 0.0-1.0
}

Compose psyche_facts and effects_pl from the release's OWN finished reading above (its tier, center, summary, arc, topics, deadpan, and both prose lanes), never from the track rows directly. They are the prescription for taking in the whole album, in the register of a drug-facts panel.

You never emit a tier and never emit a final charge. The server composes the charge from center + vernier under the governing axis and derives the tier from it.

REMEMBER: If your reasoning above does not cite specific track positions moving an axis off zero, that axis IS zero and the center sits in Decent territory. Do not override your own analysis, and do not let the arithmetic of the track charges stand in for it.

## The Charge Scale

The charge is a war-to-peace axis: -100 = all-out war (with self or others), +100 = all-out peace (with self or community, local or universal). Every release falls somewhere on that spectrum. The tier vocabulary maps onto it: Ascended (violet) +75 to +100, Elevated (blue) +25 to +74, Decent (green) -24 to +24, Degraded (orange) -25 to -74, Corrupted (red) -75 to -100. The final number is composed by the server; your center and vernier are the inputs.

## confidence

confidence reflects how firmly the release reads, which at album scale is mostly a question of the rows you were given:
- 0.9+ = every track carries a full approved reading and the album's shape is unambiguous
- 0.7-0.9 = the readings are complete and the album's shape is clear enough to place
- 0.5-0.7 = some rows are thin, or the running order does not resolve into a clear shape
- below 0.5 = tracks are missing readings, or too few tracks carry one to speak for the release

"""
