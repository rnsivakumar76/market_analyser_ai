#!/usr/bin/env python3
"""
Simple test to check if our changes work with basic imports
"""
import sys
import os

# Add the app directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

try:
    print("Testing basic imports...")
    import pandas as pd
    print("✅ pandas imported")
    
    import numpy as np
    print("✅ numpy imported")
    
    # Test our fixed modules
    from analyzers.fundamentals_analyzer import _get_forex_calendar
    print("✅ fundamentals_analyzer imported")
    
    from analyzers.pullback_warning_analyzer import analyze_pullback_warning
    print("✅ pullback_warning_analyzer imported")
    
    from analyzers.strength_analyzer import analyze_daily_strength
    print("✅ strength_analyzer imported")
    
    from main import _fetch_via_yfinance
    print("✅ main module imported")
    
    print("\n🎉 All imports successful!")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Other error: {e}")
    sys.exit(1)
