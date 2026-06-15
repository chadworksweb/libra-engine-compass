"""LEC's own database models.

LEC owns three things in its own `libra_engine_compass` DB, none of which are a
read of Rising Compass:
  - service keys (`api_clients` / `api_client_keys`) -- LEC issues + verifies the
    keys its clients (RC, LT, future chargers) present on /api/score.
  - the calibration-spend meter (`claude_api_usage`) -- with correct $5/$25 Opus
    pricing (see services/claude_meter.py).
  - the precedent corpus (`precedent_songs`) -- a PROJECTION of RC's calibrated
    songs, synced from RC (the sync mechanism is a Phase 1 open item). Used only
    when /api/score is called with use_precedents=true. NOT populated yet.

Model shapes mirror RC's (api_client_keys / claude_api_usage) so an existing key
or meter row ports cleanly.
"""

from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ApiClient(Base):
    """An organization (or internal system) that consumes the LEC scoring API.

    LEC's first clients: rising-compass, lyric-transformer, and future chargers.
    `behavior` is carried for parity with RC's client model; LEC's score path is
    stateless, so it does not branch on it today.
    """
    __tablename__ = "api_clients"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(String(64), unique=True, nullable=False)
    name = Column(Text, nullable=False)
    contact_email = Column(Text)
    plan_tier = Column(String(32), default="service")
    status = Column(String(16), default="active")  # active | suspended | revoked
    behavior = Column(String(16), default="service", nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    keys = relationship("ApiClientKey", back_populates="client", cascade="all, delete-orphan")


class ApiClientKey(Base):
    """Hashed API key -- one client can have many. Raw key shown only at creation.
    LEC verifies the X-Api-Key header against key_hash here."""
    __tablename__ = "api_client_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    client_id = Column(Integer, ForeignKey("api_clients.id", ondelete="CASCADE"), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False)
    key_prefix = Column(String(12), nullable=False)
    label = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime)
    revoked_at = Column(DateTime)

    client = relationship("ApiClient", back_populates="keys")


class ClaudeApiUsage(Base):
    """One row per Anthropic messages.create() call LEC makes. Tracks OUTBOUND
    calibration spend. call_site identifies the feature ("calibrator");
    context_json captures the artifact title/artist/type so spend is attributable.
    Costs are stamped at the correct $5/$25 Opus rate by services/claude_meter.py.
    """
    __tablename__ = "claude_api_usage"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    call_site = Column(String(64), nullable=False)
    model = Column(String(64), nullable=False)
    input_tokens = Column(Integer, nullable=False, default=0)
    output_tokens = Column(Integer, nullable=False, default=0)
    cache_creation_tokens = Column(Integer, nullable=False, default=0)
    cache_read_tokens = Column(Integer, nullable=False, default=0)
    input_cost_usd = Column(Float, nullable=False, default=0.0)
    output_cost_usd = Column(Float, nullable=False, default=0.0)
    cache_creation_cost_usd = Column(Float, nullable=False, default=0.0)
    cache_read_cost_usd = Column(Float, nullable=False, default=0.0)
    total_cost_usd = Column(Float, nullable=False, default=0.0)
    duration_ms = Column(Integer)
    stop_reason = Column(String(32))
    ok = Column(Integer, nullable=False, default=1)
    error = Column(Text)
    pricing_source = Column(String(32))
    context_json = Column(Text)


class PrecedentSong(Base):
    """LEC's precedent corpus -- a PROJECTION of RC's calibrated songs, synced
    from RC (not a read of RC's DB). Carries only the fields the precedent prompt
    needs; no full lyrics. Consumed when /api/score runs with use_precedents=true
    (RC library calibrations); OFF for external artifacts (LT scoring a fresh
    lyric).

    Phase 0: the schema exists; nothing populates or reads it yet. The sync
    mechanism (one-time backfill + RC upsert-on-calibration is the leaning
    option) is a Phase 1 decision. The stateless parity path never touches this.
    """
    __tablename__ = "precedent_songs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # The originating RC songs.id -- the stable link for upsert-on-calibration.
    rc_song_id = Column(Integer, unique=True)
    title = Column(Text, nullable=False)
    artist = Column(Text)
    rubric_color = Column(String(20))
    charge_value = Column(Integer)
    charge_summary = Column(Text)
    contaminated = Column(Boolean, default=False)
    contamination_note = Column(Text)
    synced_at = Column(DateTime, default=datetime.utcnow)
