"""The governance venue's own database models (lecg-).

Four tables, all in the venue's OWN DB (never a read of RC or the instrument):

  - citizens             lazily provisioned on the SHARED Clerk spine, keyed to
                         clerk_user_id (the satellite pattern from
                         LIBRA-ENGINE-ACCOUNT-ARCHITECTURE.md). The Tier-2
                         "verified human" bit is NOT a column here -- it is a
                         shared identity credential read off the Clerk identity
                         (Decision 3). This row is the venue's local profile +
                         the FK target for authorship.
  - motions              the Motion Desk (proposals about the law). Faithful
                         port of RC's motions table, re-keyed to citizens.
  - motion_arguments     the Deliberation Chamber (typed argument, 2-level).
  - constitution_amendments  the ratification WRITE-BACK ledger -- one row per
                         change the law takes by ratified motion. The forward
                         continuation of le-scaffold's genesis changelog, with
                         full provenance (which motion, before/after versions).

Shapes mirror RC's motions / motion_arguments so the Cut 2 data migration ports
rows cleanly (authors re-keyed RC user_id -> clerk_user_id -> citizens.id).
"""

from datetime import datetime

from sqlalchemy import (
    Column, DateTime, ForeignKey, Index, Integer, Text,
)
from sqlalchemy.orm import relationship

from governance.lecg_database import Base


class Citizen(Base):
    """A participant in the Libra Engine Compass, provisioned the first time a
    verified Clerk session reaches the venue. Identity is shared (one Clerk app);
    this row is the venue's LOCAL record, keyed to clerk_user_id. handle + the
    verified-human status are properties of the shared identity -- handle is
    cached here for display + author serialization; the verified bit is read live
    off the Clerk identity, never stored (Decision 3)."""
    __tablename__ = "citizens"

    id = Column(Integer, primary_key=True, autoincrement=True)
    clerk_user_id = Column(Text, nullable=False, unique=True)
    handle = Column(Text, unique=True)          # cached public pseudonym (NULL pre-onboarding)
    anon_id = Column(Text, nullable=False, unique=True)  # stable non-identifying public id
    status = Column(Text, nullable=False, default="active")  # active | suspended | banned
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    motions = relationship("Motion", back_populates="filer")
    arguments = relationship("MotionArgument", back_populates="author")


class Motion(Base):
    """A formal proposal about the constitution -- amend / add / remove a tenet,
    rule, or modifier, or a process motion. Targets the canonical constitution
    (never a song). Faithful port of RC migration 060/061."""
    __tablename__ = "motions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_type = Column(Text, nullable=False)   # amend_tenet|new_tenet|remove_tenet|amend_rule|new_rule|remove_rule|process
    target_kind = Column(Text)                   # tenet | rule | modifier | NULL
    target_ref = Column(Text)                    # e.g. 'violet-01', 'R1', 'contamination'
    claim = Column(Text, nullable=False)         # 1-line summary (<=280)
    reasoning = Column(Text, nullable=False)     # full argument (50-5000)
    citations = Column(Text)                     # JSON array of URLs (<=10)
    filed_by_citizen_id = Column(Integer, ForeignKey("citizens.id"), nullable=False)
    status = Column(Text, nullable=False, default="filed")  # filed|in_deliberation|ratified|rejected|covered
    resolution_summary = Column(Text)            # terminal summary (>=10)
    resolved_at = Column(DateTime)
    resolved_by_admin = Column(Text)             # admin username (cookie-auth, not a citizen)
    filed_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    filer = relationship("Citizen", back_populates="motions")
    arguments = relationship("MotionArgument", back_populates="motion", cascade="all, delete-orphan")
    amendments = relationship("ConstitutionAmendment", back_populates="motion")

    __table_args__ = (
        Index("idx_motions_status_filed_at", "status", "filed_at"),
        Index("idx_motions_type_status", "motion_type", "status", "filed_at"),
        Index("idx_motions_target", "target_kind", "target_ref"),
        Index("idx_motions_filed_by", "filed_by_citizen_id", "filed_at"),
    )


class MotionArgument(Base):
    """A typed post in the Deliberation Chamber. 2-level depth: top-level posts
    (parent_id NULL) plus flat rebuttals (parent_id -> a top-level post). Faithful
    port of RC migration 062."""
    __tablename__ = "motion_arguments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_id = Column(Integer, ForeignKey("motions.id", ondelete="CASCADE"), nullable=False)
    citizen_id = Column(Integer, ForeignKey("citizens.id"), nullable=False)
    post_type = Column(Text, nullable=False)     # argument_for|argument_against|rebuttal|citation|clarification
    parent_id = Column(Integer, ForeignKey("motion_arguments.id", ondelete="SET NULL"))
    summary = Column(Text, nullable=False)       # 1-280
    body = Column(Text, nullable=False)          # 50-5000
    citations = Column(Text)                     # JSON array of URLs
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    motion = relationship("Motion", back_populates="arguments")
    author = relationship("Citizen", back_populates="arguments")

    __table_args__ = (
        Index("idx_motion_arguments_motion_created", "motion_id", "created_at"),
        Index("idx_motion_arguments_motion_type", "motion_id", "post_type"),
        Index("idx_motion_arguments_parent", "parent_id"),
        Index("idx_motion_arguments_citizen", "citizen_id", "created_at"),
    )


class ConstitutionAmendment(Base):
    """The ratification WRITE-BACK ledger -- one row per change the canonical
    constitution takes. The forward continuation of le-scaffold's genesis
    changelog: where the genesis history (the founding ratification + the
    pre-Cut-2 amendments) lives verbatim in le-scaffold.json, every change from
    Cut 2 onward is a row HERE, tied to the ratified motion that forced it.

    This is the provenance spine of a governed constitution: each amendment names
    the motion, the target, the before/after item version, and the before/after
    constitution_version. The instrument adopts the new law version DELIBERATELY
    (it pins constitution_version; a ratification bumps it, the instrument adopts
    on its own clock -- the safety valve in the Integrity notes).

    motion_id is nullable so the Cut 2 data migration can carry RC's
    rubric_changes history in verbatim (Decision 5) as source_label-tagged rows
    with no originating motion in this venue."""
    __tablename__ = "constitution_amendments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    motion_id = Column(Integer, ForeignKey("motions.id"), nullable=True)
    change = Column(Text, nullable=False)        # add | amend | remove
    target_kind = Column(Text, nullable=False)   # tenet|rule|modifier|flag|note|tier|method|process
    target_ref = Column(Text)                    # the amended item id (NULL for process/method-wide)
    from_version = Column(Text)                  # the item version before (NULL for add)
    to_version = Column(Text)                    # the item version after (NULL for remove)
    summary = Column(Text, nullable=False)       # the changelog summary line
    new_core = Column(Text)                      # the new neutral law text (NULL for remove/process)
    source_label = Column(Text)                  # provenance ("motion-0042" | a carried genesis source)
    constitution_version_before = Column(Text)   # governed law version before this amendment
    constitution_version_after = Column(Text)    # governed law version after
    ratified_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    ratified_by_admin = Column(Text)             # admin who ran the ratification
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # Edition adoption (RULED 2026-06-20): adopting an edition bakes pending
    # amendments into le-baseline. adopted_at stamps when this row was baked
    # (NULL = pending, still overlaid by governed_constitution); adopted_in_version
    # records the edition that took it up.
    adopted_at = Column(DateTime)
    adopted_in_version = Column(Text)

    motion = relationship("Motion", back_populates="amendments")

    __table_args__ = (
        Index("idx_amendments_motion", "motion_id"),
        Index("idx_amendments_target", "target_kind", "target_ref"),
        Index("idx_amendments_ratified_at", "ratified_at"),
    )
