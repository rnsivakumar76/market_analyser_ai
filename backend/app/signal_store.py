"""
Signal Store — DynamoDB persistence for IntradaySignals
=========================================================
Single-table pattern reusing the existing nexus-{env} table.

PK/SK layout:
  PK: SIGNAL#{symbol}
  SK: {timeframe}#{signal_type}#{bar_time}   ← dedup key (one signal per bar per direction)

GSI1 layout (query by recency):
  GSI1PK: SIGNAL
  GSI1SK: {generated_at}#{symbol}

TTL: signals auto-expire from DynamoDB 7 days after expiry.

Falls back gracefully (no-op) when DynamoDB is not configured
(local dev environment).
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from . import db as nexus_db
from .models import IntradaySignal

logger = logging.getLogger(__name__)

_SIGNAL_TTL_DAYS = 7   # keep signal records 7 days after expiry


def _to_dynamo(signal: IntradaySignal) -> dict:
    expiry_dt = datetime.fromisoformat(signal.expires_at.replace("Z", "+00:00"))
    ttl = int((expiry_dt + timedelta(days=_SIGNAL_TTL_DAYS)).timestamp())
    return {
        "PK":      f"SIGNAL#{signal.symbol}",
        "SK":      f"{signal.timeframe}#{signal.signal_type}#{signal.bar_time}",
        "GSI1PK":  "SIGNAL",
        "GSI1SK":  f"{signal.generated_at}#{signal.symbol}",
        "entity_type": "intraday_signal",
        "ttl":     ttl,
        **signal.model_dump(),
    }


def _from_dynamo(item: dict) -> IntradaySignal:
    fields = {k: v for k, v in item.items()
              if k not in ("PK", "SK", "GSI1PK", "GSI1SK", "entity_type", "ttl")}
    return IntradaySignal(**fields)


def save_signal(signal: IntradaySignal) -> bool:
    """
    Persist a new signal.  Returns True if saved, False if duplicate or DynamoDB unavailable.
    Uses condition_expression to avoid overwriting an existing signal for the same bar.
    """
    if not nexus_db.is_dynamo_enabled():
        logger.debug("[SIGNAL_STORE] DynamoDB not enabled — signal not persisted")
        return False
    try:
        table = nexus_db._get_table()
        item  = _to_dynamo(signal)
        table.put_item(
            Item=item,
            ConditionExpression="attribute_not_exists(PK)",  # dedup
        )
        logger.info(f"[SIGNAL_STORE] Saved {signal.symbol} {signal.timeframe} {signal.signal_type} bar={signal.bar_time}")
        return True
    except Exception as e:
        if "ConditionalCheckFailedException" in str(e):
            logger.debug(f"[SIGNAL_STORE] Duplicate signal skipped: {signal.symbol} {signal.timeframe} {signal.bar_time}")
        else:
            logger.warning(f"[SIGNAL_STORE] Save failed: {e}")
        return False


def get_recent_signals(limit: int = 50) -> List[IntradaySignal]:
    """
    Return most recent signals (all symbols) via GSI1, newest first.
    """
    if not nexus_db.is_dynamo_enabled():
        return []
    try:
        table = nexus_db._get_table()
        resp = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk",
            ExpressionAttributeValues={":pk": "SIGNAL"},
            ScanIndexForward=False,
            Limit=limit,
        )
        return [_from_dynamo(item) for item in resp.get("Items", [])]
    except Exception as e:
        logger.warning(f"[SIGNAL_STORE] get_recent_signals failed: {e}")
        return []


def get_signals_for_symbol(symbol: str, limit: int = 20) -> List[IntradaySignal]:
    """Return recent signals for a specific symbol."""
    if not nexus_db.is_dynamo_enabled():
        return []
    try:
        table = nexus_db._get_table()
        resp = table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": f"SIGNAL#{symbol}"},
            ScanIndexForward=False,
            Limit=limit,
        )
        return [_from_dynamo(item) for item in resp.get("Items", [])]
    except Exception as e:
        logger.warning(f"[SIGNAL_STORE] get_signals_for_symbol {symbol} failed: {e}")
        return []


def expire_old_signals() -> int:
    """
    Mark ACTIVE signals as EXPIRED if their expires_at has passed.
    Returns count of signals expired.
    Called at the start of each scan cycle.
    (DynamoDB TTL handles actual deletion — this updates the status field for UI display.)
    """
    if not nexus_db.is_dynamo_enabled():
        return 0
    try:
        table = nexus_db._get_table()
        now   = datetime.now(timezone.utc).isoformat()
        resp  = table.query(
            IndexName="GSI1",
            KeyConditionExpression="GSI1PK = :pk AND GSI1SK < :cutoff",
            ExpressionAttributeValues={":pk": "SIGNAL", ":cutoff": now + "#~"},
            Limit=100,
        )
        count = 0
        for item in resp.get("Items", []):
            if item.get("status") == "ACTIVE" and item.get("expires_at", "") < now:
                table.update_item(
                    Key={"PK": item["PK"], "SK": item["SK"]},
                    UpdateExpression="SET #s = :v",
                    ExpressionAttributeNames={"#s": "status"},
                    ExpressionAttributeValues={":v": "EXPIRED"},
                )
                count += 1
        if count:
            logger.info(f"[SIGNAL_STORE] Expired {count} old signals")
        return count
    except Exception as e:
        logger.warning(f"[SIGNAL_STORE] expire_old_signals failed: {e}")
        return 0
