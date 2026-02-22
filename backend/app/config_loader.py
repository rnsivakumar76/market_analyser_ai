import yaml
from pathlib import Path
from typing import Dict, Any, List


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "instruments.yaml"
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
    """Save strategy settings back to YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "instruments.yaml"
    else:
        config_path = Path(config_path)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['strategy'] = strategy
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)


def save_instruments(instruments: List[Dict[str, str]], config_path: str = None) -> None:
    """Save instruments list back to YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config" / "instruments.yaml"
    else:
        config_path = Path(config_path)
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    config['instruments'] = instruments
    
    with open(config_path, 'w') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)
