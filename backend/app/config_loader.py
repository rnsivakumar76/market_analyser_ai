import yaml
import os
import boto3
from pathlib import Path
from typing import Dict, Any, List
from botocore.exceptions import ClientError


S3_BUCKET = os.environ.get("CONFIG_S3_BUCKET")
CONFIG_FILE_NAME = "instruments.yaml"
LOCAL_CONFIG_DIR = Path(__file__).parent.parent / "config"
DEFAULT_USER_ID = "global_default"

_s3_client = None

def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3")
    return _s3_client


def _get_config_key(user_id: str) -> str:
    """Helper to get the storage key for a specific user."""
    return f"users/{user_id}/{CONFIG_FILE_NAME}"


def load_config(user_id: str = DEFAULT_USER_ID, config_path: str = None) -> Dict[str, Any]:
    """Load configuration from S3 or local YAML file for a specific user."""
    if S3_BUCKET:
        key = _get_config_key(user_id)
        try:
            response = get_s3_client().get_object(Bucket=S3_BUCKET, Key=key)
            config = yaml.safe_load(response['Body'].read())
            return config
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # If file doesn't exist for this user in S3 yet, load global default and save it to S3
                config = _load_local_config(user_id, config_path)
                _save_to_storage(config, user_id, config_path)
                return config
            raise e
    
    return _load_local_config(user_id, config_path)


def _load_local_config(user_id: str = DEFAULT_USER_ID, config_path: str = None) -> Dict[str, Any]:
    """Fallback to local filesystem for config, now user-aware."""
    if config_path is None:
        # Use user-specific filename locally too
        config_path = LOCAL_CONFIG_DIR / f"{user_id}_{CONFIG_FILE_NAME}"
        # If user specific doesn't exist, try global default
        if not config_path.exists():
            config_path = LOCAL_CONFIG_DIR / CONFIG_FILE_NAME
    else:
        config_path = Path(config_path)
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        # Final fallback if nothing exists
        return {"instruments": [], "strategy": {}, "alerts": {}}


ALLOWED_SYMBOLS = {'XAU', 'XAG', 'WTI', 'SPX', 'BTC'}

def get_instruments(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract instruments list from config, strictly filtered to the allowed 5."""
    instruments = config.get('instruments', [])
    return [inst for inst in instruments if inst.get('symbol', '').upper() in ALLOWED_SYMBOLS]


def get_analysis_params(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract analysis parameters from config."""
    return config.get('analysis', {})


def get_alert_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract alert settings from config."""
    return config.get('alerts', {})


def get_strategy_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Extract strategy settings from config."""
    return config.get('strategy', {
        "conviction_threshold": 70,
        "adx_threshold": 25,
        "atr_multiplier_tp": 3.0,
        "atr_multiplier_sl": 1.5,
        "portfolio_value": 10000.0,
        "risk_per_trade_percent": 1.0
    })


def save_strategy_config(strategy: Dict[str, Any], user_id: str = DEFAULT_USER_ID, config_path: str = None) -> None:
    """Save strategy settings back to S3 or YAML file for a user."""
    config = load_config(user_id, config_path)
    config['strategy'] = strategy
    _save_to_storage(config, user_id, config_path)


def save_instruments(instruments: List[Dict[str, str]], user_id: str = DEFAULT_USER_ID, config_path: str = None) -> None:
    """Save instruments list back to S3 or YAML file for a user."""
    config = load_config(user_id, config_path)
    config['instruments'] = instruments
    _save_to_storage(config, user_id, config_path)


def _save_to_storage(config: Dict[str, Any], user_id: str = DEFAULT_USER_ID, config_path: str = None) -> None:
    """Internal helper to write config to S3 or Local, now user-aware."""
    if S3_BUCKET:
        key = _get_config_key(user_id)
        content = yaml.dump(config, default_flow_style=False, sort_keys=False)
        get_s3_client().put_object(Bucket=S3_BUCKET, Key=key, Body=content)
    else:
        if config_path is None:
            config_path = LOCAL_CONFIG_DIR / f"{user_id}_{CONFIG_FILE_NAME}"
        else:
            config_path = Path(config_path)
        
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
