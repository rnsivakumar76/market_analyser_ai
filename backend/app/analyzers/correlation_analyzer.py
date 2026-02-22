import pandas as pd
import numpy as np
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def calculate_correlations(data_map: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """
    Calculate Pearson correlation between all instruments based on the last 30 days of price changes.
    """
    if not data_map:
        return {"labels": [], "matrix": []}

    # Extract closing prices for all instruments
    price_series = {}
    for symbol, df in data_map.items():
        if len(df) >= 30:
            # Get last 30 days of percentage changes
            # We use pct_change to normalize price levels
            price_series[symbol] = df['Close'].tail(30).pct_change().dropna()

    if not price_series:
        return {"labels": [], "matrix": []}

    # Combine into a single DataFrame
    combined_df = pd.DataFrame(price_series)
    
    # Drop columns with insufficient data (though we checked tail(30))
    combined_df = combined_df.dropna(axis=1, how='all')
    
    # Calculate correlation matrix
    corr_matrix = combined_df.corr().replace({np.nan: 0})
    
    labels = corr_matrix.columns.tolist()
    matrix = corr_matrix.values.tolist()
    
    # Round values for cleaner API response
    matrix = [[round(val, 2) for val in row] for row in matrix]
    
    return {
        "labels": labels,
        "matrix": matrix
    }
