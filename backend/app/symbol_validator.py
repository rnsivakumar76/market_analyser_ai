"""
Symbol Validator
================
Validates trading symbols against supported data providers (TwelveData)
and provides suggestions for corrections when symbols are not recognized.
"""
import logging
from typing import Dict, List, Optional, Tuple
from .twelvedata_fetcher import TwelveDataFetcher

logger = logging.getLogger(__name__)

# Common symbol aliases and corrections
_SYMBOL_ALIASES: Dict[str, str] = {
    # Gold
    'GOLD': 'XAU',
    'GC': 'XAU',
    'GC=F': 'XAU',
    'GOLDUSD': 'XAU',
    
    # Silver
    'SILVER': 'XAG',
    'SI': 'XAG',
    'SI=F': 'XAG',
    'SILVERUSD': 'XAG',
    
    # Crude Oil
    'OIL': 'WTI',
    'CL': 'WTI',
    'CL=F': 'WTI',
    'CRUDE': 'WTI',
    'USOIL': 'WTI',
    'BRENT': 'BRENT',
    'BZ=F': 'BRENT',
    
    # Bitcoin
    'BITCOIN': 'BTC',
    'BTCUSD': 'BTC',
    'BTC-USD': 'BTC',
    
    # S&P 500
    'SP500': 'SPX',
    'SPY': 'SPX',
    '^GSPC': 'SPX',
    
    # US Dollar Index
    'USD': 'DXY',
    'DX': 'DXY',
    'DX-Y.NYB': 'DXY',
    
    # 10-Year Treasury Note
    'TNX': 'TNX',
    'US10Y': 'TNX',
    '^TNX': 'TNX',
}

# Extended list of commonly supported symbols by TwelveData
_SUPPORTED_SYMBOLS = {
    # Commodities
    'XAU', 'XAG', 'WTI', 'BRENT', 'NG', 'CL', 'GC', 'SI',
    
    # Forex
    'EUR/USD', 'GBP/USD', 'USD/JPY', 'USD/CHF', 'AUD/USD', 'USD/CAD',
    'EUR', 'GBP', 'JPY', 'CHF', 'AUD', 'CAD',
    
    # Crypto
    'BTC/USD', 'ETH/USD', 'BTC', 'ETH', 'LTC', 'XRP',
    
    # Indices
    'SPX', 'DJI', 'NDX', 'DXY', 'TNX', 'VIX',
    
    # ETFs (fallbacks)
    'GLD', 'SLV', 'USO', 'SPY', 'QQQ', 'IWM', 'UUP',
}


class SymbolValidator:
    """Validates symbols against data provider support."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.fetcher = TwelveDataFetcher(api_key=api_key)
    
    def normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to standard format (uppercase, remove spaces)."""
        return symbol.upper().strip()
    
    def check_alias(self, symbol: str) -> Optional[str]:
        """Check if symbol is an alias for a standard symbol."""
        normalized = self.normalize_symbol(symbol)
        return _SYMBOL_ALIASES.get(normalized)
    
    def is_predefined_supported(self, symbol: str) -> bool:
        """Check if symbol is in the predefined supported list."""
        normalized = self.normalize_symbol(symbol)
        return normalized in _SUPPORTED_SYMBOLS
    
    def validate_with_provider(self, symbol: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate symbol by attempting to fetch current price from provider.
        
        Returns:
            (is_valid, suggested_symbol, error_message)
        """
        normalized = self.normalize_symbol(symbol)
        
        # First check if it's an alias
        suggested = self.check_alias(normalized)
        if suggested:
            return (True, suggested, f"Symbol corrected from {normalized} to {suggested}")
        
        # Check predefined list
        if self.is_predefined_supported(normalized):
            return (True, normalized, None)
        
        # Try to fetch price to validate with provider
        try:
            # Map to TwelveData format
            td_symbol = self.fetcher.get_symbol_mapping(normalized)
            if not td_symbol:
                td_symbol = normalized
            
            # Try primary mapping
            price = self.fetcher._fetch_price_call(td_symbol)
            if price and price > 0:
                return (True, normalized, None)
        except Exception as e:
            logger.debug(f"Primary fetch failed for {normalized}: {e}")
        
        # Try fallback mapping
        try:
            fallback = self.fetcher.get_fallback_mapping(normalized)
            if fallback:
                price = self.fetcher._fetch_price_call(fallback)
                if price and price > 0:
                    return (True, normalized, f"Using fallback ticker {fallback}")
        except Exception as e:
            logger.debug(f"Fallback fetch failed for {normalized}: {e}")
        
        # If all failed, try to suggest similar symbols
        suggestions = self._get_similar_symbols(normalized)
        error_msg = f"Symbol {normalized} is not supported by the data provider"
        if suggestions:
            error_msg += f". Did you mean: {', '.join(suggestions[:3])}?"
        
        return (False, None, error_msg)
    
    def _get_similar_symbols(self, symbol: str) -> List[str]:
        """Get similar symbols based on string similarity."""
        normalized = self.normalize_symbol(symbol)
        similar = []
        
        for supported in _SUPPORTED_SYMBOLS:
            # Check if symbol is a substring or contains similar characters
            if normalized in supported or supported in normalized:
                similar.append(supported)
            # Check first few characters match
            if len(normalized) >= 2 and len(supported) >= 2:
                if normalized[:2] == supported[:2]:
                    similar.append(supported)
        
        return list(set(similar))[:5]  # Return top 5 unique suggestions
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of all predefined supported symbols."""
        return sorted(list(_SUPPORTED_SYMBOLS))


def validate_symbol(symbol: str, api_key: Optional[str] = None) -> Dict[str, any]:
    """
    Convenience function to validate a symbol.
    
    Returns:
        {
            'valid': bool,
            'symbol': str (normalized/corrected),
            'message': str (correction or error message),
            'suggestions': List[str] (if invalid)
        }
    """
    validator = SymbolValidator(api_key=api_key)
    normalized = validator.normalize_symbol(symbol)
    
    # Check alias first
    suggested = validator.check_alias(normalized)
    if suggested:
        return {
            'valid': True,
            'symbol': suggested,
            'message': f"Symbol corrected from {symbol} to {suggested}",
            'suggestions': []
        }
    
    # Check predefined list
    if validator.is_predefined_supported(normalized):
        return {
            'valid': True,
            'symbol': normalized,
            'message': None,
            'suggestions': []
        }
    
    # Validate with provider
    is_valid, suggested, error_msg = validator.validate_with_provider(symbol)
    
    if is_valid:
        return {
            'valid': True,
            'symbol': suggested or normalized,
            'message': error_msg,
            'suggestions': []
        }
    else:
        suggestions = validator._get_similar_symbols(symbol)
        return {
            'valid': False,
            'symbol': None,
            'message': error_msg,
            'suggestions': suggestions
        }
