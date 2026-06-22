"""The lens contract + registry + composer (Decoupling Part 1, steps 2-3).

This is an LEC INSTRUMENT module. A LENS points the universal instrument at one
kind of work. The gospel (Libra Engine's baseline) holds the domain-neutral law,
its structure, and the reading method:

  le-baseline/le-cores.json     the neutral moral cores (the law text)
  le-baseline/le-scaffold.json  structure + governance (axes, labels, ranges, ids,
                                tenet numbers, rule layers, versioning, changelog)
  le-baseline/le-method.json    the universal read-method kernels (the procedure)

A lens (the first is `rc-lyric`) holds everything domain-specific, keyed to
gospel ids. `compose(gospel, lens)` joins the two into the rubric-definition the
calibrator sends.

Ownership prefixes (Chad, 2026-06-17): le- = Libra Engine baseline/gospel,
lec- = this instrument + its tooling, rc- = the lyric lens (Rising Compass's
application). Python modules carry the lec_ prefix with an underscore so they
stay importable; data files and folders carry le-/lec-/rc- with a hyphen.

Scope of compose(): it mirrors `rubric_builder.build_rubric_definition()` only,
the RUBRIC_DEFINITION half of the live system prompt. The fuller calibration-
format method (anonymous-read preamble, visceral read, the seven-route tree,
two-axis read, precedent placement + the precedent table, the intensity vernier,
the contamination/summary checks, reconciliation, the JSON schema, the charge
scale, and summary-voice) still lives in `compass_agent_rubric.CALIBRATION_FORMAT`
and is NOT decoupled in this step. The full-prompt composer that joins
compose() + that format layer (with `lens.precedents_key` selecting the table and
`lens.summary_voice` merged in) is a later piece; the parity harness
(lec_parity_check) handles the join for scoring.

Design + boundary: `Dropbox/Libra Engine/Libra Engine Compass (LEC)/plans and
docs/LEC-DECOUPLING-PART1-BOUNDARY-MAP.md`. Hub: LIBRA-ENGINE-ALTITUDE-PLAN.md.

Nothing here is wired into the live calibrator. RC still renders from
services/agents/rc-lyric-live/rc-lyric-rubric.json via rubric_builder; this is the parallel,
parity-bound path being built beside it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASELINE_DIR = HERE / "le-baseline"
CORES_PATH = BASELINE_DIR / "le-cores.json"
SCAFFOLD_PATH = BASELINE_DIR / "le-scaffold.json"
METHOD_PATH = BASELINE_DIR / "le-method.json"
SATIRE_PATH = BASELINE_DIR / "le-satire.json"
# The rc-lyric inhabited-voice lens doc. Unlike satire (decoupled into the
# universal le-satire law + a lens skin), inhabited-voice is a single lyric-native
# lens doc spliced as an overlay; it lives with the live lens data, not le-baseline.
INHABITED_PATH = HERE.parent / "services" / "agents" / "rc-lyric-live" / "rc-lyric-inhabited-voice.md"

# Sentinel the gospel rule cores use to defer the worked example to the lens
# (ruling 4: named exemplars are lens-owned). compose() strips it and splices in
# lens.rule_examples at the rule's position.
LENS_EXEMPLAR_SENTINEL = "The lens supplies the worked exemplar."

# Instrument-owned (per le-cores.json flags[].instrument_owned): the dogma_note
# field instruction. The flag's doctrinal TEST is gospel (flag.core); the worked
# fires/does-not-fire contrast is lens (lens.flag_examples); the rendered block
# format + this instruction are the instrument's.
DOGMA_NOTE_INSTRUCTION = (
    "When the flag fires, dogma_note must name which framework "
    "(Christian / Islamic / Karmic / Dharmic / Institutional-<name>) and describe, "
    "in your own words, the moment that triggered it. Do NOT quote or reproduce "
    "the text; paraphrase it. One short sentence."
)


@dataclass(frozen=True)
class Lens:
    """One domain adapter. Everything a product owns about how the universal
    instrument gets pointed at its kind of work, keyed to gospel ids so the
    composer can attach each piece to the tenet, rule, modifier, flag, or method
    section it illustrates.

    A lens NEVER restates the law. It binds vocabulary, supplies examples, adds
    its domain-only rules, and configures the domain guards. The moral cores and
    the reading method stay in the gospel, ratified once.
    """

    # --- Identity -----------------------------------------------------
    content_type: str          # the dispatch key + lens id, e.g. "rc-lyric"
    label: str                 # human label for the domain, e.g. "song lyrics"
    product_framing: str       # domain identity prose (the lyric wording of the old
                               # rubric_builder._PRELUDE opener, minus the universal
                               # read-method kernels, which the gospel owns)

    # --- Vocabulary binding (gospel neutral noun -> domain noun) ------
    # Keys are the gospel glossary_contract placeholders (the work / the speaker /
    # the text / the audience) plus any phrase the lens rebinds (a private 1:1 bond).
    glossary: dict = field(default_factory=dict)

    # --- Lens-owned content, keyed to gospel ids ----------------------
    # tenet_examples: keyed by tenet id, note id (e.g. "violet-note-specifics"), or
    #   tier slug -> list[str]. Lyric uses only the violet note's worked block.
    tenet_examples: dict = field(default_factory=dict)
    # rule_examples: rule id -> the canonical worked case spliced in where the gospel
    #   core left the LENS_EXEMPLAR_SENTINEL (R4 -> Every Breath You Take, etc.).
    rule_examples: dict = field(default_factory=dict)
    # domain_rules: rule id -> the FULL domain rule text for rules that live in the
    #   lens (lyric: R1, R12). The gospel carries only their thin universal sibling;
    #   the composer slots this full text in at the rule's position instead.
    domain_rules: dict = field(default_factory=dict)
    # modifier_examples / flag_examples: id -> list[str] (contamination examples,
    #   dogma fires/does-not-fire worked contrast).
    modifier_examples: dict = field(default_factory=dict)
    flag_examples: dict = field(default_factory=dict)
    # method_examples: method-slot id -> block. A method kernel with
    #   "lens_example_after": "<slot>" gets this block injected after it (lyric:
    #   "topic_ladder" = the love-song ladder).
    method_examples: dict = field(default_factory=dict)
    # flag_render: optional id -> a fully rendered prompt block for a flag. Escape
    #   hatch for parity: when present, compose() emits it verbatim instead of
    #   composing gospel core + lens examples + instruction. Instrument-owned today;
    #   carried on the lens until the instrument owns flag rendering directly.
    flag_render: dict = field(default_factory=dict)

    # --- Corpora + behavior -------------------------------------------
    precedents_key: str = "lyric"      # artifact_type the precedent corpus loads under
                                       # (points at the live per-type corpus selector)
    use_precedents_default: bool = True
    satire_available: bool = False     # whether the lens offers a parallel satire re-read
    satire_skin: dict = field(default_factory=dict)    # the lens's satire SKIN: song-specific
                                       # worked examples keyed by le-satire tenet id (e.g. S8).
                                       # The universal satire law is le-satire (the baseline's);
                                       # this is the only satire content the lens owns. Consumed
                                       # by compose_satire, not compose().
    summary_voice: list = field(default_factory=list)  # domain output-hygiene rules
                                       # (lyric: no genre labels, no production descriptors).
                                       # Consumed by the calibration-format layer, not compose().
    guard_config: dict = field(default_factory=dict)   # copyright/verbatim guard config


# --- Registry / dispatch ----------------------------------------------

LENS_REGISTRY: dict = {}
_LENS_FIELDS = {f.name for f in fields(Lens)}
DEFAULT_LENS = "rc-lyric"


def register_lens(lens: Lens) -> None:
    """Register a lens under its content_type. Re-registering replaces it."""
    LENS_REGISTRY[lens.content_type] = lens


def get_lens(content_type: str, *, fallback: str = DEFAULT_LENS) -> Lens:
    """Resolve the lens for a content type. Loads its bundle on first use, falling
    back to `fallback` (the first authored lens, rc-lyric) for an unknown type,
    mirroring rubric_builder.load_precedents's lyric fallback. Raises if neither
    the requested type nor the fallback can be resolved."""
    for key in (content_type, fallback):
        if key in LENS_REGISTRY:
            return LENS_REGISTRY[key]
        try:
            return load_lens_bundle(key)
        except FileNotFoundError:
            continue
    raise KeyError(
        f"No lens for content_type {content_type!r} and no {fallback!r} fallback bundle"
    )


def load_lens_bundle(content_type: str) -> Lens:
    """Load + register a lens from its data bundle. The bundle lives beside this
    module at <content_type>/<content_type>-bundle.json (e.g.
    rc-lyric/rc-lyric-bundle.json). Bundle keys that are not Lens fields (notes,
    version metadata) are ignored."""
    bundle_path = HERE / content_type / f"{content_type}-bundle.json"
    with open(bundle_path, encoding="utf-8") as f:
        data = json.load(f)
    lens = Lens(**{k: v for k, v in data.items() if k in _LENS_FIELDS})
    register_lens(lens)
    return lens


# --- Gospel loader (cores + scaffold + method, merged by id) ----------

def _load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_gospel() -> dict:
    """Load the Libra Engine baseline and merge its three files into one gospel
    dict the composer reads directly. cores supplies the neutral law text;
    scaffold supplies axis/label/charge_range/tenet numbers/rule layers; method
    supplies the reading procedure."""
    cores = _load_json(CORES_PATH)
    scaffold = _load_json(SCAFFOLD_PATH)
    method = _load_json(METHOD_PATH)

    sc_tiers = {t["slug"]: t for t in scaffold["tiers"]}
    tiers = []
    for ct in cores["tiers"]:
        st = sc_tiers[ct["slug"]]
        st_ten = {x["id"]: x for x in st["tenets"]}
        tiers.append({
            "slug": ct["slug"],
            "axis": st["axis"],
            "label": st["label"],
            "charge_range": st["charge_range"],
            "definition_core": ct["definition_core"],
            "tenets": [
                {"id": x["id"], "number": st_ten[x["id"]]["number"], "core": x["core"]}
                for x in ct["tenets"]
            ],
            "notes": [
                {"id": n["id"], "title_core": n.get("title_core", ""), "core": n["core"]}
                for n in ct.get("notes", [])
            ],
        })

    sc_rules = {r["id"]: r for r in scaffold["rules"]}
    rules = []
    for cr in cores["rules"]:
        sr = sc_rules.get(cr["id"], {})
        rules.append({**cr, "layer": sr.get("layer", cr.get("layer", "baseline"))})

    return {
        "schema_version": cores.get("schema_version"),
        "tiers": tiers,
        "modifiers": cores["modifiers"],
        "flags": cores["flags"],
        "rules": rules,
        "method": method,
    }


def load_satire() -> dict:
    """Load the universal satire modifier (le-baseline/le-satire.json). This is the
    domain-neutral satire LAW (the work / the speaker / the text / the audience);
    compose_satire renders it through a lens. Owned by the baseline (le-), available
    to every lens; the lens supplies only its satire SKIN (lens.satire_skin)."""
    return _load_json(SATIRE_PATH)


_INHABITED_BENCH_START = "\n\nValidation bench (a change to these tenets"
_INHABITED_BENCH_END = "\n\nThe inhabited-voice recalibration exists"


def load_inhabited() -> str:
    """The rc-lyric inhabited-voice lens, prompt-ready: the ratified lens doc with
    the VALIDATION-BENCH block stripped. That block is a regression-test spec
    naming specific songs + their expected tiers, so it must never enter the
    scoring prompt (it would pre-judge those exact songs). Everything else in the
    doc is reading guidance and belongs in the prompt. Lyric-native (no glossary
    binding): inhabited-voice is a lyric-only lens, not a universal le- modifier."""
    raw = INHABITED_PATH.read_text(encoding="utf-8")
    start = raw.find(_INHABITED_BENCH_START)
    end = raw.find(_INHABITED_BENCH_END)
    if start != -1 and end != -1 and end > start:
        raw = raw[:start] + raw[end:]
    return raw.strip() + "\n"


# --- Glossary rendering -----------------------------------------------

def _apply_glossary(text: str, glossary: dict) -> str:
    """Bind the gospel's neutral nouns to the lens's domain nouns. Replaces both
    the lowercase and sentence-initial Capitalized forms. Longest keys first so a
    multi-word phrase binds before any shorter key that is its substring. Kept to
    the safe glossary phrases (the work / the speaker / the text / the audience /
    a private 1:1 bond): bare 'work' is never rebound, so 'internal work' and 'the
    work of exposing' survive intact."""
    if not text:
        return text
    for key in sorted(glossary, key=len, reverse=True):
        val = glossary[key]
        text = text.replace(key, val)
        if key[:1].islower():
            cap_key = key[0].upper() + key[1:]
            cap_val = (val[0].upper() + val[1:]) if val else val
            text = text.replace(cap_key, cap_val)
    return text


def _axis_note(axis: str) -> str:
    if axis in ("harm", "transcendence"):
        return f" [{axis} axis]"
    if axis == "neutral":
        return " [neutral zone of both axes]"
    return ""


# --- Section renderers -------------------------------------------------

def _attach(text: str, extra) -> str:
    """Append a lens example (str or list[str]) to a line as inline prose."""
    if not extra:
        return text
    if isinstance(extra, list):
        extra = " ".join(e.strip() for e in extra if e)
    return (text + " " + extra.strip()).strip()


def _render_method_kernel(kernel: dict, lens: Lens) -> str:
    heading = kernel.get("heading")
    core = _apply_glossary(kernel.get("core", ""), lens.glossary)
    out = f"## {heading}\n\n{core}" if heading else core
    slot = kernel.get("lens_example_after")
    if slot and lens.method_examples.get(slot):
        out += "\n\n" + lens.method_examples[slot].strip()
    return out


def _render_tiers(gospel: dict, lens: Lens) -> str:
    g = lens.glossary
    blocks = []
    for tier in gospel["tiers"]:
        header = (
            f"**{tier['slug']} ({tier['label']}){_axis_note(tier['axis'])}:** "
            f"{_apply_glossary(tier['definition_core'], g)}"
        )
        lines = [header]
        for ten in tier["tenets"]:
            line = f"{ten['number']}. {_apply_glossary(ten['core'], g)}"
            line = _attach(line, lens.tenet_examples.get(ten["id"]))
            lines.append(line)
        block = "\n".join(lines)
        for note in tier["notes"]:
            title = _apply_glossary(note.get("title_core", ""), g)
            body = _apply_glossary(note["core"], g)
            note_block = f"**{title}** {body}" if title else body
            note_block = _attach(note_block, lens.tenet_examples.get(note["id"]))
            block += "\n\n" + note_block
        block = _attach(block, lens.tenet_examples.get(tier["slug"]))
        blocks.append(block)
    return "\n\n".join(blocks)


def _render_dogma(gospel: dict, lens: Lens) -> str:
    flag = next((f for f in gospel["flags"] if f["id"] == "dogma_referenced"), None)
    if not flag:
        return ""
    if lens.flag_render.get("dogma_referenced"):
        return lens.flag_render["dogma_referenced"].strip()
    parts = [
        "## Dogma Reference (parallel tag, does NOT affect the score)",
        "",
        _apply_glossary(flag["core"], lens.glossary),
    ]
    examples = lens.flag_examples.get("dogma_referenced")
    if examples:
        parts += ["", "Worked contrast:"]
        parts += [f"- {e}" for e in examples]
    parts += ["", DOGMA_NOTE_INSTRUCTION]
    return "\n".join(parts)


def _render_contamination(gospel: dict, lens: Lens) -> str:
    mod = next((m for m in gospel["modifiers"] if m["id"] == "contamination"), None)
    if not mod:
        return ""
    parts = ["## Contamination (modifier)", "", _apply_glossary(mod["core"], lens.glossary)]
    examples = lens.modifier_examples.get("contamination")
    if examples:
        parts += ["", "Examples of contamination:"]
        parts += [f"- {e}" for e in examples]
    return "\n".join(parts)


def _render_rules(gospel: dict, lens: Lens) -> str:
    parts = ["## Rules", ""]
    for i, rule in enumerate(gospel["rules"]):
        if i > 0:
            parts.append("")
        rid = rule["id"]
        if lens.domain_rules.get(rid):
            # lens carries the full operative rule; gospel has only the thin sibling
            text = lens.domain_rules[rid].strip()
        else:
            text = _apply_glossary(rule["core"], lens.glossary).strip()
            example = lens.rule_examples.get(rid)
            if LENS_EXEMPLAR_SENTINEL in text:
                text = text.replace(LENS_EXEMPLAR_SENTINEL, "").strip()
            text = _attach(text, example)
        parts.append(f"{rid}. {text}")
    return "\n".join(parts)


# --- The composer ------------------------------------------------------

def compose(gospel: dict, lens: Lens) -> str:
    """Assemble the rubric-definition string from the gospel + a lens bundle.

    Mirrors `rubric_builder.build_rubric_definition()` so the lyric lens can be
    held to SCORE parity against lec-golden-2026-06-17. Assembly order:

      1. lens.product_framing (the domain identity opener), then the gospel
         reading-method kernels (sequential accumulation, read-the-work-not-the-
         author, read-the-text-not-the-medium, zero-external-knowledge, the
         five-tier header) rendered through lens.glossary.
      2. Tiers: each gospel tier's definition core + tenet cores via the glossary,
         with the scaffold's axis/label in the header and lens.tenet_examples
         attached by tenet/note/tier id.
      3. The gospel calibration-method kernels (whole-work, topics-not-tiers,
         start-at-zero, the topic-neutral closer), with lens.method_examples
         (the love-song ladder) injected after the start-at-zero kernel.
      4. Dogma flag: instrument header + gospel core (glossary) +
         lens.flag_examples worked contrast + the instrument dogma_note instruction
         (or lens.flag_render verbatim when supplied).
      5. Contamination modifier: gospel core (glossary) + lens.modifier_examples.
      6. Rules: gospel rule cores via the glossary with lens.rule_examples spliced
         in at the deferred-exemplar sentinel, and lens.domain_rules (R1, R12)
         substituting their thin universal siblings.

    The precedent table, the route tree, and the rest of the calibration-format
    method are NOT emitted here (see module docstring); the full-prompt composer
    joins them downstream.
    """
    blocks: list = []

    if lens.product_framing:
        blocks.append(lens.product_framing.strip())

    method = gospel.get("method", {})
    for kernel in method.get("reading_method", []):
        blocks.append(_render_method_kernel(kernel, lens))

    blocks.append(_render_tiers(gospel, lens))

    for kernel in method.get("calibration_method", []):
        blocks.append(_render_method_kernel(kernel, lens))

    blocks.append(_render_dogma(gospel, lens))
    blocks.append(_render_contamination(gospel, lens))
    blocks.append(_render_rules(gospel, lens))

    return "\n\n".join(b for b in blocks if b).strip() + "\n"


# --- The satire composer (the universal modifier, lens-bound) ---------

SATIRE_TITLE = "# Satire Modifier (parallel reading lens)"


def compose_satire(satire: dict, lens: Lens) -> str:
    """Render the universal satire modifier (le-satire) through a lens.

    Mirrors compose() but for the satire OVERLAY: bind the gospel-neutral nouns
    via lens.glossary and splice the lens's own satire SKIN examples
    (lens.satire_skin["examples"], keyed by le-satire tenet id) in after the tenet
    they illustrate. The satire LAW (S1-S8, the depiction/commentary modes, the
    ceiling rule, the run procedure, the five output fields) is the baseline's; the
    lens owns only the worked examples, exactly like the rubric-definition carve.

    The output-field schema (LITERAL_SUMMARY / FLIPPED_SUMMARY_TEST /
    MODE_BREAKDOWN / SATIRE_READING / CEILING_CHECK) is emitted here, so the
    calibration-format half downstream needs no satire-specific edit.

    Callers gate on lens.satire_available before composing (compose_satire_prompt
    raises); this function renders unconditionally so the parity harness can render
    any lens that authors a skin.
    """
    g = lens.glossary
    skin = (lens.satire_skin or {}).get("examples", {})

    def gl(text: str) -> str:
        return _apply_glossary(text, g)

    parts: list = [SATIRE_TITLE, "", gl(satire["intro"]), "", gl(satire["rationale"])]

    stays = satire["stays_the_same"]
    parts += ["", f"## {stays['heading']}", ""]
    parts += [f"- {gl(p)}" for p in stays["points"]]

    changes = satire["what_changes"]
    parts += ["", f"## {changes['heading']}", "", gl(changes["body"])]

    parts += ["", f"## {satire['tenets_heading']}"]
    for tenet in satire["tenets"]:
        parts += ["", f"### {tenet['id']}. {gl(tenet['title'])}", "", gl(tenet["core"])]
        # The lens's worked example is its OWN domain text (song-specific); it is
        # attached raw, not glossary-rendered, matching how compose() attaches
        # lens.rule_examples.
        example = skin.get(tenet["id"])
        if example:
            parts += ["", example.strip()]

    proc = satire["procedure"]
    parts += ["", f"## {proc['heading']}", ""]
    for i, step in enumerate(proc["steps"], 1):
        parts.append(f"{i}. {gl(step)}")

    out = satire["output"]
    parts += [
        "", f"## {out['heading']}", "", gl(out["intro"]), "",
        "Required additional reasoning fields (output BEFORE the JSON, in this order):",
        "", "```",
    ]
    for fld in out["fields"]:
        parts.append(f"{fld['name']}: [{gl(fld['instruction'])}]")
    parts += ["```", "", gl(out["closing"])]

    return "\n".join(parts).strip() + "\n"
