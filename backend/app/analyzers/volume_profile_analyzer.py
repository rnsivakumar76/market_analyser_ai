import pandas as pd
import numpy as np
from typing import Optional
import logging

from ..models import VolumeProfile, VolumeProfileBucket, StrategyMode

logger = logging.getLogger(__name__)


def calculate_volume_profile(
    df: pd.DataFrame,
    mode: StrategyMode = StrategyMode.LONG_TERM
) -> Optional[VolumeProfile]:
    """
    Calculate Volume Profile (POC, VAH, VAL) from OHLCV data.
    Long-term: 50 buckets over full history.
    Short-term: 20 buckets over last 20 bars.
    """
    try:
        num_buckets = 50 if mode == StrategyMode.LONG_TERM else 20
        lookback = len(df) if mode == StrategyMode.LONG_TERM else min(20, len(df))

        data = df.tail(lookback).copy()
        if len(data) < 5:
            return None

        if 'Volume' not in data.columns or data['Volume'].sum() == 0:
            return None

        price_min = data['Low'].min()
        price_max = data['High'].max()
        if price_min >= price_max:
            return None

        bucket_size = (price_max - price_min) / num_buckets
        bucket_edges = [price_min + i * bucket_size for i in range(num_buckets + 1)]

        # Distribute each candle's volume across price buckets it spans
        volume_per_bucket = np.zeros(num_buckets)
        for _, row in data.iterrows():
            low, high, vol = row['Low'], row['High'], row['Volume']
            if high <= low or vol == 0:
                continue
            for i in range(num_buckets):
                b_low = bucket_edges[i]
                b_high = bucket_edges[i + 1]
                overlap = max(0, min(high, b_high) - max(low, b_low))
                if overlap > 0:
                    volume_per_bucket[i] += vol * (overlap / (high - low))

        if volume_per_bucket.sum() == 0:
            return None

        # POC = bucket with most volume
        poc_idx = int(np.argmax(volume_per_bucket))
        poc = round(float(bucket_edges[poc_idx] + bucket_size / 2), 4)

        # VAH / VAL: value area = 70% of total volume
        total_vol = volume_per_bucket.sum()
        value_area_target = total_vol * 0.70

        # Expand from POC outward until 70% volume captured
        vah_idx = poc_idx
        val_idx = poc_idx
        captured = volume_per_bucket[poc_idx]
        sorted_remaining = sorted(
            range(num_buckets), key=lambda i: volume_per_bucket[i], reverse=True
        )

        for idx in sorted_remaining:
            if captured >= value_area_target:
                break
            if idx == poc_idx:
                continue
            if idx > vah_idx:
                vah_idx = idx
            elif idx < val_idx:
                val_idx = idx
            captured += volume_per_bucket[idx]

        vah = round(float(bucket_edges[vah_idx + 1]), 4)
        val = round(float(bucket_edges[val_idx]), 4)

        # Build bucket list for sparkline
        buckets = []
        max_vol = float(volume_per_bucket.max())
        for i in range(num_buckets):
            buckets.append(VolumeProfileBucket(
                price_low=round(float(bucket_edges[i]), 4),
                price_high=round(float(bucket_edges[i + 1]), 4),
                volume=round(float(volume_per_bucket[i]), 2),
                pct_of_max=round(float(volume_per_bucket[i] / max_vol * 100), 1) if max_vol > 0 else 0.0,
                is_poc=(i == poc_idx)
            ))

        current_price = float(data['Close'].iloc[-1])
        if current_price > vah:
            interpretation = f"Price above Value Area High (${vah:.2f}). Breakout zone — watch for continuation or rejection."
        elif current_price < val:
            interpretation = f"Price below Value Area Low (${val:.2f}). Breakdown zone — high acceptance risk below."
        else:
            interpretation = f"Price within Value Area (${val:.2f}–${vah:.2f}). Mean-reversion bias toward POC ${poc:.2f}."

        return VolumeProfile(
            poc=poc,
            vah=vah,
            val=val,
            num_buckets=num_buckets,
            buckets=buckets,
            interpretation=interpretation
        )

    except Exception as e:
        logger.error(f"Volume profile calculation failed: {e}")
        return None
