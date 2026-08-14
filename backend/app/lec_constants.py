# Tier display constants -- single source of truth. Lifted verbatim from Rising
# Compass (the tier vocabulary IS the rubric's, so it must not drift). The
# consumer maps color_key to its OWN palette; these hexes are RC's reference.
COLOR_LABELS = {
    "violet": "Ascended", "blue": "Elevated", "green": "Decent",
    "orange": "Degraded", "red": "Corrupted",
}
COLOR_HEX = {
    "violet": "#9933ff", "blue": "#3388ff", "green": "#33cc55",
    "orange": "#ffbb33", "red": "#ff3333",
}
COLOR_BG = {
    "violet": "#f3e8ff", "blue": "#e8f0ff", "green": "#e8fae8",
    "orange": "#fff5e0", "red": "#ffe8e8",
}

# Canonical tier order, strongest -> weakest. Single source for /api/rubric tiers.
TIER_ORDER = ["violet", "blue", "green", "orange", "red"]

# Artifact types the Compass reads (POST /api/score). The calibrator reads any
# of these against the SAME rubric; `lyric` is RC's own default (byte-for-byte
# unchanged scoring). The non-lyric types are the Creative/Curio charger
# surfaces. Per-type precedent corpora are a separate content workstream; until
# they land, the lyric precedent table anchors every type. The label is how the
# user prompt frames the read.
ARTIFACT_TYPE_LABELS = {
    "lyric": "song",
    "poem": "poem",
    "prose_essay": "essay",
    "script_dialogue": "script",
    "message": "message",
    "email": "email",
    "article": "article",
    # A release read as one work. Unlike every other type, its text is not prose
    # the lens interprets: it is the artifact's own approved song ROWS in running
    # order. It is also the only type that does NOT read by the song lens -- see
    # LENS_FOR_ARTIFACT in app/rubric/lec_lens.py.
    "album": "album",
}
ARTIFACT_TYPES = frozenset(ARTIFACT_TYPE_LABELS)
