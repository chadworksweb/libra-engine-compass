"""Legacy monolith rubric assembler (RETIRED from the live path 2026-06-27).

Historically this module assembled RUBRIC_DEFINITION at import from the monolith
rc-lyric-live/rc-lyric-rubric.json. Since the Decoupling cutover the live scorer
composes the gospel (le-baseline) + rc-lyric lens instead (see app.rubric.lec_lens
/ lec_full_prompt), so the monolith is no longer the instrument and the file is
kept off-prod as a backup.

What remains in use on the live path: `render_precedent_table` (reads the precedent
JSON, which stays on prod). `build_rubric_definition` / `load_tenets` survive for
offline tooling only and require the backup rc-lyric-rubric.json to be present;
they raise (fail-loud) if it is absent. Nothing here is built at import anymore.
"""

import json
import logging
from pathlib import Path

TENETS_PATH = Path(__file__).parent / "rc-lyric-live" / "rc-lyric-rubric.json"
PRECEDENTS_PATH = Path(__file__).parent / "rc-lyric-live" / "rc-lyric-precedents.json"
# Per-type benchmark corpora (one file per non-lyric artifact type, e.g.
# rc-lyric-precedents/poem.json). `lyric` uses the canonical PRECEDENTS_PATH above.
PRECEDENTS_DIR = Path(__file__).parent / "rc-lyric-live" / "rc-lyric-precedents"

logger = logging.getLogger(__name__)


def load_tenets() -> dict:
    """Load the canonical tenets JSON."""
    with open(TENETS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_precedents(artifact_type: str = "lyric") -> dict:
    """Load the v3 precedent table for an artifact type. `lyric` (the default)
    uses the canonical song precedents. Other types use precedents/<type>.json
    when it exists; until a type's corpus is authored it falls back to the lyric
    table (logged)."""
    if artifact_type and artifact_type != "lyric":
        type_path = PRECEDENTS_DIR / f"{artifact_type}.json"
        if type_path.exists():
            with open(type_path, encoding="utf-8") as f:
                data = json.load(f)
            if data.get("entries"):
                return data
            logger.info("Precedent corpus for type '%s' is empty; using lyric precedents", artifact_type)
        else:
            logger.info("No precedent corpus for type '%s' yet; using lyric precedents", artifact_type)
    with open(PRECEDENTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def render_precedent_table(artifact_type: str = "lyric") -> str:
    """Render the precedent table for PRECEDENT PLACEMENT: every entry as
    `id (tier): signature`, sorted by charge descending. The relative-placement
    framing (never equal to an entry; always stronger/weaker/between) lives in
    the CALIBRATION_FORMAT step that consumes this table. `artifact_type` selects
    the corpus (lyric default; per-type otherwise)."""
    data = load_precedents(artifact_type)
    entries = sorted(data["entries"], key=lambda e: e["charge"], reverse=True)
    lines = []
    for e in entries:
        lines.append(f"  - {e['id']} ({e['tier']}): {e['signature']}")
    return "\n".join(lines)


_PRELUDE = """You are a lyric calibration agent for The Rising Compass — a cultural diagnostic tool that reads the energetic charge of popular music by assessing the messages contained in the lyrics of the world's most listened to songs.

## How to Read Lyrics

```
# You are a sequential accumulator, not a bag-of-words scanner.
# WRONG: scan all tokens → pattern-match lines against tier definitions → calibrate
# RIGHT: read line by line → compound meaning → calibrate the accumulated result

meaning = ""
for line in lyrics:
    # Each line's meaning is a function of itself PLUS everything before it.
    # "you belong to me" after 6 lines of tender reassurance = devotion.
    # "you belong to me" after 6 lines of threats = possession.
    # The same tokens mean different things depending on accumulated context.
    meaning += interpret(line, context=meaning)

# The input to calibrate is the COMPOUNDED meaning, not the raw lyrics.
# What does this song MOSTLY say? What is the dominant arc?
calibrate(meaning)  # NOT calibrate(lyrics)
```

Do not scan lyrics for keywords. Do not match isolated lines against tier definitions. Read the song the way a human reads a poem — from top to bottom, where each line reshapes everything that came before it. After reading the full song, identify the dominant arc. That is what you calibrate.

## The Core Rule: Songs, Not Artists

We calibrate SONGS, never artists. The same artist can have an Ascended song and a Corrupted song. Each work stands on its own. Do not let an artist's reputation, catalog, or public persona influence the calibration of an individual song. Analyzes the song's lyrics in isolation.

## Read Lyrics, Not Production

Calibrate what the words SAY, not how the song SOUNDS. A melancholic R&B track with degraded lyrics is degraded, not elevated. Vulnerable-sounding production doesn't transform sexual innuendo into honest processing. An upbeat party track with thoughtful lyrics isn't automatically shallow. Strip the instrumentation and read what's on the page.

## Zero External Knowledge

You have never heard this song before. You know nothing about it — not its genre, its cultural impact, its chart performance, its music video, its place in any album, or any critical analysis ever written about it. You are encountering these lyrics for the first time as plain text on a page.

Do not reference: the song's genre, its sonic qualities, its era's cultural context, the artist's reputation or catalog, any film/TV/cultural association, any critical or popular consensus about the song's meaning, or any fact not present in the lyrics themselves.

If your summary or reasoning contains a word that could only come from knowing the song (a genre label, a production descriptor, a reference to its legacy), you have violated this rule. Rewrite.

## The Five Tiers

Each tier is defined by what is objectively on the page, not by what the listener might feel. Any song can trigger any emotion in the right listener. We calibrate what the lyrics DO, not what they might activate.

"""


_MIDDLE = """## Calibrate the Whole Song, Not the Most Interesting Line

A few possessive or edgy lines in an otherwise straightforward love song don't make the song Degraded. A few thoughtful lines in an otherwise shallow song don't make it Elevated. The calibration reflects the song's dominant messaging, not its outliers. Assess what the song MOSTLY says — the bulk of the lyrics, the repeated refrains, the overall arc. If a small portion of the song contradicts the dominant messaging, that's what the contamination system is for, not a tier shift.

## The Core Principle: Topics Don't Determine Tiers

We do NOT calibrate topics. We calibrate MESSAGING — what the lyrics say and do on the page. The same topic can land at any tier depending on what the lyrics contain.

## Calibration Method: Start at Zero

Every song starts at Decent (charge 0). This is not a judgment — it is the starting position. From zero, you must build a case using specific lyrical evidence to move the needle in either direction.

- **To move UP:** Identify specific lyrics that process, resolve, grow, heal, or transcend. Quote or reference the actual words. "This song feels elevated" is not a case. "These lyrics demonstrate X because [specific line/image]" is a case.
- **To move DOWN:** Identify specific lyrics that degrade, objectify, celebrate harm, or promote destructive patterns. Same standard — cite the words on the page.
- **If you cannot build a clear case in either direction, the song stays Decent.** This is the correct outcome for most songs. Decent is not a failure — it is the baseline of popular music.
- **The burden of proof increases with distance from zero.** Moving to Elevated requires clear, specific evidence. Moving to Ascended requires overwhelming, undeniable evidence. Same downward. The further from zero, the higher the bar.
- **Do NOT start from an assumed tier and adjust.** Do not think "this feels like an Elevated song, let me see if it holds up." Start from zero every time. Build the case from the lyrics. Let the evidence place the song.
- **When in doubt, stay closer to zero.** A song that might be Elevated but you're not sure? It's probably high Decent. A song that might be Degraded but the evidence is ambiguous? It's probably low Decent. The compass would rather be precisely conservative than impressively wrong.

**Love songs are the clearest example:**
- Love + "our connection heals us and extends outward to our community" → **ascended** (violet). The love transcends the couple.
- Love + "we make each other better, we grow together" → **elevated** (blue). The love is a vehicle for growth.
- Love + "I love you, you love me, we're happy" → **decent** (green). It's fine. It's just filling time. Surface-level romance.
- Love + "let's get drunk and forget everything" → **degraded** (orange). The love is a cover for escapism and substance celebration.
- Love + "I own you / let's fuck / you're mine" → **corrupted** (red). The love is a cover for objectification and possession.

**The same applies to every topic** — struggle, partying, ambition, faith, heartbreak. The topic is neutral. The messaging on the page determines the tier.

"""


def _render_tier(tier: dict) -> str:
    # The v3 axis assignment rides in the tier header: orange/red tenets
    # define the harm axis, blue/violet the transcendence axis, green the
    # neutral zone of both. The tenets themselves are unchanged.
    axis = tier.get("axis")
    axis_note = ""
    if axis in ("harm", "transcendence"):
        axis_note = f" [{axis} axis]"
    elif axis == "neutral":
        axis_note = " [neutral zone of both axes]"
    lines = [f"**{tier['slug']} ({tier['label']}){axis_note}:** {tier['definition']}"]
    for tenet in tier["tenets"]:
        lines.append(f"{tenet['number']}. {tenet['text']}")
    out = "\n".join(lines)
    for note in tier.get("notes", []):
        out += f"\n\n**{note['title']}** {note['text']}"
    return out


def _render_five_tiers(data: dict) -> str:
    return "\n\n".join(_render_tier(t) for t in data["tiers"])


def _render_contamination(data: dict) -> str:
    mod = next(m for m in data["modifiers"] if m["id"] == "contamination")
    parts = [
        "## Contamination (modifier)",
        "",
        mod["definition"],
        "",
        mod["body"],
        "",
        "Examples of contamination:",
    ]
    for ex in mod["examples"]:
        parts.append(f"- {ex}")
    parts.append("")
    parts.append(mod["closing"])
    return "\n".join(parts)


def _render_rules(data: dict) -> str:
    parts = ["## Rules", ""]
    for i, rule in enumerate(data["rules"]):
        if i > 0:
            parts.append("")
        parts.append(f"{rule['id']}. {rule['text']}")
    return "\n".join(parts)


def _render_dogma(data: dict) -> str:
    """Render the dogma_referenced flag's full agent text from rc-lyric-rubric.json -- the
    single source for the calibrator (no dogma prose is hardcoded in this module
    anymore). `prompt_block` is the agent text; the definition/body/examples/
    closing fields are a separate public summary for the Tenets page, mirroring
    how the contamination modifier's public blurb differs from agent internals."""
    flag = next(f for f in data.get("flags", []) if f["id"] == "dogma_referenced")
    return flag["prompt_block"]


def build_rubric_definition() -> str:
    """Assemble the full rubric string from the prelude/middle prose and the JSON tenets."""
    data = load_tenets()
    return (
        _PRELUDE
        + _render_five_tiers(data)
        + "\n\n"
        + _MIDDLE
        + _render_dogma(data)
        + _render_contamination(data)
        + "\n\n"
        + _render_rules(data)
        + "\n\n"
    )


# RUBRIC_DEFINITION (the monolith render of rc-lyric-rubric.json) is RETIRED as of
# the 2026-06-27 cutover: the live scorer composes the gospel + rc-lyric lens
# instead, so nothing reads rc-lyric-rubric.json at import anymore (the file is
# kept off-prod as a backup). `build_rubric_definition` / `load_tenets` remain as
# functions for offline tooling only; calling them requires the backup file to be
# present locally and will raise (fail-loud) if it is not.
