import pandas as pd
import numpy as np
from config.settings import IndicatorConfig


class VolumeIndicators:
    def __init__(self, config: IndicatorConfig):
        self.config = config

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self.compute_volume_ma(df)
        df = self.compute_volume_ratio(df)
        df = self.compute_obv(df)
        df = self.compute_vwap(df)
        df = self.compute_volume_price_trend(df)
        df = self.compute_volume_breakout(df)
        return df

    def compute_volume_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.config.volume_ma_period
        df["VOL_MA5"] = df["volume"].rolling(window=5).mean()
        df["VOL_MA10"] = df["volume"].rolling(window=10).mean()
        df["VOL_MA20"] = df["volume"].rolling(window=period).mean()
        df["VOL_trend"] = np.where(df["VOL_MA5"] > df["VOL_MA10"], 1, -1)
        return df

    def compute_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        df["VOL_RATIO"] = df["volume"] / df["VOL_MA20"].replace(0, np.nan)
        df["VOL_RATIO_zone"] = np.where(
            df["VOL_RATIO"] > 2.0, "放量",
            np.where(df["VOL_RATIO"] > 1.5, "温和放量",
                     np.where(df["VOL_RATIO"] < 0.5, "地量", "正常"))
        )
        return df

    def compute_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        df["price_dir"] = np.sign(df["close"].diff().fillna(0))
        df["OBV"] = (df["volume"] * df["price_dir"]).cumsum()
        df["OBV_MA"] = df["OBV"].rolling(window=20).mean()
        df["OBV_divergence"] = 0
        price_rising = df["close"] > df["close"].shift(5)
        obv_falling = df["OBV"] < df["OBV"].shift(5)
        df.loc[price_rising & obv_falling, "OBV_divergence"] = -1
        price_falling = df["close"] < df["close"].shift(5)
        obv_rising = df["OBV"] > df["OBV"].shift(5)
        df.loc[price_falling & obv_rising, "OBV_divergence"] = 1
        return df

    def compute_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        if "amount" in df.columns:
            df["VWAP"] = df["amount"].cumsum() / df["volume"].cumsum().replace(0, np.nan)
            df["VWAP_deviation"] = (df["close"] - df["VWAP"]) / df["VWAP"] * 100
        return df

    def compute_volume_price_trend(self, df: pd.DataFrame) -> pd.DataFrame:
        price_change_pct = df["close"].pct_change()
        df["VPT"] = (df["volume"] * price_change_pct).cumsum()
        df["VPT_MA"] = df["VPT"].rolling(window=20).mean()
        return df

    def compute_volume_breakout(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        df["VOL_MAX20"] = df["volume"].rolling(window=lookback).max()
        df["VOL_breakout"] = df["volume"] >= df["VOL_MAX20"].shift(1)
        return df

    def compute_atr(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.config.atr_period
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.DataFrame({
            "hl": high - low,
            "hc": abs(high - close.shift(1)),
            "lc": abs(low - close.shift(1))
        }).max(axis=1)
        df["ATR"] = tr.rolling(window=period).mean()
        df["ATR_pct"] = df["ATR"] / df["close"] * 100
        return df
