"""The amendment pipeline + the ratification WRITE-BACK (lecg-).

Two halves:

1. The amendment LOG (read surface) -- a faithful port of RC's
   services/amendments: the static framing (venue / thresholds / statuses)
   merged with live motions mapped into amendment shape. Re-keyed to Citizen;
   the venue IS the deliberation home now, so the discussion link points at this
   venue's Chamber.

2. The ratification WRITE-BACK (the piece that NEVER existed). RC's plan said
   "update core.json on ratify" and never built it. Here it is, designed to the
   Integrity Spine + the six rulings:

   - The GENESIS constitution (the founding law, the pre-Cut-2 changelog) stays
     immutable in the repo (le-baseline/*.json), assembled by lecg_constitution.
     That frozen artifact is what the lec- INSTRUMENT pins and scores against --
     it has no governance-DB access (Decision 1/4: distinct app, distinct DB, no
     inter-service HTTP), so it can only ever see a repo-versioned edition.

   - Each ratified amendment is a first-class, provenance-bearing row in THIS
     venue's DB (constitution_amendments), tied to the motion that forced it. The
     GOVERNED constitution = genesis OVERLAID with the ratified amendment layer;
     governed_version() is its hash. With zero amendments it equals the genesis
     constitution_version (in sync).

   - A ratification bumps governed_version immediately. The instrument adopts the
     new law DELIBERATELY: an edition is materialized from the governed
     constitution (materialize_edition) and the instrument re-pins it on its own
     clock. THAT is the Integrity-Spine safety valve -- a live amendment can never
     silently change what a paid product scores against. Until an edition is cut,
     the instrument's /health reports the pin out of sync, surfacing the pending
     adoption.

   The genesis hash is unchanged (instrument unaffected) until that deliberate
   edition. Cut 2 builds the write-back + the materialize step; the file-write /
   commit / redeploy that adopts an edition stays the gated human act.
"""

from __future__ import annotations

import copy
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from governance.lecg_constitution import (
    _assemble, _assemble_from_dicts, _load_dicts, _version_of,
)
from governance.lecg_models import Citizen, ConstitutionAmendment, Motion
from governance.lecg_motions import VALID_MOTION_TYPES, transition_status

logger = logging.getLogger(__name__)


# ======================================================================
# The amendment log (read surface)
# ======================================================================

# Compass-framed static config. The venue is no longer off-site (RC's log.json
# pointed at a Discord stub) -- deliberation happens in this venue's Chamber, and
# the Compass holds the public record directly.
_LOG_CONFIG = {
    "schema_version": "2.0",
    "updated_at": "2026-06-20",
    "venue": {
        "platform": "libra-engine-compass",
        "url": "/motion-desk/",
        "coming_soon": False,
        "note": "Deliberation happens in the open, inside the Compass: the Motion "
                "Desk files proposals, the Deliberation Chamber hosts the argument, "
                "and ratification amends the constitution the instrument scores "
                "against. The Compass houses the law; the public authors it.",
    },
    "thresholds": {
        "co_sponsors_required": 7,
        "deliberation_window_days": 21,
        "ratification_supermajority_pct": 66,
    },
    "statuses": [
        {"key": "proposed", "label": "Proposed", "description": "Filed at the Motion Desk. Awaiting the move to deliberation."},
        {"key": "deliberating", "label": "Deliberating", "description": "The floor is open. The Deliberation Chamber hosts the argument."},
        {"key": "ratified", "label": "Ratified", "description": "Accepted. The amendment is written back to the canonical constitution and the law version bumps."},
        {"key": "covered", "label": "Already Covered", "description": "Raised in good faith, but the substance is already held by an existing tenet."},
        {"key": "rejected", "label": "Rejected", "description": "Went through deliberation and did not clear the ratification bar."},
    ],
}

_STATUS_MAP = {
    "filed": "proposed",
    "in_deliberation": "deliberating",
    "ratified": "ratified",
    "rejected": "rejected",
    "covered": "covered",
}


def _format_date(dt) -> Optional[str]:
    if dt is None:
        return None
    try:
        return dt.date().isoformat()
    except AttributeError:
        return None


def _title_from_motion(motion: Motion) -> str:
    claim = (motion.claim or "").strip()
    mt = motion.motion_type
    if mt == "amend_tenet" and motion.target_ref:
        return f"Amend tenet {motion.target_ref}: {claim}"
    if mt == "remove_tenet" and motion.target_ref:
        return f"Remove tenet {motion.target_ref}: {claim}"
    if mt == "new_tenet":
        return f"New tenet: {claim}"
    if mt == "amend_rule" and motion.target_ref:
        kind = motion.target_kind or "rule"
        return f"Amend {kind} {motion.target_ref}: {claim}"
    if mt == "remove_rule" and motion.target_ref:
        kind = motion.target_kind or "rule"
        return f"Remove {kind} {motion.target_ref}: {claim}"
    if mt == "new_rule":
        return f"New rule: {claim}"
    if mt == "process":
        return f"Process: {claim}"
    return claim


def _motion_to_amendment(db: Session, motion: Motion) -> dict:
    filer = db.query(Citizen).get(motion.filed_by_citizen_id) if motion.filed_by_citizen_id else None
    proposer = (filer.handle if filer and filer.handle else (filer.anon_id if filer else None))

    status = _STATUS_MAP.get(motion.status, motion.status)
    cites_tenet = motion.target_ref if motion.target_kind == "tenet" else None

    out: dict = {
        "id": f"motion-{motion.id:04d}",
        "status": status,
        "proposed_at": _format_date(motion.filed_at),
        "proposer": proposer,
        "cites_tenet": cites_tenet,
        "target_kind": motion.target_kind,
        "target_ref": motion.target_ref,
        "motion_type": motion.motion_type,
        "title": _title_from_motion(motion),
        "proposed_change": motion.reasoning,
        "novelty_argument": None,
        "soundness_argument": None,
        "discussion_url": (f"/motion-desk/deliberation-chamber/{motion.id}/" if motion.status != "filed" else None),
        "co_sponsors": 0,
        "deliberation_opens_at": None,
        "deliberation_closes_at": None,
        "ratified_at": None,
        "rejected_at": None,
        "covered_by": None,
        "rejection_reason": None,
    }
    resolved_date = _format_date(motion.resolved_at)
    if status == "ratified":
        out["ratified_at"] = resolved_date
    elif status == "rejected":
        out["rejected_at"] = resolved_date
        out["rejection_reason"] = motion.resolution_summary
    elif status == "covered":
        out["rejected_at"] = resolved_date
        out["rejection_reason"] = motion.resolution_summary
        out["covered_by"] = motion.target_ref if motion.target_kind == "tenet" else None
    return out


def load_amendment_log(db: Optional[Session] = None) -> dict:
    """The merged public amendment log: static framing + live motions."""
    config = copy.deepcopy(_LOG_CONFIG)
    amendments: list[dict] = []
    if db is not None:
        rows = (
            db.query(Motion)
            .filter(Motion.motion_type.in_(VALID_MOTION_TYPES))
            .order_by(Motion.filed_at.desc())
            .all()
        )
        amendments = [_motion_to_amendment(db, m) for m in rows]
    config["amendments"] = amendments
    return config


# ======================================================================
# The governed constitution = genesis + the ratified amendment layer
# ======================================================================

VALID_CHANGES = {"add", "amend", "remove"}
VALID_AMEND_KINDS = {"tenet", "rule", "modifier", "flag", "note", "tier", "method", "process"}


def _find_item(constitution: dict, kind: str, ref: Optional[str]) -> Optional[dict]:
    """Locate the operative item by (kind, ref) in an assembled constitution."""
    if kind == "tenet":
        for tier in constitution.get("tiers", []):
            for ten in tier.get("tenets", []):
                if ten.get("id") == ref:
                    return ten
    elif kind == "note":
        for tier in constitution.get("tiers", []):
            for note in tier.get("notes", []):
                if note.get("id") == ref:
                    return note
    elif kind == "rule":
        for r in constitution.get("rules", []):
            if r.get("id") == ref:
                return r
    elif kind == "modifier":
        for m in constitution.get("modifiers", []):
            if m.get("id") == ref:
                return m
    elif kind == "flag":
        for f in constitution.get("flags", []):
            if f.get("id") == ref:
                return f
    elif kind == "tier":
        for tier in constitution.get("tiers", []):
            if tier.get("slug") == ref:
                return tier
    return None


def _apply_amendment(constitution: dict, row: ConstitutionAmendment) -> None:
    """Mutate an assembled constitution in place by one ratified amendment, and
    append the matching changelog entry. amend = retext + version bump (the
    common case, fully supported). remove = mark status repealed. add = append a
    minimal item (the rich add payload -- number/tier placement -- is a follow-up;
    the changelog records it regardless). Unknown / process-level changes only
    append to the changelog (no operative edit)."""
    change = row.change
    kind = row.target_kind
    ref = row.target_ref

    if change == "amend" and kind in {"tenet", "rule", "modifier", "flag", "note", "tier"}:
        item = _find_item(constitution, kind, ref)
        if item is not None:
            if row.new_core is not None:
                item["core"] = row.new_core
            if row.to_version is not None:
                item["version"] = row.to_version
            item["status"] = "ratified"
    elif change == "remove" and kind in {"tenet", "rule", "modifier", "flag", "note", "tier"}:
        item = _find_item(constitution, kind, ref)
        if item is not None:
            item["status"] = "repealed"
            if row.to_version is not None:
                item["version"] = row.to_version
    elif change == "add" and kind in {"rule", "modifier", "flag"}:
        # Minimal add into the flat collections; tenets/notes need tier placement
        # (a richer payload), deferred to the materialize/author step.
        collection = {"rule": "rules", "modifier": "modifiers", "flag": "flags"}[kind]
        constitution.setdefault(collection, []).append({
            "id": ref,
            "core": row.new_core or "",
            "version": row.to_version or "1.0",
            "status": "ratified",
            "ratified_at": (row.ratified_at.date().isoformat() if row.ratified_at else None),
        })

    constitution.setdefault("changelog", []).append({
        "at": (row.ratified_at.date().isoformat() if row.ratified_at else _format_date(datetime.utcnow())),
        "change": change,
        "target": ref or kind,
        "from_version": row.from_version,
        "to_version": row.to_version,
        "summary": row.summary,
        "source": row.source_label,
    })


def governed_constitution(db: Session, baseline_dir=None) -> dict:
    """The current governed law = genesis assembled fresh, then each PENDING
    (ratified-but-not-yet-adopted) amendment applied in order, then re-versioned.
    The venue's live view.

    Only `adopted_at IS NULL` rows overlay: once an edition bakes an amendment into
    le-baseline (the genesis the instrument pins), re-applying it here would
    double-count it, so adopted rows drop out of the overlay and live on as
    provenance + in the baked changelog. baseline_dir overrides the genesis source
    (the adoption round-trip self-test points it at a temp copy)."""
    constitution = _assemble(baseline_dir)  # fresh dict (never the lru_cached load_constitution)
    rows = (
        db.query(ConstitutionAmendment)
        .filter(ConstitutionAmendment.adopted_at.is_(None))
        .order_by(ConstitutionAmendment.id.asc())
        .all()
    )
    for row in rows:
        _apply_amendment(constitution, row)
    constitution["constitution_version"] = _version_of(constitution)
    return constitution


def governed_version(db: Session) -> str:
    """The governed law version (genesis + the ratified amendment layer)."""
    return governed_constitution(db)["constitution_version"]


def materialize_edition(db: Session) -> dict:
    """PREVIEW of the next edition: the full governed constitution the instrument
    would adopt (genesis + every pending amendment). The admin edition/preview
    surface returns this for review. The actual WRITE -- baking it into le-baseline
    + marking the amendments adopted -- is materialize_to_baseline (below); the
    re-pin is the gated git-commit + redeploy, per the Integrity-Spine safety valve."""
    return governed_constitution(db)


# ======================================================================
# The ratification WRITE-BACK
# ======================================================================

def ratify_motion(
    db: Session,
    motion: Motion,
    resolution_summary: str,
    admin_username: str,
    amendment: Optional[dict] = None,
) -> tuple[Motion, Optional[ConstitutionAmendment]]:
    """Ratify a motion AND (if an amendment payload is supplied) write the change
    back to the constitution: record a constitution_amendments row tied to this
    motion, stamping the governed law version before and after.

    amendment (optional dict): {change, target_kind, target_ref?, to_version?,
    new_core?, summary}. Omitted => a bare ratification (process motions that
    bless without retexting, or a ratification whose text is cut in a follow-up).
    When supplied, the governed_version bumps and the instrument's pin goes out of
    sync until an edition is deliberately adopted.
    """
    # 1. Transition the motion (validates the lifecycle + the summary length).
    transition_status(db, motion, "ratified", admin_username, resolution_summary)

    if amendment is None:
        logger.info("Motion %s ratified (no constitution write-back)", motion.id)
        return motion, None

    change = (amendment.get("change") or "").strip().lower()
    kind = (amendment.get("target_kind") or "").strip().lower()
    ref = amendment.get("target_ref")
    if ref is not None:
        ref = ref.strip() or None
    to_version = amendment.get("to_version")
    new_core = amendment.get("new_core")
    summary = (amendment.get("summary") or "").strip()

    if change not in VALID_CHANGES:
        raise HTTPException(status_code=422, detail=f"amendment.change must be one of {sorted(VALID_CHANGES)}")
    if kind not in VALID_AMEND_KINDS:
        raise HTTPException(status_code=422, detail=f"amendment.target_kind must be one of {sorted(VALID_AMEND_KINDS)}")
    if not summary or len(summary) < 10:
        raise HTTPException(status_code=422, detail="amendment.summary required (10+ chars) -- the changelog line")
    if change == "amend" and not new_core:
        raise HTTPException(status_code=422, detail="amend requires amendment.new_core (the new neutral law text)")
    if change in {"amend", "remove"} and kind in {"tenet", "rule", "modifier", "flag", "note", "tier"} and not ref:
        raise HTTPException(status_code=422, detail=f"{change} of a {kind} requires amendment.target_ref")

    # 2. Capture the governed version + the target item's current version BEFORE.
    before_constitution = governed_constitution(db)
    before_version = before_constitution["constitution_version"]
    from_version = None
    if ref and kind in {"tenet", "rule", "modifier", "flag", "note", "tier"}:
        item = _find_item(before_constitution, kind, ref)
        if item is not None:
            from_version = item.get("version")

    # 3. Record the amendment (the provenance spine), tied to the motion.
    row = ConstitutionAmendment(
        motion_id=motion.id,
        change=change,
        target_kind=kind,
        target_ref=ref,
        from_version=from_version,
        to_version=to_version,
        summary=summary,
        new_core=new_core,
        source_label=f"motion-{motion.id:04d}",
        constitution_version_before=before_version,
        ratified_by_admin=admin_username,
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    # 4. The new governed version now includes this amendment. Stamp it.
    row.constitution_version_after = governed_version(db)
    db.commit()
    db.refresh(row)

    logger.info(
        "Constitution amended by motion %s: %s %s/%s  %s -> %s  (gov %s -> %s)",
        motion.id, change, kind, ref, from_version, to_version,
        before_version, row.constitution_version_after,
    )
    return motion, row


# ======================================================================
# Edition adoption: materialize the governed law into le-baseline
# ======================================================================
# RULED (Chad, 2026-06-20): the instrument adopts a ratified edition by
# materializing the governed constitution back into the le-baseline files (the
# genesis the lec instrument pins + scores against), then a git commit (tag
# edition-<version>) + redeploy re-pins it. Git is the edition ledger; genesis
# lives on as a tag, not a separate frozen file. This is the deliberate, gated act
# -- ratification only grows the pending overlay; nothing the live scorer sees
# moves until an edition is adopted here (the Integrity-Spine safety valve).

_FILE_EDITABLE = {"tenet", "rule", "modifier", "flag", "note", "tier"}


def _find_in_file(doc: dict, kind: str, ref: Optional[str]) -> Optional[dict]:
    """Locate an item by (kind, ref) inside a RAW le-baseline file dict (cores or
    scaffold -- both carry the same tiers/tenets/notes/rules/modifiers/flags
    shape)."""
    if kind == "tenet":
        for tier in doc.get("tiers", []):
            for x in tier.get("tenets", []):
                if x.get("id") == ref:
                    return x
    elif kind == "note":
        for tier in doc.get("tiers", []):
            for x in tier.get("notes", []):
                if x.get("id") == ref:
                    return x
    elif kind == "rule":
        for x in doc.get("rules", []):
            if x.get("id") == ref:
                return x
    elif kind == "modifier":
        for x in doc.get("modifiers", []):
            if x.get("id") == ref:
                return x
    elif kind == "flag":
        for x in doc.get("flags", []):
            if x.get("id") == ref:
                return x
    elif kind == "tier":
        for tier in doc.get("tiers", []):
            if tier.get("slug") == ref:
                return tier
    return None


def _apply_amendment_to_files(cores: dict, scaffold: dict, row: ConstitutionAmendment) -> None:
    """Apply ONE amendment to the raw le-baseline file dicts, mirroring
    _apply_amendment (which mutates the ASSEMBLED dict) field-for-field, so that
    re-assembling the written files reproduces governed_constitution exactly: the
    neutral text lives in cores, the per-item version + status in scaffold, and the
    changelog entry appends to scaffold verbatim. Delta-apply (not a full decompose)
    so any field _assemble does not read is preserved untouched. amend + remove are
    exact; add of a rule/modifier/flag is minimal; a tenet/note add needs tier
    placement (the author step) and is left to a manual edition."""
    change, kind, ref = row.change, row.target_kind, row.target_ref

    if change == "amend" and kind in _FILE_EDITABLE:
        core_item = _find_in_file(cores, kind, ref)
        scaf_item = _find_in_file(scaffold, kind, ref)
        if core_item is not None and row.new_core is not None:
            core_item["definition_core" if kind == "tier" else "core"] = row.new_core
        if scaf_item is not None:
            if row.to_version is not None:
                scaf_item["version"] = row.to_version
            scaf_item["status"] = "ratified"
    elif change == "remove" and kind in _FILE_EDITABLE:
        scaf_item = _find_in_file(scaffold, kind, ref)
        if scaf_item is not None:
            scaf_item["status"] = "repealed"
            if row.to_version is not None:
                scaf_item["version"] = row.to_version
    elif change == "add" and kind in {"rule", "modifier", "flag"}:
        coll = {"rule": "rules", "modifier": "modifiers", "flag": "flags"}[kind]
        cores.setdefault(coll, []).append({"id": ref, "core": row.new_core or ""})
        scaffold.setdefault(coll, []).append({
            "id": ref,
            "version": row.to_version or "1.0",
            "status": "ratified",
            "ratified_at": (row.ratified_at.date().isoformat() if row.ratified_at else None),
        })
    # process / tenet-or-note add / unknown: changelog only (no operative file edit)

    scaffold.setdefault("changelog", []).append({
        "at": (row.ratified_at.date().isoformat() if row.ratified_at else _format_date(datetime.utcnow())),
        "change": change,
        "target": ref or kind,
        "from_version": row.from_version,
        "to_version": row.to_version,
        "summary": row.summary,
        "source": row.source_label,
    })


def _write_baseline(baseline_dir, cores: dict, scaffold: dict) -> None:
    """Write cores + scaffold back to le-baseline (method is never amended here).
    Preserves the files' indent so the git diff shows only the real changes."""
    from governance.lecg_constitution import BASELINE_DIR, CORES_PATH, SCAFFOLD_PATH
    base = Path(baseline_dir) if baseline_dir else BASELINE_DIR
    for path, doc in ((base / CORES_PATH.name, cores), (base / SCAFFOLD_PATH.name, scaffold)):
        with path.open("w", encoding="utf-8") as fh:
            json.dump(doc, fh, ensure_ascii=False, indent=2)
            fh.write("\n")


def materialize_to_baseline(db: Session, *, baseline_dir=None, dry_run: bool = False) -> dict:
    """Adopt an edition: bake every PENDING amendment into the le-baseline files
    (the genesis the lec instrument pins + scores), then mark those amendments
    adopted so the overlay stops re-applying them (no double-count). The caller
    finishes adoption out of band -- review the git diff, commit + tag
    edition-<version>, redeploy -- which is what actually re-pins the instrument
    (the live scorer moves only by a deliberate human act).

    dry_run leaves the files + the rows untouched and only reports what would adopt
    (so the admin can review the materialized law before committing)."""
    cores, scaffold, method = _load_dicts(baseline_dir)
    pending = (
        db.query(ConstitutionAmendment)
        .filter(ConstitutionAmendment.adopted_at.is_(None))
        .order_by(ConstitutionAmendment.id.asc())
        .all()
    )
    for row in pending:
        _apply_amendment_to_files(cores, scaffold, row)

    new_version = _version_of(_assemble_from_dicts(cores, scaffold, method))

    if not dry_run:
        _write_baseline(baseline_dir, cores, scaffold)
        stamp = datetime.utcnow()
        for row in pending:
            row.adopted_at = stamp
            row.adopted_in_version = new_version
        db.commit()
        logger.info(
            "Edition adopted: %d amendment(s) baked into le-baseline; version -> %s "
            "(commit + tag + redeploy to re-pin the instrument)",
            len(pending), new_version,
        )

    return {
        "version": new_version,
        "amendments_adopted": len(pending),
        "dry_run": dry_run,
    }
