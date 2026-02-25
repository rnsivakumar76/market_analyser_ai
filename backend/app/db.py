"""
NEXUS Database Abstraction Layer (DynamoDB)
───────────────────────────────────────────
Single-table design with PK/SK pattern.

Table Schema:
    PK              SK                              Entity
    ─────────────── ─────────────────────────────── ──────────────
    USER#{user_id}  PROFILE                         User profile
    USER#{user_id}  SETTINGS                        Strategy settings
    USER#{user_id}  TRADE#{date}#{trade_id}          Trade journal entry
    USER#{user_id}  ALERT_RULE#{rule_id}             Alert rule config
    USER#{user_id}  ALERT_LOG#{timestamp}#{id}       Alert history entry
    USER#{user_id}  INSTRUMENT#{symbol}              Watched instrument
"""

import os
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Lazy DynamoDB client — only initialized when DYNAMODB_TABLE env var is set
# ──────────────────────────────────────────────────────────────────────────────

_dynamo_table = None


def _get_table():
    """Get DynamoDB table resource (lazy init)."""
    global _dynamo_table
    if _dynamo_table is None:
        import boto3
        table_name = os.environ.get('DYNAMODB_TABLE')
        if not table_name:
            raise RuntimeError("DYNAMODB_TABLE environment variable not set")
        dynamodb = boto3.resource('dynamodb')
        _dynamo_table = dynamodb.Table(table_name)
    return _dynamo_table


def is_dynamo_enabled() -> bool:
    """Check if DynamoDB is available (i.e. running on Lambda with table configured)."""
    return bool(os.environ.get('DYNAMODB_TABLE'))


# ──────────────────────────────────────────────────────────────────────────────
# Trade Journal Operations
# ──────────────────────────────────────────────────────────────────────────────

def save_trade(user_id: str, trade: dict) -> dict:
    """Save a trade journal entry to DynamoDB."""
    table = _get_table()
    trade_id = trade.get('id') or str(uuid.uuid4())
    trade_date = trade.get('date') or datetime.now(timezone.utc).strftime('%Y-%m-%d')
    created_at = trade.get('created_at') or datetime.now(timezone.utc).isoformat()

    item = {
        'PK': f"USER#{user_id}",
        'SK': f"TRADE#{trade_date}#{trade_id}",
        'GSI1PK': 'TRADE',
        'GSI1SK': f"{trade_date}#{user_id}",
        'id': trade_id,
        'created_at': created_at,
        'entity_type': 'trade',
        **{k: _convert_value(v) for k, v in trade.items() if k not in ('PK', 'SK', 'GSI1PK', 'GSI1SK')}
    }

    table.put_item(Item=item)
    logger.info(f"Saved trade {trade_id} for user {user_id}")
    return item


def get_trades(user_id: str) -> list:
    """Get all trades for a user, sorted by date."""
    table = _get_table()
    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
        ExpressionAttributeValues={
            ':pk': f"USER#{user_id}",
            ':sk_prefix': 'TRADE#'
        },
        ScanIndexForward=False  # newest first
    )
    return [_clean_item(item) for item in response.get('Items', [])]


def delete_trade(user_id: str, trade_id: str) -> bool:
    """Delete a trade by scanning for its ID."""
    table = _get_table()
    trades = get_trades(user_id)
    for trade in trades:
        if trade.get('id') == trade_id:
            table.delete_item(
                Key={
                    'PK': f"USER#{user_id}",
                    'SK': f"TRADE#{trade.get('date', '')}#{trade_id}"
                }
            )
            logger.info(f"Deleted trade {trade_id} for user {user_id}")
            return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# User Settings Operations
# ──────────────────────────────────────────────────────────────────────────────

def save_settings(user_id: str, settings: dict) -> dict:
    """Save user strategy settings."""
    table = _get_table()
    item = {
        'PK': f"USER#{user_id}",
        'SK': 'SETTINGS',
        'entity_type': 'settings',
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'data': json.dumps(settings)  # Store complex nested settings as JSON string
    }
    table.put_item(Item=item)
    logger.info(f"Saved settings for user {user_id}")
    return settings


def get_settings(user_id: str) -> Optional[dict]:
    """Get user strategy settings."""
    table = _get_table()
    response = table.get_item(
        Key={
            'PK': f"USER#{user_id}",
            'SK': 'SETTINGS'
        }
    )
    item = response.get('Item')
    if item and 'data' in item:
        return json.loads(item['data'])
    return None


# ──────────────────────────────────────────────────────────────────────────────
# User Profile Operations
# ──────────────────────────────────────────────────────────────────────────────

def save_profile(user_id: str, profile: dict) -> dict:
    """Save or update user profile."""
    table = _get_table()
    item = {
        'PK': f"USER#{user_id}",
        'SK': 'PROFILE',
        'entity_type': 'profile',
        'updated_at': datetime.now(timezone.utc).isoformat(),
        **{k: _convert_value(v) for k, v in profile.items()}
    }
    table.put_item(Item=item)
    return item


def get_profile(user_id: str) -> Optional[dict]:
    """Get user profile."""
    table = _get_table()
    response = table.get_item(
        Key={
            'PK': f"USER#{user_id}",
            'SK': 'PROFILE'
        }
    )
    return _clean_item(response.get('Item')) if response.get('Item') else None


# ──────────────────────────────────────────────────────────────────────────────
# Instrument Watchlist (future migration from S3)
# ──────────────────────────────────────────────────────────────────────────────

def save_instrument(user_id: str, symbol: str, name: str) -> dict:
    """Add an instrument to user's watchlist."""
    table = _get_table()
    item = {
        'PK': f"USER#{user_id}",
        'SK': f"INSTRUMENT#{symbol.upper()}",
        'entity_type': 'instrument',
        'symbol': symbol.upper(),
        'name': name,
        'added_at': datetime.now(timezone.utc).isoformat()
    }
    table.put_item(Item=item)
    return item


def get_instruments(user_id: str) -> list:
    """Get all instruments in user's watchlist."""
    table = _get_table()
    response = table.query(
        KeyConditionExpression='PK = :pk AND begins_with(SK, :sk_prefix)',
        ExpressionAttributeValues={
            ':pk': f"USER#{user_id}",
            ':sk_prefix': 'INSTRUMENT#'
        }
    )
    return [_clean_item(item) for item in response.get('Items', [])]


def delete_instrument(user_id: str, symbol: str) -> bool:
    """Remove an instrument from watchlist."""
    table = _get_table()
    table.delete_item(
        Key={
            'PK': f"USER#{user_id}",
            'SK': f"INSTRUMENT#{symbol.upper()}"
        }
    )
    return True


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _convert_value(value: Any) -> Any:
    """Convert Python values to DynamoDB-compatible types.
    DynamoDB doesn't support float, so convert to Decimal or string."""
    from decimal import Decimal
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _convert_value(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_convert_value(v) for v in value]
    return value


def _clean_item(item: Optional[dict]) -> Optional[dict]:
    """Clean DynamoDB item — remove PK/SK/GSI keys and convert Decimals back to float."""
    if not item:
        return None
    from decimal import Decimal
    cleaned = {}
    skip_keys = {'PK', 'SK', 'GSI1PK', 'GSI1SK', 'entity_type'}
    for k, v in item.items():
        if k in skip_keys:
            continue
        if isinstance(v, Decimal):
            cleaned[k] = float(v)
        else:
            cleaned[k] = v
    return cleaned


# ──────────────────────────────────────────────────────────────────────────────
# Analysis Cache Operations
# ──────────────────────────────────────────────────────────────────────────────

def save_analysis_results(user_id: str, results: list, mode: str) -> None:
    """Cache the full analysis results to DynamoDB."""
    table = _get_table()
    item = {
        'PK': f"USER#{user_id}",
        'SK': f"ANALYSIS#{mode.upper()}",
        'entity_type': 'analysis_cache',
        'updated_at': datetime.now(timezone.utc).isoformat(),
        'results': json.dumps(results, default=str)  # Seal the entire results list as a JSON string
    }
    table.put_item(Item=item)
    logger.info(f"Cached {len(results)} analysis results for user {user_id} ({mode})")


def get_latest_analysis_results(user_id: str, mode: str, max_age_seconds: int = 300) -> Optional[list]:
    """Retrieve cached analysis results if they are within max_age."""
    table = _get_table()
    try:
        response = table.get_item(
            Key={
                'PK': f"USER#{user_id}",
                'SK': f"ANALYSIS#{mode.upper()}"
            }
        )
        item = response.get('Item')
        if not item:
            return None
            
        updated_at_str = item['updated_at']
        # Handle ISO format with Z or +00:00
        if updated_at_str.endswith('Z'):
            updated_at_str = updated_at_str.replace('Z', '+00:00')
        updated_at = datetime.fromisoformat(updated_at_str)
        
        age = (datetime.now(timezone.utc) - updated_at).total_seconds()
        
        if age > max_age_seconds:
            logger.info(f"Analysis cache expired for {user_id} ({mode}): age={age}s")
            return None
            
        logger.info(f"Serving cached analysis for {user_id} ({mode}): age={age}s")
        return json.loads(item['results'])
    except Exception as e:
        logger.warning(f"Failed to read analysis cache: {e}")
        return None
