"""Rubric definition + calibration prompt builder for the Compass.

Coupling cut for LEC: the Song-backed `build_few_shot_examples` and the RC
narrative/editorial prompt builders were removed -- LEC is the stateless scoring
half and never reads the Library. The few-shot draw was already dead in the v2
path (calibrate_song_async hard-codes examples=""); the rubric + curated
precedent table carry the anchoring. What remains is the rubric text + the
calibration prompt builder.
"""

from app.lec_constants import ARTIFACT_TYPE_LABELS
from app.services.agents.lec_rubric_builder import render_precedent_table


# ============================== QUARANTINED ==============================
# THIS IS THE PRE-RETUNE BAN-WALL. It is still LIVE in the composed prompt for
# every song and album summary, and it should not be treated as the standard.
#
# The 2026-07-09 editorial voice retune (RC-VOICE-RETUNE-STANDARD.md, now
# archived) named THREE surfaces in scope: the two server prose prompts AND
# "the terminal-supplied prose (charge_summary, editorial, album synthesis)".
# Its stated rationale, verbatim: "the old prompts were long negative 'never'
# lists. Research and practice both say that fails: a negative instruction is a
# soft constraint against a hard training prior, so banning one phrase just
# pushes the model to the next high-probability construction." The replacement
# was to be a short POSITIVE spec + gold exemplars carried in the prompt + a
# code-side validator.
#
# That retune shipped on 2026-07-09/10 (RC d99511d, 870b3c3) and rewrote
# listener_effects_prose.py and societal_effects_prose.py, which RC owns. This
# constant had already moved to LEC on 2026-06-19 (9fbef41, a RENAME pass), and
# RC was stripped of rubric code on 2026-06-21. So the retune stopped at the
# Decoupling boundary and never reached the surface it explicitly scoped.
#
# The content below has NEVER been edited -- the only commit touching it is that
# rename. It is 12 bullets and ~22 prohibitions with ZERO exemplars and no named
# register, which is not the shape the retune settled on.
#
# WHAT THIS IS NOT EVIDENCE OF (corrected 2026-08-14). This block was first
# flagged while diagnosing a weak album summary, with the claim that the missing
# retune caused it. That claim is WRONG and the corpus disproves it: releases
# 1349 and 1351 were read under exactly this block and both produced summaries
# Chad accepts, 1351's being the current bar. A stale spec and a weak output
# were correlated in one instance and I attributed cause. The drift below is
# real and worth recording; it is not a standing explanation for bad prose, and
# it should not be cited as one.
#
# Left in place deliberately. Replacing it is an editorial call (the original
# retune ran as a line-by-line rejection loop with Chad) and there is now no
# evidence it is urgent. Sibling in the same state: rising-compass
# backend/app/services/album_synthesis.py :: ALBUM_VOICE.
#
# NOTE: this block renders into the METHOD half only, which is NOT hashed into
# rubric_version -- so it can be replaced without moving the version consumers
# pin against.
# =========================================================================
SUMMARY_VOICE_RULES = """
## charge_summary Voice

The charge_summary is a short description of the song. Just summarize what the song says, plainly. It is NOT analysis, NOT a verdict, NOT a judgment of whether the song succeeds, deserves its tier, rings true, or earns its claim. The reasoning sections above (DOMINANT ARC, ROUTE, TWO-AXIS READ, PRECEDENT PLACEMENT, tier defense) never appear in the summary. The summary is for a reader who just wants to know what the song is about.

- Direct statement. No hedging, no "could be interpreted as"
- Never use: "Normalizes", "Activates", "Models", "Wrapped in", "Framed as", "Baked in", "In today's [anything]"
- Never start with "This song is about..."
- Never use the song title — the reader already sees it
- Never use passive voice
- Be specific. Name the thing. "Contempt anthem" > "profanity"
- If the song operates on two mechanisms, name both
- 1 sentence preferred, 2 max
- Summarize, do not evaluate. Describe the song's subject, stance, and what the lyrics actually say. Never include a verdict on whether the song works, earns its claim, succeeds at its aim, or rings true. Reasoning leaks: any "but earnest," "but unearned," "but shallow," "but effective," "but hollow," "but contrived," "but trite," "but flat," "but cliched" clause is tier-defense bleeding into the summary — strip it. The SAME leak introduced by a different connective is also forbidden: "though [it] ...", "even as ...", "while [it] ...", "yet ...", or a standalone judgment word ("genuine", "earned", "unearned", "pat", "glib", "thin", "sincere", "slogan", "mantra") used to assess the song. Verdicts live in the reasoning sections, never here.
- Pure positive description. State what the song IS, never what it isn't and never what it falls short of. Forbidden constructions in summaries: "but never...", "without [X]", "rather than [X]", "instead of [X]", "more than [X]", "zero [X]", "doesn't [X]", "never explores/examines/moves/develops/processes", "fails to [X]". When tempted to add an absence clause or a "X rather than Y" contrast, replace it with another concrete detail about what the song actually does on the page — name the imagery, the stance, the move, the relational frame, the specific emotional content. Absence framing and contrast-with-what-it-lacks belong in tier-defense reasoning, not the public summary. If any part of a sentence is about what is missing, what it stops short of, or how it measures up, rewrite the whole sentence as positive description.
- Profanity censoring: f**k, s**t, c**t, b***h (first + last letter, asterisks). Ass/damn/hell uncensored.
- Never use genre labels (rockabilly, R&B, disco, punk, etc.), production descriptors, or any word that requires knowing how the song sounds. Describe what the lyrics SAY, not what the music IS.
"""

CALIBRATION_FORMAT_PRE = """## Required Output

Before any reasoning, perform the anonymous read.

ANONYMOUS READ: Whatever you know about the artist — their reputation, prior catalog, public persona, fan discourse, critical reception, awards, cultural positioning, genre branding — set it to zero before reading the lyrics. The Compass reads the page, not the persona. Proceed below as if the lyrics were submitted by an unknown writer with no public profile. If at any point in the reasoning you catch yourself reaching for context that isn't on the page, name it explicitly and discard it.

Then write your reasoning in this exact structure. The order IS the procedure: intuition first, then classification, then deliberation, then reconciliation against the intuition. Never reorder or skip a step.

VISCERAL READ: Your immediate first-impression placement on the -100..+100 charge scale, recorded BEFORE any analysis. One line, in these exact words: "Visceral: [signed integer]" -- you may append at most five words naming the register (e.g. "Visceral: -60. Contempt, instantly."). NO justification, no hedging, no analysis. This is the gut verdict; the deliberation below either confirms it or must account for leaving it (see RECONCILIATION).

DOMINANT ARC: [Read the full lyrics top to bottom. In 1-2 sentences, state what this song is fundamentally about — its overall message, arc, and emotional direction. This is the song's identity. Everything below must be evaluated against this arc.]

STARTING POSITION: Decent (0)

CITATION RULES: When you quote lyrics in the sections below, never reproduce the proper name of any real public figure (celebrity, athlete, politician, historical figure, brand) that appears in the lyrics. Replace each name with a bracketed descriptor like [public figure], [celebrity], [politician], [athlete], or [brand name]. The shape of the lyric (it lists named people, it invokes a celebrity) is the analytically useful fact, not the specific name. This protects the response from copyright filters that flag name-reproduction. Quote everything else verbatim as instructed. Apply the same redaction to slurs and to ethnic, racial, or religious epithets: never reproduce them verbatim -- refer to them abstractly (e.g. "an ethnic slur," "a racial epithet"), and note whose position they are voiced from. The analytically useful fact is that a slur appears and from what stance (victim-witness vs. deployed contempt -- see the CONTAMINATION CHECK and R5(d)), not the slur itself. This keeps readings of protest, hip-hop, and reclamation songs from tripping copyright and content filters.

ROUTE: Classify the song's governing read into exactly ONE of the seven routes below, and state it in these exact words: "Route: [slug]". Each route carries ONLY its own checks and caps; applying another route's cap is a calibration error (an encouragement song capped for failing a transformation test it was never subject to is a misroute, not a strict reading). If two routes seem live, the route of the DOMINANT ARC governs -- and a pervasive harmful payload ALWAYS routes negative_payload, no matter how sympathetic the surface frame.

- internal_work — the case for height rests on the narrator's own self-examination, accountability, processing, letting-go, vulnerability, or empathy (the Elevated internal-work tenets). REQUIRED CHECK, TRANSFORMATION: cite the specific lyrics where the narrator's posture, understanding, or state at the END of the song is materially different from the BEGINNING. Quote the opening posture, then the closing posture, then name the shift. The shift must be in the narrator. Run all three sub-tests. Inward subjunctive test: closing-state lyrics that rely on first-person wish/conditional constructions ("I wish I could," "I'd be," "if I could just," "someday I'll," "I would") name what the narrator WOULD do, not what they do. Outward wish test: closing-state lyrics that rely on imperatives addressed to others ("stay gone," "come back," "be different"), interrogative requests ("won't you," "can you"), or conditional preconditions ("if you'd just," "when you finally") are wishes directed outward — what the narrator wants from someone else is not a change in the narrator. A wish to another person is still a wish. Aesthetic-markers test: an argument for transformation resting on vivid imagery, dignified resignation, idealized memory, collective vocabulary, or any stylistic register of growth without a cited concrete change in the narrator's posture or behavior has mistaken vividness for movement. When at least TWO of the three sub-tests fail, the transcendence read is capped at the Decent band; a single failed sub-test is a flag that weighs against elevation, not a cap by itself.
- collective_stance — protest, advocacy, calls for justice/rights/equality, or systemic critique delivered as a stance toward the world. Transformation is NOT the relevant axis: the route measures the narrator's stance, not the narrator's change. Caps that DO apply: subject-vs-lens (violet-note-specifics) — a specific identifiable group as the SUBJECT/destination of the demand caps the transcendence read to Elevated (at or below +74, the +55 precedent); a group as a WINDOW onto a universal can clear to Ascended. Closing-stance (R10) — a body that names and refuses injustice but a CLOSING that relands in the very condition it critiqued caps at high Elevated (the +74 precedent). OWNERSHIP CHECK: state the systemic condition the song names and the narrator's stance toward it (critique, refusal, witness, or ownership/belonging/identity-claim). If the hook or chorus lands on "this is us / this is ours / this is home" applied to the named dysfunction, Ascended tenets 4 and 5 do NOT activate, and every down-signal previously excused as "honest confession" must be re-read as endorsement — re-route to static_portrait or negative_payload as the evidence directs.
- encouragement — R11: second-person address delivering substantive affirmation of the listener's inner dignity, strength, capacity, courage, or worth; narrator as messenger or witness to the listener's truth. The route measures what the song DELIVERS to the listener; narrator transformation is never required. Concrete, specific affirmation (the +28 precedent) earns the read; vague platitude stays in the Decent band.
- witness_critique — R5(c)/(d): the narrator names harm without enacting or endorsing it. Witness can earn Elevated on the strength of the witness alone, without narrator transformation. R5(d): a slur or epithet voiced from the victim/witness position is testimony, not deployed contempt.
- doctrinal — R14: load-bearing dogma RAISES the Ascended bar; doctrinal submission is not transcendence. Run the dogma_referenced flag together with the read. Sincere, doctrinally positioned devotion with no universal surrender and no internal movement sits low-positive Decent (the +8 precedent).
- static_portrait — a vivid self-portrait that refuses motion. Honesty about a pattern is not redemptive when the song refuses movement: a vividly honest static self-portrait sits near neutral (-5 to +5); a static unprocessed wallow with no malice and no identity-ratification can sink to the Decent floor (the -24 precedent) but no lower. THE LINE: when the stasis is ratified as identity — the hook frames the dysfunction as home, design, kingdom, or "this is who I am" — the song has crossed to the harm axis (the -42 precedent's territory); naming the wound and calling it home is endorsement, not honesty.
- negative_payload — the dominant arc IS the harmful content: ego-service, flex/materialism, objectification, substance celebration, contempt, violence, destruction. R8's cumulative principle governs: a lower-tier payload that RECURS across the song — especially carried by the repeated hook, refrain, or chorus — is the DOMINANT ARC, not an outlier, not atmosphere, not scenery. A sympathetic surface frame (heartbreak, love, party-fun) does not demote a payload that pervades the song; decode coded sex/substance language to its real weight. Weigh co-occurring DIFFERENT down-signals (substance-as-coping AND a sexual tally AND an emotionally-numb close) by their CUMULATIVE force, never one-at-a-time-removable (the -45 precedent).

TWO-AXIS READ: Score BOTH axes, every song, after the route is set. Moral content is two-dimensional — harm/ego-service is one axis, transcendence/internal-work the other — and a song can score on both at once. One scale cannot hold both; the server composes the public charge. Your job is the two honest reads.

HARM AXIS: How much ego-service, objectification, contempt, substance celebration, or destruction is on the page — the Degraded/Corrupted (orange/red) tenets; cite them by number with the lyric evidence. Then settle pervasiveness, which is REQUIRED: none (no harm content), discrete (a line or short passage sitting on an arc that genuinely stays higher — removal test: if you deleted the offending lines, a coherent higher song would remain), or pervasive (the payload recurs or is hook-carried — if removal would gut the song, or the offending content IS the hook, it is pervasive). A PERVASIVE payload governs the charge no matter what the transcendence axis shows; there is no keep-the-nice-tier-and-flag-the-payload move. State in these exact words: "Harm: [0 or negative integer, 0 to -100]. Pervasiveness: [none|discrete|pervasive]."

TRANSCENDENCE AXIS: How much internal work, collective witness, encouragement, surrender, or universal address is on the page — the Elevated/Ascended (blue/violet) tenets; cite them by number with the lyric evidence — read under YOUR route's caps (subject-vs-lens, closing-stance, dogma-raised bar, transformation outcome). Tier vocabulary maps onto the value: an Elevated-strength read sits +25..+74, Ascended +75 and above; a route cap "to Elevated" means the value cannot exceed +74. State in these exact words: "Transcendence: [0 or positive integer, 0 to +100]."

PRECEDENT PLACEMENT: Place the GOVERNING read relative to the precedent table below. The governing axis is the dominant arc's axis; a pervasive harm payload governs regardless of the transcendence claim. A song is NEVER "equal to" a precedent: judge whether it reads stronger or weaker than an entry, or sits between two entries, and say why ("sits between -42 and -65, closer to -42 because the dysfunction is self-directed..."). The center may be a round number — the vernier sets the fine position. State the results in these exact words: "Precedents: [the entry ids you placed against]" and "Center: [signed integer]". These are calibration references only: they never override the anonymous read, and you must NOT infer any song's identity from them.

"""

CALIBRATION_FORMAT_POST = """

The extremes (+95 to +100 redefinition-level, -98 to -100 comprehensive annihilation) are intentionally left without an entry. Reserve them for songs that clearly exceed every entry above.

INTENSITY VERNIER: Rate the four components below, each -2..+2, each RELATIVE to the precedent(s) you placed against, each POLE-AGNOSTIC: positive means markedly MORE intense than the placed precedent, negative markedly LESS intense, regardless of which direction the axis runs (the server applies the governing axis's sign). One line per component with a reason of ten words or fewer.
- Saturation: how fully the governing-axis tenets fire across the song (sparse vs saturated).
- Resolution: closing-posture strength — how decisively the read completes and is earned vs gestured.
- Register: new-language/redefining vs rhetorical/repetitive/derivative.
- Reach: intimate/personal vs universal/collective, within the placement.
Mixed signs are MANDATORY: if every nonzero component leans the same direction, you skipped the relative judgment — re-judge each component independently. All-zero is allowed and means the song sits exactly on the placement. You NEVER name the final charge; the server composes it from your center and these components.

CONTAMINATION CHECK: Run this every time, as its own step, AFTER the two-axis read and INDEPENDENT of the placement. Contamination is a binary flag, never a function of the charge. Your HARM AXIS read already settled discrete-vs-pervasive: a PERVASIVE payload governs the charge (the song calibrates at the payload's level and is NOT contaminated), while a DISCRETE harm artifact on a read the harm axis does not govern IS the contamination case. The server cross-derives the flag from your axis data; this check is your own statement of the same fact, and a mismatch is recorded. Only reads landing in violet/blue/green territory can be contaminated (red/orange already calibrate as harmful). Scan explicitly for any discrete line or passage that meets a Degraded or Corrupted tenet: substance promotion, sexual or other objectification, an ego/flex/materialism payload, casual cruelty or contempt, a tossed-off betrayal or infidelity. Apply R5(d): a slur or epithet voiced from the victim/witness position does NOT set contaminated -- only a slur the narrator deploys as contempt against a target does. State the outcome on this line every time, in these exact words: "Contamination: none" or "Contamination: <artifact>". Never omit this step, even when the verdict is obvious.

SUMMARY CHECK: Run this every time, right before the VERDICT. Draft the charge_summary and verify it is PURE POSITIVE DESCRIPTION of what the song IS and what its lyrics actually do -- subject, stance, relational frame, imagery, the moves on the page. State ONLY what is present. The summary is not a verdict and not analysis: NEVER say what the song does NOT do, lacks, fails at, avoids, "reaches for" or "gestures at," and NEVER judge whether it works, earns its claim, goes deep enough, or rings true (that reasoning lives in the sections above, never in the summary). Forbidden in the summary: "doesn't / does not," "without [X]," "no real [X]," "never explores/examines/moves/develops/processes," "fails to," "reaches for," "gestures at ... but," "lacks," "falls short," and any "but [shallow/unearned/hollow/effective/contrived]" clause. If your draft contains any of these, REWRITE it as positive description before emitting the JSON. State the outcome on this line: "Summary check: clean" once it holds.

VERDICT: State the governing read in tier vocabulary and placement language — "[Decent/Elevated/Ascended/Degraded/Corrupted] territory, [stronger than / weaker than / between] [precedent id(s)]" — because [1-sentence reason based on the DOMINANT ARC, not outlier lines]. Do NOT name a final number anywhere in the verdict; the server composes it.

RECONCILIATION: Compare your Center against your VISCERAL READ. If they differ by more than 25 points, name exactly what deliberation found that the gut missed — the specific lyric evidence, route fact, or satire/witness/era correction that justifies leaving the first impression. On satire, witness-voice, and era-convention songs this clause is satisfied legitimately. If you cannot name a concrete finding, the gut was right and you reasoned yourself out of the obvious read: go back and re-place the center. State one of, in these exact words: "Reconciliation: aligned" or "Reconciliation: [what deliberation found]".

THEN, output the JSON object on a new line starting with {

JSON fields:
{
    "visceral_charge": signed integer from your VISCERAL READ line,
    "route": "internal_work|collective_stance|encouragement|witness_critique|doctrinal|static_portrait|negative_payload",
    "harm": {"value": integer 0 to -100, "pervasive": true only if Pervasiveness was pervasive, else false},
    "transcendence": {"value": integer 0 to 100},
    "precedent_refs": ["the entry ids from your Precedents line, e.g. \\"-42\\", \\"-65\\""],
    "center": signed integer from your Center line,
    "vernier": {"sat": -2..2, "res": -2..2, "reg": -2..2, "reach": -2..2},
    "contaminated": true/false,
    "contamination_note": "A brief description, IN YOUR OWN WORDS, of what contaminates the song -- the specific move, image, or stance that does it. NEVER quote or reproduce the lyrics: no quotation marks, no copied runs of words from the song. Paraphrase the contaminating content, do not transcribe it. Not a restatement of charge_summary. Null if not contaminated.",
    "dogma_referenced": true|false,
    "dogma_note": "Which framework (Christian/Islamic/Karmic/Dharmic/Institutional-<name>) and a brief note IN YOUR OWN WORDS describing how the framework shows up. NEVER quote or reproduce the lyrics: no quotation marks, no copied runs of words. Paraphrase the moment, do not transcribe it. Null if not referenced.",
    "charge_summary": "One-line summary of what the song IS — its subject and emotional core. Never mention contamination, undermining, or anything negative about the song here. That belongs in contamination_note only.",
IMPORTANT: Never use the word "contaminated" or "contamination" in charge_summary. Contamination is tracked separately via its own field and icon.
    "confidence": 0.0-1.0
}

You never emit a tier and never emit a final charge. The server composes the charge from center + vernier under the governing axis and derives the tier from it.

REMEMBER: If your reasoning above does not cite specific lyrics moving an axis off zero, that axis IS zero and the center sits in Decent territory. Do not override your own analysis.

## The Charge Scale

The charge is a war-to-peace axis: -100 = all-out war (with self or others), +100 = all-out peace (with self or community, local or universal). Every song falls somewhere on that spectrum. The tier vocabulary for your reasoning maps onto it: Ascended (violet) +75 to +100, Elevated (blue) +25 to +74, Decent (green) -24 to +24, Degraded (orange) -25 to -74, Corrupted (red) -75 to -100. A route cap "to Elevated" means the read cannot exceed +74. The final number is composed by the server; your center and vernier are the inputs.

## confidence

confidence should reflect how well you know the song:
- 0.9+ = you know the lyrics and can calibrate with high certainty
- 0.7-0.9 = you know the song well enough to calibrate accurately
- 0.5-0.7 = you have general knowledge but are less certain
- below 0.5 = you're guessing based on limited knowledge
""" + SUMMARY_VOICE_RULES


# Reassembled byte-for-byte for the lyric path (PRE + lyric precedents + POST).
# build_calibration_prompt rebuilds with a type's own corpus for non-lyric
# artifacts (which falls back to the lyric table until that corpus is authored).
CALIBRATION_FORMAT = CALIBRATION_FORMAT_PRE + render_precedent_table() + CALIBRATION_FORMAT_POST


def build_calibration_prompt(
    song_title: str,
    song_artist: str,
    lyrics: str | None = None,
    examples: str | None = None,
    artifact_type: str = "lyric",
) -> tuple[str, str]:
    """Build system and user prompts for calibration.

    `artifact_type`: "lyric" is RC's own path and is byte-for-byte unchanged. The
    other types (poem/essay/script/message/email/article) reuse the SAME rubric +
    precedent discipline but the user prompt frames the read as that artifact
    rather than a song. Per-type precedent corpora are a separate workstream;
    until they land the lyric precedent table (baked into CALIBRATION_FORMAT)
    anchors every type.

    Returns (system_prompt, user_prompt).
    """
    # The monolith RUBRIC_DEFINITION is retired (cutover complete 2026-06-27). The
    # system prompt is composed fresh from the gospel + the artifact's lens for
    # EVERY type: lyric -> rc-lyric; other types fall back to the rc-lyric lens
    # (precedents_key "lyric") until their own lens is authored, matching the old
    # lyric-table fallback. compose_cutover_prompt is the score-parity-validated
    # join (rubric-definition + verbatim calibration-format). Lazy import keeps the
    # agents <- rubric dependency off module load (no cycle with lec_full_prompt).
    # A composition error propagates: the calibrator turns it into an explicit
    # needs-human-review result (fail-loud), never a silent monolith fallback.
    from app.rubric.lec_full_prompt import compose_cutover_prompt
    from app.rubric.lec_lens import get_lens_for_artifact, load_gospel
    # get_lens_for_artifact, NOT get_lens: a type with its own declared lens
    # (album -> rc-album) resolves fail-loud, because get_lens's fallback would
    # hand an album the SONG lens without saying so. Unlisted types behave
    # exactly as before.
    system_prompt = compose_cutover_prompt(load_gospel(), get_lens_for_artifact(artifact_type))
    # `examples` is retained for signature compat but unused: few-shot is disabled
    # (the calibrator always passes "") and the composed prompt carries no slot.

    # The no-text case never reaches the model: calibrate_song_async
    # short-circuits to the null calibration before building a prompt.
    if artifact_type == "lyric":
        user_parts = [f'Calibrate this song: "{song_title}" by {song_artist}']
        if lyrics:
            user_parts.append(f"\nLyrics:\n{lyrics}")
    elif artifact_type == "album":
        # The album's "text" is not prose to interpret -- it is the release's own
        # approved song rows in running order, which the lens reads as the work.
        # Saying so here keeps the frame honest; the running order is
        # load-bearing, so the rows arrive in sequence and are read in sequence.
        title_part = f': "{song_title}"' if song_title else ""
        by_part = f" by {song_artist}" if song_artist else ""
        user_parts = [
            f"Calibrate this release{title_part}{by_part}, taken as one whole work."
        ]
        if lyrics:
            user_parts.append(
                "\nIts song rows, in running order:\n" + lyrics)
    else:
        label = ARTIFACT_TYPE_LABELS.get(artifact_type, "text")
        title_part = f' titled "{song_title}"' if song_title else ""
        user_parts = [
            f"Calibrate this {label}{title_part}. Read it on its own terms as a "
            f"{label}, not as a song lyric."
        ]
        if lyrics:
            user_parts.append(f"\n{label.capitalize()}:\n{lyrics}")
    user_prompt = "\n".join(user_parts)

    return system_prompt, user_prompt
