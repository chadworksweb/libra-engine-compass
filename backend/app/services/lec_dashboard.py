"""Builds the LEC admin dashboard summary -- the one JSON payload the console
page renders. Read-only over LEC's own DB + its rubric constants. LEC is
stateless about scores (it persists nothing per /api/score), so "activity" is
derived from the calibration-spend meter (claude_api_usage), whose context_json
carries each read's title/artist.
"""

import json
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.lec_config import settings
from app.lec_constants import (
    ARTIFACT_TYPE_LABELS, COLOR_BG, COLOR_HEX, COLOR_LABELS, TIER_ORDER,
)
from app.lec_database import engine
from app.lec_models import ApiClient, ApiClientKey, ClaudeApiUsage, PrecedentSong

SPEND_WINDOW_DAYS = 30
RECENT_LIMIT = 12


def _rubric_block() -> dict:
    # Imported here to avoid a circular import at module load (score imports
    # constants, dashboard imports score).
    from app.routers.lec_score import _tenet_count, rubric_version

    tiers = [
        {
            "key": k,
            "label": COLOR_LABELS[k],
            "hex": COLOR_HEX[k],
            "bg": COLOR_BG[k],
        }
        for k in TIER_ORDER
    ]
    return {
        "version": rubric_version(),
        "tenet_count": _tenet_count(),
        "tiers": tiers,
        "artifact_types": [
            {"key": k, "label": v} for k, v in ARTIFACT_TYPE_LABELS.items()
        ],
    }


def _spend_block(rows: list[ClaudeApiUsage]) -> dict:
    total_cost = sum(r.total_cost_usd or 0.0 for r in rows)
    total_calls = len(rows)
    ok_calls = sum(1 for r in rows if r.ok)
    in_tok = sum(r.input_tokens or 0 for r in rows)
    out_tok = sum(r.output_tokens or 0 for r in rows)

    # 30-day daily cost series, zero-filled so the sparkline has a fixed width.
    today = datetime.utcnow().date()
    start = today - timedelta(days=SPEND_WINDOW_DAYS - 1)
    buckets = {(start + timedelta(days=i)).isoformat(): 0.0 for i in range(SPEND_WINDOW_DAYS)}
    window_cost = 0.0
    window_calls = 0
    for r in rows:
        if not r.ts:
            continue
        d = r.ts.date()
        if d >= start:
            buckets[d.isoformat()] = buckets.get(d.isoformat(), 0.0) + (r.total_cost_usd or 0.0)
            window_cost += r.total_cost_usd or 0.0
            window_calls += 1
    series = [{"date": d, "cost": round(c, 6)} for d, c in sorted(buckets.items())]

    return {
        "total_cost_usd": round(total_cost, 4),
        "total_calls": total_calls,
        "ok_calls": ok_calls,
        "failed_calls": total_calls - ok_calls,
        "avg_cost_usd": round(total_cost / total_calls, 4) if total_calls else 0.0,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "window_days": SPEND_WINDOW_DAYS,
        "window_cost_usd": round(window_cost, 4),
        "window_calls": window_calls,
        "series": series,
    }


def _recent_block(rows: list[ClaudeApiUsage]) -> list[dict]:
    recent = sorted(rows, key=lambda r: r.ts or datetime.min, reverse=True)[:RECENT_LIMIT]
    out = []
    for r in recent:
        ctx = {}
        if r.context_json:
            try:
                ctx = json.loads(r.context_json)
            except Exception:
                ctx = {}
        out.append({
            "ts": r.ts.isoformat() if r.ts else None,
            "title": ctx.get("title"),
            "artist": ctx.get("artist"),
            "call_site": r.call_site,
            "model": r.model,
            "input_tokens": r.input_tokens,
            "output_tokens": r.output_tokens,
            "cost_usd": round(r.total_cost_usd or 0.0, 4),
            "duration_ms": r.duration_ms,
            "ok": bool(r.ok),
            "error": r.error,
        })
    return out


def _clients_block(db: Session) -> list[dict]:
    clients = db.query(ApiClient).order_by(ApiClient.created_at.asc()).all()
    out = []
    for c in clients:
        keys = []
        for k in c.keys:
            keys.append({
                "label": k.label,
                "prefix": k.key_prefix,
                "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
                "revoked": k.revoked_at is not None,
            })
        out.append({
            "slug": c.slug,
            "name": c.name,
            "status": c.status,
            "plan_tier": c.plan_tier,
            "keys": keys,
        })
    return out


def build_summary(db: Session) -> dict:
    rows = db.query(ClaudeApiUsage).all()
    return {
        "service": {
            "name": "Libra Engine Compass",
            "model": settings.agent_model,
            "db_dialect": engine.url.get_backend_name(),
            "auth_required": settings.auth_required,
            "generated_at": datetime.utcnow().isoformat(),
            # Live calibrator config -- overlaid on the pipeline map so the
            # diagram reflects the running gates, not hard-coded assumptions.
            "escalation_repass_enabled": settings.escalation_repass_enabled,
            "escalation_model": settings.escalation_model or settings.agent_model,
            "confidence_floor": settings.escalation_confidence_floor,
        },
        "rubric": _rubric_block(),
        "spend": _spend_block(rows),
        "recent": _recent_block(rows),
        "clients": _clients_block(db),
        "precedent_count": db.query(PrecedentSong).count(),
    }
