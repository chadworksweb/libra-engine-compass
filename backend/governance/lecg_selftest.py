"""LECG governance self-test -- the venue end to end, no model call / no network.

Exercises the whole Cut 2 pipeline against a throwaway SQLite DB:
  file a motion -> deliberate -> post an argument -> ratify WITH write-back,
and asserts the invariants that matter:

  - target validation reads the CANONICAL CONSTITUTION (a bogus tenet 422s);
  - the lifecycle state machine holds;
  - the ratification WRITE-BACK records a constitution_amendment, bumps the
    governed_version, and rewrites the governed law text;
  - the SEAM holds: the genesis constitution_version (what the lec INSTRUMENT
    pins) is UNCHANGED by a ratification -- the instrument adopts deliberately;
  - the chamber depth + self-rebut rules hold.

Run:  cd backend && python -m governance.lecg_selftest
(uses a temp sqlite file via LECG_DATABASE_URL; set automatically if unset.)
"""

import os
import sys
import tempfile

# Use a throwaway sqlite DB so the self-test never touches a real one. Set BEFORE
# importing the engine (governance.lecg_config reads env at import).
if "LECG_DATABASE_URL" not in os.environ or "lecg_selftest" not in os.environ.get("LECG_DATABASE_URL", ""):
    _tmp = os.path.join(tempfile.gettempdir(), "lecg_selftest.db")
    if os.path.exists(_tmp):
        os.remove(_tmp)
    os.environ["LECG_DATABASE_URL"] = f"sqlite:///{_tmp}"

from fastapi import HTTPException  # noqa: E402

from governance.lecg_constitution import constitution_version  # noqa: E402
from governance.lecg_database import Base, engine, SessionLocal  # noqa: E402
from governance import lecg_models  # noqa: E402,F401
from governance.lecg_models import Citizen  # noqa: E402
from governance import lecg_amendments as A  # noqa: E402
from governance import lecg_chamber as C  # noqa: E402
from governance import lecg_motions as M  # noqa: E402


_checks = []


def check(name, ok):
    _checks.append((name, bool(ok)))


def _mk_citizen(db, clerk_id, handle):
    c = Citizen(clerk_user_id=clerk_id, anon_id=f"anon-{clerk_id}", handle=handle, status="active")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def run():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    genesis = constitution_version()
    check("genesis constitution_version present", bool(genesis))
    check("governed == genesis at zero amendments", A.governed_version(db) == genesis)

    alice = _mk_citizen(db, "clerk_alice", "alice")
    bob = _mk_citizen(db, "clerk_bob", "bob")

    # --- target validation against the canonical constitution ---
    bogus_422 = False
    try:
        M.file_motion(db, alice, "amend_tenet", "tenet", "violet-99", "x", "y" * 60, None)
    except HTTPException as e:
        bogus_422 = (e.status_code == 422)
    check("bogus tenet target rejected (422)", bogus_422)

    bad_rule_422 = False
    try:
        M.file_motion(db, alice, "amend_rule", "rule", "R999", "x", "y" * 60, None)
    except HTTPException as e:
        bad_rule_422 = (e.status_code == 422)
    check("bogus rule target rejected (422)", bad_rule_422)

    # --- file a real motion ---
    motion = M.file_motion(
        db, alice, "amend_tenet", "tenet", "violet-01",
        claim="Tighten violet-01 to separate sacred substance from sacred tone.",
        reasoning="The current wording reads reverent tone as substance; this narrows it. " * 2,
        citations=["https://example.org/evidence"],
    )
    check("motion filed", motion.status == "filed")
    check("motion target normalized", motion.target_ref == "violet-01" and motion.target_kind == "tenet")

    # --- lifecycle: cannot post in the chamber before deliberation ---
    closed_409 = False
    try:
        C.post_argument(db, bob, motion, "argument_for", None, "early", "z" * 60, None)
    except HTTPException as e:
        closed_409 = (e.status_code == 409)
    check("chamber closed before deliberation (409)", closed_409)

    # --- move to deliberation ---
    M.transition_status(db, motion, "in_deliberation", admin_username="tester")
    check("motion in_deliberation", motion.status == "in_deliberation")

    # --- chamber: a top-level argument, then a rebuttal; self-rebut blocked ---
    arg = C.post_argument(db, alice, motion, "argument_for", None, "for it", "Because the narrowing is sound. " * 3, None)
    check("argument posted", arg.id is not None and arg.parent_id is None)

    self_rebut_422 = False
    try:
        C.post_argument(db, alice, motion, "rebuttal", arg.id, "self", "rebutting my own. " * 4, None)
    except HTTPException as e:
        self_rebut_422 = (e.status_code == 422)
    check("self-rebut blocked (422)", self_rebut_422)

    rebut = C.post_argument(db, bob, motion, "rebuttal", arg.id, "against", "I disagree because. " * 4, None)
    check("rebuttal posted to top-level", rebut.parent_id == arg.id)

    nested_422 = False
    try:
        C.post_argument(db, alice, motion, "rebuttal", rebut.id, "nest", "nested rebuttal. " * 4, None)
    except HTTPException as e:
        nested_422 = (e.status_code == 422)
    check("nested rebuttal blocked -- 2-level depth cap (422)", nested_422)

    # --- ratify WITH the write-back ---
    new_text = "A work reaches the Ascended ceiling only on delivered sacred substance, not on reverent tone alone."
    motion, row = A.ratify_motion(
        db, motion,
        resolution_summary="Ratified after deliberation: the narrowing holds without lowering the ceiling.",
        admin_username="tester",
        amendment={
            "change": "amend", "target_kind": "tenet", "target_ref": "violet-01",
            "to_version": "1.1", "new_core": new_text,
            "summary": "Narrow violet-01: sacred substance, not reverent tone, governs the Ascended ceiling.",
        },
    )
    check("motion ratified", motion.status == "ratified")
    check("amendment row recorded", row is not None and row.motion_id == motion.id)
    check("amendment tied to motion source_label", row.source_label == f"motion-{motion.id:04d}")
    check("amendment from_version captured", row.from_version == "1.0")
    check("amendment to_version captured", row.to_version == "1.1")
    check("version_before == genesis", row.constitution_version_before == genesis)
    check("version_after differs from before", row.constitution_version_after and row.constitution_version_after != genesis)

    gov = A.governed_constitution(db)
    v01 = A._find_item(gov, "tenet", "violet-01")
    check("governed law text rewritten", v01 is not None and v01["core"] == new_text)
    check("governed item version bumped", v01["version"] == "1.1")
    check("governed_version moved off genesis", gov["constitution_version"] != genesis)
    check("changelog grew by the amendment", any(e.get("source") == f"motion-{motion.id:04d}" for e in gov.get("changelog", [])))

    # --- THE SEAM: the instrument's genesis pin is UNCHANGED ---
    check("genesis (instrument pin) unchanged by ratification", constitution_version() == genesis)

    # --- materialize_edition reflects the amendment (preview) ---
    edition = A.materialize_edition(db)
    ed01 = A._find_item(edition, "tenet", "violet-01")
    check("edition carries the amended text", ed01 is not None and ed01["core"] == new_text)

    # --- EDITION ADOPTION: materialize into a TEMP le-baseline (never the real law) ---
    import shutil
    from governance import lecg_constitution as K
    from governance.lecg_models import ConstitutionAmendment

    tmp_base = os.path.join(tempfile.gettempdir(), "lecg_edition_baseline")
    if os.path.exists(tmp_base):
        shutil.rmtree(tmp_base, ignore_errors=True)
    os.makedirs(tmp_base, exist_ok=True)
    for p in (K.CORES_PATH, K.SCAFFOLD_PATH, K.METHOD_PATH):
        shutil.copy(p, os.path.join(tmp_base, p.name))

    def _pending():
        return db.query(ConstitutionAmendment).filter(ConstitutionAmendment.adopted_at.is_(None)).count()

    gov_before = A.governed_constitution(db, baseline_dir=tmp_base)   # temp genesis + the pending amend
    check("one pending amendment before adoption", _pending() == 1)

    res = A.materialize_to_baseline(db, baseline_dir=tmp_base)         # bake into temp + stamp adopted
    check("adoption baked the pending amendment", res["amendments_adopted"] == 1)
    check("no pending amendments after adoption", _pending() == 0)

    gov_after = A.governed_constitution(db, baseline_dir=tmp_base)     # temp now baked + pending empty
    check("governed law identical across adoption (no double-apply)", gov_after == gov_before)
    check("adopted edition version != genesis", res["version"] != genesis)
    check("materialize version == re-assembled written baseline", res["version"] == K._version_of(K._assemble(tmp_base)))

    written = K._assemble(tmp_base)
    w01 = A._find_item(written, "tenet", "violet-01")
    check("written le-baseline carries the amended text", w01 is not None and w01["core"] == new_text)
    check("instrument genesis pin unchanged (real le-baseline untouched)", constitution_version() == genesis)

    shutil.rmtree(tmp_base, ignore_errors=True)

    # --- the amendment log surfaces the ratified motion ---
    log = A.load_amendment_log(db)
    ratified_entries = [a for a in log["amendments"] if a["status"] == "ratified"]
    check("amendment log shows the ratified motion", len(ratified_entries) >= 1)

    db.close()

    passed = sum(1 for _, ok in _checks if ok)
    for name, ok in _checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}")
    print(f"\nlecg governance self-test: {passed}/{len(_checks)}")
    print(f"genesis (instrument pin)   = {genesis}")
    print(f"governed after 1 amendment = {gov['constitution_version']}")
    return passed == len(_checks)


if __name__ == "__main__":
    ok = run()
    sys.exit(0 if ok else 1)
