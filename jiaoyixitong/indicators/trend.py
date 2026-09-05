import pandas as pd
import numpy as np
from typing import Tuple, Dict, Any
from config.settings import IndicatorConfig


class TrendIndicators:
    def __init__(self, config: IndicatorConfig):
        self.config = config

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self.compute_ma(df)
        df = self.compute_ema(df)
        df = self.compute_macd(df)
        df = self.compute_bollinger(df)
        df = self.compute_adx(df)
        df = self.compute_trix(df)
        return df

    def compute_ma(self, df: pd.DataFrame) -> pd.DataFrame:
        for p in self.config.ma_periods:
            df[f"MA{p}"] = df["close"].rolling(window=p).mean()
        df["MA_score"] = self._ma_alignment_score(df)
        return df

    def _ma_alignment_score(self, df: pd.DataFrame) -> pd.Series:
        short_ma = df[f"MA{self.config.ma_short}"]
        long_ma = df[f"MA{self.config.ma_long}"]
        ma_diff = (short_ma - long_ma) / long_ma * 100
        score = pd.Series(0.0, index=df.index)
        score[ma_diff > 1] = 2
        score[(ma_diff > 0) & (ma_diff <= 1)] = 1
        score[(ma_diff < 0) & (ma_diff >= -1)] = -1
        score[ma_diff < -1] = -2
        return score

    def compute_ema(self, df: pd.DataFrame) -> pd.DataFrame:
        df["EMA12"] = df["close"].ewm(span=12, adjust=False).mean()
        df["EMA26"] = df["close"].ewm(span=26, adjust=False).mean()
        df["EMA50"] = df["close"].ewm(span=50, adjust=False).mean()
        return df

    def compute_macd(self, df: pd.DataFrame) -> pd.DataFrame:
        fast = self.config.macd_fast
        slow = self.config.macd_slow
        sig = self.config.macd_signal
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
        df["MACD_DIF"] = ema_fast - ema_slow
        df["MACD_DEA"] = df["MACD_DIF"].ewm(span=sig, adjust=False).mean()
        df["MACD_HIST"] = (df["MACD_DIF"] - df["MACD_DEA"]) * 2
        df["MACD_signal"] = 0
        golden = (df["MACD_DIF"] > df["MACD_DEA"]) & (df["MACD_DIF"].shift(1) <= df["MACD_DEA"].shift(1))
        dead = (df["MACD_DIF"] < df["MACD_DEA"]) & (df["MACD_DIF"].shift(1) >= df["MACD_DEA"].shift(1))
        df.loc[golden, "MACD_signal"] = 1
        df.loc[dead, "MACD_signal"] = -1
        df["MACD_trend"] = np.where(df["MACD_HIST"] > df["MACD_HIST"].shift(1), 1, -1)
        return df

    def compute_bollinger(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.config.boll_period
        std = self.config.boll_std
        df["BOLL_MID"] = df["close"].rolling(window=period).mean()
        rolling_std = df["close"].rolling(window=period).std()
        df["BOLL_UP"] = df["BOLL_MID"] + std * rolling_std
        df["BOLL_DN"] = df["BOLL_MID"] - std * rolling_std
        df["BOLL_WIDTH"] = (df["BOLL_UP"] - df["BOLL_DN"]) / df["BOLL_MID"] * 100
        df["BOLL_position"] = (df["close"] - df["BOLL_DN"]) / (df["BOLL_UP"] - df["BOLL_DN"])
        return df

    def compute_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high, low, close = df["high"], df["low"], df["close"]
        tr = pd.DataFrame({
            "hl": high - low,
            "hc": abs(high - close.shift(1)),
            "lc": abs(low - close.shift(1))
        }).max(axis=1)
        atr = tr.rolling(window=period).mean()
        up_move = high - high.shift(1)
        down_move = low.shift(1) - low
        plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
        minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
        plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr.replace(0, np.nan)
        minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr.replace(0, np.nan)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)
        df["ADX"] = dx.rolling(window=period).mean()
        df["ADX_PDI"] = plus_di
        df["ADX_MDI"] = minus_di
        df["ADX_trend"] = np.where(df["ADX_PDI"] > df["ADX_MDI"], 1, -1)
        df["ADX_strength"] = np.where(df["ADX"] > 25, "强趋势", np.where(df["ADX"] > 20, "中等趋势", "弱趋势"))
        return df

    def compute_trix(self, df: pd.DataFrame, period: int = 15) -> pd.DataFrame:
        ema1 = df["close"].ewm(span=period, adjust=False).mean()
        ema2 = ema1.ewm(span=period, adjust=False).mean()
        ema3 = ema2.ewm(span=period, adjust=False).mean()
        df["TRIX"] = ema3.pct_change() * 100
        df["TRIX_MA"] = df["TRIX"].rolling(window=9).mean()
        return df
