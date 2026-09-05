import pandas as pd
import numpy as np
from config.settings import IndicatorConfig


class MomentumIndicators:
    def __init__(self, config: IndicatorConfig):
        self.config = config

    def compute_all(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df = self.compute_rsi(df)
        df = self.compute_kdj(df)
        df = self.compute_wr(df)
        df = self.compute_cci(df)
        df = self.compute_mfi(df)
        df = self.compute_bias(df)
        return df

    def compute_rsi(self, df: pd.DataFrame) -> pd.DataFrame:
        period = self.config.rsi_period
        delta = df["close"].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        rs = avg_gain / avg_loss.replace(0, np.nan)
        df["RSI"] = 100 - (100 / (1 + rs))
        df["RSI_signal"] = 0
        df.loc[df["RSI"] < self.config.rsi_oversold, "RSI_signal"] = 1
        df.loc[df["RSI"] > self.config.rsi_overbought, "RSI_signal"] = -1
        df["RSI_zone"] = np.where(
            df["RSI"] < self.config.rsi_oversold, "超卖",
            np.where(df["RSI"] > self.config.rsi_overbought, "超买", "中性")
        )
        return df

    def compute_kdj(self, df: pd.DataFrame) -> pd.DataFrame:
        n, m1, m2 = self.config.kdj_n, self.config.kdj_m1, self.config.kdj_m2
        low_n = df["low"].rolling(window=n).min()
        high_n = df["high"].rolling(window=n).max()
        rsv = (df["close"] - low_n) / (high_n - low_n).replace(0, np.nan) * 100
        k = rsv.ewm(com=m1 - 1, adjust=False).mean()
        d = k.ewm(com=m2 - 1, adjust=False).mean()
        df["KDJ_K"] = k
        df["KDJ_D"] = d
        df["KDJ_J"] = 3 * k - 2 * d
        df["KDJ_signal"] = 0
        golden = (df["KDJ_K"] > df["KDJ_D"]) & (df["KDJ_K"].shift(1) <= df["KDJ_D"].shift(1))
        dead = (df["KDJ_K"] < df["KDJ_D"]) & (df["KDJ_K"].shift(1) >= df["KDJ_D"].shift(1))
        df.loc[golden & (df["KDJ_K"] < 30), "KDJ_signal"] = 2
        df.loc[golden & (df["KDJ_K"] >= 30), "KDJ_signal"] = 1
        df.loc[dead & (df["KDJ_K"] > 70), "KDJ_signal"] = -2
        df.loc[dead & (df["KDJ_K"] <= 70), "KDJ_signal"] = -1
        return df

    def compute_wr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        high_n = df["high"].rolling(window=period).max()
        low_n = df["low"].rolling(window=period).min()
        df["WR"] = (high_n - df["close"]) / (high_n - low_n).replace(0, np.nan) * 100
        df["WR_zone"] = np.where(
            df["WR"] > 80, "超卖",
            np.where(df["WR"] < 20, "超买", "中性")
        )
        return df

    def compute_cci(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        ma_tp = tp.rolling(window=period).mean()
        mad = tp.rolling(window=period).apply(lambda x: np.mean(np.abs(x - np.mean(x))), raw=True)
        df["CCI"] = (tp - ma_tp) / (0.015 * mad.replace(0, np.nan))
        df["CCI_signal"] = 0
        df.loc[df["CCI"] > 100, "CCI_signal"] = -1
        df.loc[df["CCI"] < -100, "CCI_signal"] = 1
        return df

    def compute_mfi(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        tp = (df["high"] + df["low"] + df["close"]) / 3
        money_flow = tp * df["volume"]
        positive_flow = money_flow.where(tp > tp.shift(1), 0)
        negative_flow = money_flow.where(tp < tp.shift(1), 0)
        pos_sum = positive_flow.rolling(window=period).sum()
        neg_sum = negative_flow.rolling(window=period).sum()
        mfr = pos_sum / neg_sum.replace(0, np.nan)
        df["MFI"] = 100 - (100 / (1 + mfr))
        return df

    def compute_bias(self, df: pd.DataFrame) -> pd.DataFrame:
        df["BIAS6"] = (df["close"] - df["MA5"]) / df["MA5"] * 100
        df["BIAS12"] = (df["close"] - df["MA10"]) / df["MA10"] * 100
        df["BIAS24"] = (df["close"] - df["MA20"]) / df["MA20"] * 100
        return df
