import yaml
import os
import boto3
from pathlib import Path
from typing import Dict, Any, List
from botocore.exceptions import ClientError


S3_BUCKET = os.environ.get("CONFIG_S3_BUCKET")
CONFIG_FILE_NAME = "instruments.yaml"
LOCAL_CONFIG_PATH = Path(__file__).parent.parent / "config" / CONFIG_FILE_NAME

s3_client = boto3.client("s3")


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from S3 or local YAML file."""
    if S3_BUCKET:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=CONFIG_FILE_NAME)
            config = yaml.safe_load(response['Body'].read())
            return config
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                # If file doesn't exist in S3 yet, load local default and save it to S3
                config = _load_local_config(config_path)
                save_instruments(config.get('instruments', []), config_path)
                return config
            raise e
    
    return _load_local_config(config_path)


def _load_local_config(config_path: str = None) -> Dict[str, Any]:
    """Fallback to local filesystem for config."""
    if config_path is None:
        config_path = LOCAL_CONFIG_PATH
    else:
        config_path = Path(config_path)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config


def get_instruments(config: Dict[str, Any]) -> List[Dict[str, str]]:
    """Extract instruments list from config."""
    return config.get('instruments', [])


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


def save_strategy_config(strategy: Dict[str, Any], config_path: str = None) -> None:
    """Save strategy settings back to S3 or YAML file."""
    config = load_config(config_path)
    config['strategy'] = strategy
    _save_to_storage(config, config_path)


def save_instruments(instruments: List[Dict[str, str]], config_path: str = None) -> None:
    """Save instruments list back to S3 or YAML file."""
    config = load_config(config_path)
    config['instruments'] = instruments
    _save_to_storage(config, config_path)


def _save_to_storage(config: Dict[str, Any], config_path: str = None) -> None:
    """Internal helper to write config to S3 or Local."""
    if S3_BUCKET:
        content = yaml.dump(config, default_flow_style=False, sort_keys=False)
        s3_client.put_object(Bucket=S3_BUCKET, Key=CONFIG_FILE_NAME, Body=content)
    else:
        if config_path is None:
            config_path = LOCAL_CONFIG_PATH
        else:
            config_path = Path(config_path)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
