"""One-time data migration: RC's live legislature -> the lecg- governance DB.

Part 2 Cut 2, the "data migration" remaining item. Moves the live participation
data out of Rising Compass and into the venue's own governance DB, re-keying
every author RC user_id -> clerk_user_id -> a lecg- citizens.id (the satellite
pattern: identity is the SHARED Clerk spine; the citizen row is the venue's local
per-property record).

What moves:
  - motions            RC.motions            -> governance.motions
  - motion_arguments   RC.motion_arguments   -> governance.motion_arguments
  - authors            RC.users (authors only) -> governance.citizens
What does NOT move:
  - RC users wholesale -- identity is shared (Clerk); the venue provisions its own
    citizen rows lazily on first authed call. The migration backfills ONLY the
    authors of existing motions/arguments so their history attributes correctly.
  - Audience Vibe / Lobby / Misread -- product feedback, stays in RC.
  - RC's rubric_changes (the genesis history). RULED (Chad, 2026-06-20): the
    constitution_amendments ledger is the FORWARD continuation only (Cut-2-onward,
    motion-linked). The genesis history already lives complete + verbatim in
    le-scaffold.json's changelog (baked into every assembled constitution), and
    governed_constitution() overlays it -- carrying rubric_changes in too would
    only duplicate it. So genesis history is NOT migrated here.

DECOUPLED BY DESIGN: this bridge reads RC over RAW SQL against the RC DSN; it does
NOT import RC's ORM models. The whole point of Part 2 is that the venue does not
reach into a product's code. After this runs once (at deploy), RC's rubric
apparatus is stripped (the RC-strip remaining item) and the link is gone.

IDEMPOTENCY / SAFETY (same discipline as RC's gated migrations):
  - One-time. Refuses to run if the target motions/arguments are already
    populated, unless --force. Runs in ONE transaction; --dry-run rolls back.
  - Citizens are keyed on clerk_user_id: a re-run (or a citizen already lazily
    provisioned, incl. the dev citizen) reuses the existing row, never duplicates.
  - Old->new id maps are threaded through (no PK preservation), so Postgres
    sequences never desync and thread structure (parent_id) is remapped exactly.
  - GATED: never run against a shared prod DB from a local checkout. Requires an
    explicit --source-url; intended to run on le-projects-01 at deploy, with both
    the RC DSN and the governance DSN reachable.

Run:
  python -m governance.lecg_rc_import --source-url <RC_DSN> [--dry-run] [--force]
  python -m governance.lecg_rc_import --selftest      # synthetic data, no network
"""

from __future__ import annotations

import argparse
import logging
import secrets
from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from governance.lecg_database import Base, SessionLocal
from governance.lecg_models import Citizen, Motion, MotionArgument


# ---------- value maps ----------

VALID_CITIZEN_STATUS = {"active", "suspended", "banned"}


# ---------- helpers ----------

def _dt(value) -> Optional[datetime]:
    """Coerce a source timestamp (datetime from psycopg, or an ISO-ish string
    from sqlite) to a datetime, or None. Tolerant of 'T'/'Z'/fractional forms."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        s = value.strip().replace("Z", "").replace("T", " ")
        if not s:
            return None
        for candidate in (s, s.split(".")[0]):
            try:
                return datetime.fromisoformat(candidate)
            except ValueError:
                continue
    return None


def _new_anon(used: set) -> str:
    """A fresh venue-scheme anon id not already taken (mirrors lecg_auth)."""
    for _ in range(10):
        cand = f"Citizen-{secrets.token_hex(4)}"
        if cand not in used:
            return cand
    raise RuntimeError("could not generate a unique anon_id after 10 attempts")


def _map_citizen_status(raw: Optional[str]) -> str:
    return raw if raw in VALID_CITIZEN_STATUS else "active"


def _rows(conn: Connection, sql: str) -> list[dict]:
    return [dict(r._mapping) for r in conn.execute(text(sql))]


# ---------- read the source (raw SQL; no RC ORM) ----------

def fetch_source(conn: Connection) -> dict:
    """Read the RC tables the migration needs. Users are narrowed to the authors
    actually referenced by a motion or argument (the venue provisions the rest
    lazily)."""
    motions = _rows(conn, (
        "SELECT id, motion_type, target_kind, target_ref, claim, reasoning, "
        "citations, filed_by_user_id, status, resolution_summary, resolved_at, "
        "resolved_by_admin_id, filed_at FROM motions ORDER BY id"
    ))
    arguments = _rows(conn, (
        "SELECT id, motion_id, user_id, post_type, parent_id, summary, body, "
        "citations, created_at FROM motion_arguments ORDER BY id"
    ))
    referenced = {m["filed_by_user_id"] for m in motions}
    referenced |= {a["user_id"] for a in arguments}
    all_users = _rows(conn, (
        "SELECT id, clerk_user_id, handle, anon_id, status FROM users ORDER BY id"
    ))
    users = [u for u in all_users if u["id"] in referenced]
    return {"users": users, "motions": motions, "motion_arguments": arguments}


# ---------- write the destination (governance ORM; flush, never commit) ----------

def import_citizens(db, users: list[dict]) -> dict:
    """Provision a citizen per referenced RC author. Keyed on clerk_user_id:
    reuses an existing citizen (re-run / lazily-provisioned / dev citizen) instead
    of duplicating. Carries handle + (continuity) the RC anon_id, regenerating on
    a collision. Returns rc_user_id -> citizen_id."""
    used_anon = {a for (a,) in db.query(Citizen.anon_id).all() if a}
    user_map: dict = {}
    for u in users:
        existing = (
            db.query(Citizen)
            .filter(Citizen.clerk_user_id == u["clerk_user_id"])
            .first()
        )
        if existing is not None:
            user_map[u["id"]] = existing.id
            continue

        anon = u.get("anon_id")
        if not anon or anon in used_anon:
            anon = _new_anon(used_anon)
        used_anon.add(anon)

        citizen = Citizen(
            clerk_user_id=u["clerk_user_id"],
            handle=u.get("handle"),
            anon_id=anon,
            status=_map_citizen_status(u.get("status")),
        )
        db.add(citizen)
        db.flush()
        user_map[u["id"]] = citizen.id
    return user_map


def import_motions(db, motions: list[dict], user_map: dict) -> dict:
    """Port motions, re-keyed to citizens. RC's integer resolved_by_admin_id has
    no username here, so it is preserved as a provenance string. Returns
    rc_motion_id -> motion_id."""
    motion_map: dict = {}
    for m in motions:
        citizen_id = user_map.get(m["filed_by_user_id"])
        if citizen_id is None:
            raise RuntimeError(
                f"motion {m['id']} author user_id={m['filed_by_user_id']} "
                "was not provisioned (source integrity)"
            )
        admin_id = m.get("resolved_by_admin_id")
        resolved_by = f"rc-admin-{admin_id}" if admin_id is not None else None

        motion = Motion(
            motion_type=m["motion_type"],
            target_kind=m.get("target_kind"),
            target_ref=m.get("target_ref"),
            claim=m["claim"],
            reasoning=m["reasoning"],
            citations=m.get("citations"),
            filed_by_citizen_id=citizen_id,
            status=m["status"],
            resolution_summary=m.get("resolution_summary"),
            resolved_at=_dt(m.get("resolved_at")),
            resolved_by_admin=resolved_by,
            filed_at=_dt(m.get("filed_at")) or datetime.utcnow(),
        )
        db.add(motion)
        db.flush()
        motion_map[m["id"]] = motion.id
    return motion_map


def import_arguments(db, arguments: list[dict], motion_map: dict, user_map: dict) -> dict:
    """Port chamber posts, re-keyed to citizens, remapping motion_id and the
    parent_id thread. Parents are inserted before children (a resolve loop, so any
    ordering / depth is safe). Returns rc_argument_id -> argument_id."""
    arg_map: dict = {}
    remaining = list(arguments)
    while remaining:
        progress = False
        still: list[dict] = []
        for a in remaining:
            parent_old = a.get("parent_id")
            if parent_old is not None and parent_old not in arg_map:
                still.append(a)
                continue

            motion_id = motion_map.get(a["motion_id"])
            if motion_id is None:
                raise RuntimeError(
                    f"argument {a['id']} references motion {a['motion_id']} "
                    "which was not migrated (source integrity)"
                )
            citizen_id = user_map.get(a["user_id"])
            if citizen_id is None:
                raise RuntimeError(
                    f"argument {a['id']} author user_id={a['user_id']} "
                    "was not provisioned (source integrity)"
                )

            arg = MotionArgument(
                motion_id=motion_id,
                citizen_id=citizen_id,
                post_type=a["post_type"],
                parent_id=(arg_map[parent_old] if parent_old is not None else None),
                summary=a["summary"],
                body=a["body"],
                citations=a.get("citations"),
                created_at=_dt(a.get("created_at")) or datetime.utcnow(),
            )
            db.add(arg)
            db.flush()
            arg_map[a["id"]] = arg.id
            progress = True
        if not progress:
            orphans = [a["id"] for a in still]
            raise RuntimeError(f"orphaned argument parent_id chain: {orphans}")
        remaining = still
    return arg_map


# ---------- orchestration ----------

def run_migration(
    db,
    source_conn: Connection,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict:
    """Run the whole migration in ONE transaction. Returns a count report.
    Refuses a populated target unless force; rolls back when dry_run."""
    existing_motions = db.query(Motion).count()
    existing_args = db.query(MotionArgument).count()
    if (existing_motions or existing_args) and not force:
        raise RuntimeError(
            f"target already populated (motions={existing_motions}, "
            f"arguments={existing_args}); refusing. Pass force=True to override."
        )

    src = fetch_source(source_conn)
    user_map = import_citizens(db, src["users"])
    motion_map = import_motions(db, src["motions"], user_map)
    arg_map = import_arguments(db, src["motion_arguments"], motion_map, user_map)

    report = {
        "citizens_provisioned": len(user_map),
        "motions": len(motion_map),
        "arguments": len(arg_map),
        "dry_run": dry_run,
        "forced": force,
    }

    if dry_run:
        db.rollback()
    else:
        db.commit()
    return report


# ---------- CLI ----------

def main(argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Migrate RC's legislature into the lecg- governance DB.")
    parser.add_argument("--source-url", help="RC database DSN (read-only source).")
    parser.add_argument("--dry-run", action="store_true", help="Run inside a transaction, then roll back.")
    parser.add_argument("--force", action="store_true", help="Proceed even if the target is already populated.")
    parser.add_argument("--selftest", action="store_true", help="Run the synthetic self-test (no network).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    if args.selftest:
        return _selftest()

    if not args.source_url:
        parser.error("--source-url is required (or use --selftest)")

    Base.metadata.create_all(bind=SessionLocal().get_bind())
    source_engine = create_engine(args.source_url)
    db = SessionLocal()
    try:
        with source_engine.connect() as source_conn:
            report = run_migration(db, source_conn, force=args.force, dry_run=args.dry_run)
    finally:
        db.close()
        source_engine.dispose()

    print("RC -> lecg governance migration report:")
    for key, value in report.items():
        print(f"  {key}: {value}")
    return 0


# ---------- self-test (synthetic source + throwaway governance DBs) ----------

def _selftest() -> int:
    import os
    import tempfile
    from sqlalchemy.orm import sessionmaker

    checks: list = []

    def chk(name, ok):
        checks.append((name, bool(ok)))

    def _fresh_engine(tag):
        path = os.path.join(tempfile.gettempdir(), f"lecg_rcimport_{tag}.db")
        if os.path.exists(path):
            os.remove(path)
        return create_engine(f"sqlite:///{path}")

    # --- build a synthetic RC source ---
    src_engine = _fresh_engine("src")
    with src_engine.begin() as c:
        c.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, clerk_user_id TEXT, handle TEXT, anon_id TEXT, status TEXT)"))
        c.execute(text("CREATE TABLE motions (id INTEGER PRIMARY KEY, motion_type TEXT, target_kind TEXT, target_ref TEXT, claim TEXT, reasoning TEXT, citations TEXT, filed_by_user_id INTEGER, status TEXT, resolution_summary TEXT, resolved_at TEXT, resolved_by_admin_id INTEGER, filed_at TEXT)"))
        c.execute(text("CREATE TABLE motion_arguments (id INTEGER PRIMARY KEY, motion_id INTEGER, user_id INTEGER, post_type TEXT, parent_id INTEGER, summary TEXT, body TEXT, citations TEXT, created_at TEXT)"))
        # users: 1 alice + 2 bob author things; 3 carol has no activity (must NOT migrate)
        c.execute(text(
            "INSERT INTO users VALUES "
            "(1,'clerk_alice','alice','rc-anon-1','active'),"
            "(2,'clerk_bob','bob','rc-anon-2','active'),"
            "(3,'clerk_carol','carol','rc-anon-3','active')"
        ))
        # motion 1: amend_tenet by alice, ratified, admin id 5; motion 2: process by bob
        c.execute(text(
            "INSERT INTO motions VALUES "
            "(1,'amend_tenet','tenet','violet-01','claim one','reason one text',"
            "'[\"https://example.org/e\"]',1,'ratified','resolved well enough here',"
            "'2026-06-01 10:00:00',5,'2026-05-01 09:00:00'),"
            "(2,'process',NULL,NULL,'claim two','reason two text',NULL,2,"
            "'in_deliberation',NULL,NULL,NULL,'2026-05-02 09:00:00')"
        ))
        # arguments on motion 1: top-level by bob, then a rebuttal by alice -> parent 1
        c.execute(text(
            "INSERT INTO motion_arguments VALUES "
            "(1,1,2,'argument_for',NULL,'sum one','body one text',NULL,'2026-05-03 09:00:00'),"
            "(2,1,1,'rebuttal',1,'sum two','body two text',NULL,'2026-05-04 09:00:00')"
        ))

    def _gov_session(tag):
        eng = _fresh_engine(tag)
        Base.metadata.create_all(bind=eng)
        return eng, sessionmaker(bind=eng, autoflush=False, autocommit=False)

    # --- 1. core migration ---
    eng1, Gov1 = _gov_session("gov1")
    db = Gov1()
    with src_engine.connect() as sc:
        report = run_migration(db, sc)

    chk("report counts (2 citizens / 2 motions / 2 args)",
        report["citizens_provisioned"] == 2 and report["motions"] == 2 and report["arguments"] == 2)
    chk("citizens = 2 (authors only)", db.query(Citizen).count() == 2)
    chk("carol NOT provisioned (no activity)",
        db.query(Citizen).filter_by(clerk_user_id="clerk_carol").first() is None)
    chk("motions = 2", db.query(Motion).count() == 2)
    chk("arguments = 2", db.query(MotionArgument).count() == 2)

    alice = db.query(Citizen).filter_by(clerk_user_id="clerk_alice").first()
    bob = db.query(Citizen).filter_by(clerk_user_id="clerk_bob").first()
    chk("handle carried", alice is not None and alice.handle == "alice")

    m1 = db.query(Motion).filter_by(target_ref="violet-01").first()
    chk("motion author re-keyed RC->citizen", m1.filed_by_citizen_id == alice.id)
    chk("motion status preserved", m1.status == "ratified")
    chk("motion resolved_by_admin mapped", m1.resolved_by_admin == "rc-admin-5")
    chk("motion filed_at preserved", m1.filed_at is not None and m1.filed_at.month == 5 and m1.filed_at.year == 2026)
    chk("motion resolved_at preserved", m1.resolved_at is not None and m1.resolved_at.month == 6)
    chk("citations preserved verbatim", bool(m1.citations) and "example.org" in m1.citations)

    parent = db.query(MotionArgument).filter_by(parent_id=None).first()
    child = db.query(MotionArgument).filter(MotionArgument.parent_id.isnot(None)).first()
    chk("argument thread remapped (child.parent == parent.id)", child.parent_id == parent.id)
    chk("argument parent on the right motion", parent.motion_id == m1.id)
    chk("argument author re-keyed (parent by bob)", parent.citizen_id == bob.id)
    chk("rebuttal author re-keyed (child by alice)", child.citizen_id == alice.id)

    # --- 2. idempotency guard (a re-run refuses a populated target) ---
    guard = False
    db2 = Gov1()
    try:
        with src_engine.connect() as sc:
            run_migration(db2, sc)
    except RuntimeError:
        guard = True
    finally:
        db2.rollback()
        db2.close()
    chk("idempotency guard refuses populated target", guard)
    db.close()

    # --- 3. dry-run leaves the target empty ---
    eng3, Gov3 = _gov_session("gov3")
    dbd = Gov3()
    with src_engine.connect() as sc:
        dry_report = run_migration(dbd, sc, dry_run=True)
    chk("dry-run reports work done", dry_report["motions"] == 2 and dry_report["arguments"] == 2)
    chk("dry-run persisted nothing (motions)", dbd.query(Motion).count() == 0)
    chk("dry-run persisted nothing (citizens)", dbd.query(Citizen).count() == 0)
    dbd.close()

    src_engine.dispose()
    for eng in (eng1, eng3):
        eng.dispose()

    passed = sum(1 for _, ok in checks if ok)
    for name, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\nlecg_rc_import self-test: {passed}/{len(checks)}")
    if passed != len(checks):
        return 1
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
