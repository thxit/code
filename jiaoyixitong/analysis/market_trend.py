import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from loguru import logger
from data.fetcher import DataFetcher
from indicators.trend import TrendIndicators
from indicators.momentum import MomentumIndicators
from indicators.volume import VolumeIndicators
from config.settings import SystemConfig



class MarketTrendAnalyzer:
    def __init__(self, config: SystemConfig, fetcher: DataFetcher):
        self.config = config
        self.fetcher = fetcher
        self.trend_ind = TrendIndicators(config.indicator)
        self.momentum_ind = MomentumIndicators(config.indicator)
        self.volume_ind = VolumeIndicators(config.indicator)

    def analyze(self, index_code: str = "000001", period: int = 250) -> Dict[str, Any]:
        logger.info(f"Analyzing market trend for {index_code}")
        df = self.fetcher.fetch_index_daily(index_code, period=period)
        if df is None or df.empty:
            return {"error": f"No data for index {index_code}"}

        df = self.trend_ind.compute_all(df)
        df = self.momentum_ind.compute_all(df)
        df = self.volume_ind.compute_all(df)
        df = self.volume_ind.compute_atr(df)

        latest = df.iloc[-1]
        result = {
            "index_code": index_code,
            "index_name": self.config.market.index_names.get(index_code, index_code),
            "current_price": round(float(latest["close"]), 2),
            "date": str(latest["date"].date()),
            "trend": self._analyze_trend(df, latest),
            "momentum": self._analyze_momentum(df, latest),
            "volume": self._analyze_volume(df, latest),
            "volatility": self._analyze_volatility(df),
            "support_resistance": self._find_support_resistance(df),
            "daily_stats": self._daily_stats(df, latest),
            "overall_score": 0.0,
            "overall_signal": "观望",
            "summary": ""
        }
        result["overall_score"] = self._compute_overall_score(result)
        result["overall_signal"] = self._get_signal_label(result["overall_score"])
        result["summary"] = self._generate_summary(result)

        tail_rows = min(120, len(df))
        raw_cols = ["date", "close", "MA5", "MA10", "MA20", "MA60",
                    "MACD_DIF", "MACD_DEA", "MACD_HIST", "RSI",
                    "KDJ_K", "KDJ_D", "KDJ_J", "BOLL_UP", "BOLL_MID", "BOLL_DN", "volume"]
        result["_raw_df"] = df[raw_cols].tail(tail_rows).to_dict(orient="records")
        for r in result["_raw_df"]:
            r["date"] = str(r["date"].date()) if hasattr(r["date"], "date") else str(r["date"])
            for k, v in r.items():
                if k != "date" and v is not None and not isinstance(v, str):
                    r[k] = round(float(v), 4) if not (isinstance(v, float) and (v != v)) else None
        return result

    def _analyze_trend(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        analysis = {}
        analysis["MA5"] = round(float(latest.get("MA5", np.nan)), 2)
        analysis["MA10"] = round(float(latest.get("MA10", np.nan)), 2)
        analysis["MA20"] = round(float(latest.get("MA20", np.nan)), 2)
        analysis["MA60"] = round(float(latest.get("MA60", np.nan)), 2)
        analysis["MA120"] = round(float(latest.get("MA120", np.nan)), 2)
        analysis["MA250"] = round(float(latest.get("MA250", np.nan)), 2)

        ma_desc = []
        if latest["close"] > analysis["MA5"]:
            ma_desc.append("站上5日线")
        if latest["close"] > analysis["MA20"]:
            ma_desc.append("站上20日线")
        if latest["close"] > analysis["MA60"]:
            ma_desc.append("站上60日线")
        if not ma_desc:
            ma_desc.append("位于主要均线下方")

        ma_alignment = []
        if analysis["MA5"] > analysis["MA10"]:
            ma_alignment.append("短线多头排列")
        if analysis["MA10"] > analysis["MA20"]:
            ma_alignment.append("中线多头排列")
        if analysis["MA20"] > analysis["MA60"]:
            ma_alignment.append("长线多头排列")

        analysis["alignment_score"] = latest.get("MA_score", 0)
        analysis["description"] = "; ".join(ma_desc)
        analysis["alignment"] = "; ".join(ma_alignment) if ma_alignment else "均线空头排列"

        macd = {}
        macd["DIF"] = round(float(latest.get("MACD_DIF", np.nan)), 4)
        macd["DEA"] = round(float(latest.get("MACD_DEA", np.nan)), 4)
        macd["HIST"] = round(float(latest.get("MACD_HIST", np.nan)), 4)
        macd["signal"] = int(latest.get("MACD_signal", 0))
        if macd["signal"] == 1:
            macd["status"] = "金叉"
        elif macd["signal"] == -1:
            macd["status"] = "死叉"
        elif macd["DIF"] > macd["DEA"]:
            macd["status"] = "多头区域"
        else:
            macd["status"] = "空头区域"
        analysis["MACD"] = macd

        boll = {}
        boll["UP"] = round(float(latest.get("BOLL_UP", np.nan)), 2)
        boll["MID"] = round(float(latest.get("BOLL_MID", np.nan)), 2)
        boll["DN"] = round(float(latest.get("BOLL_DN", np.nan)), 2)
        boll["width"] = round(float(latest.get("BOLL_WIDTH", np.nan)), 2)
        boll["position"] = round(float(latest.get("BOLL_position", 0.5)), 2)
        if boll["position"] > 0.8:
            boll["zone"] = "上轨附近（超买）"
        elif boll["position"] < 0.2:
            boll["zone"] = "下轨附近（超卖）"
        elif boll["position"] > 0.5:
            boll["zone"] = "中上轨"
        else:
            boll["zone"] = "中下轨"
        analysis["BOLL"] = boll

        adx_val = float(latest.get("ADX", np.nan))
        analysis["ADX"] = round(adx_val, 2)
        analysis["ADX_strength"] = latest.get("ADX_strength", "未知")
        analysis["ADX_direction"] = "上涨" if latest.get("ADX_PDI", 0) > latest.get("ADX_MDI", 0) else "下跌"

        return analysis

    def _analyze_momentum(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        analysis = {}
        analysis["RSI"] = round(float(latest.get("RSI", 50)), 1)
        analysis["RSI_zone"] = latest.get("RSI_zone", "中性")
        kdj = {}
        kdj["K"] = round(float(latest.get("KDJ_K", 50)), 1)
        kdj["D"] = round(float(latest.get("KDJ_D", 50)), 1)
        kdj["J"] = round(float(latest.get("KDJ_J", 50)), 1)
        kdj["signal"] = int(latest.get("KDJ_signal", 0))
        if kdj["signal"] >= 2:
            kdj["status"] = "低位金叉（强买）"
        elif kdj["signal"] == 1:
            kdj["status"] = "金叉"
        elif kdj["signal"] <= -2:
            kdj["status"] = "高位死叉（强卖）"
        elif kdj["signal"] == -1:
            kdj["status"] = "死叉"
        else:
            kdj["status"] = "中性"
        analysis["KDJ"] = kdj
        analysis["WR"] = round(float(latest.get("WR", 50)), 1)
        analysis["CCI"] = round(float(latest.get("CCI", 0)), 1)
        analysis["MFI"] = round(float(latest.get("MFI", 50)), 1)
        df_len = len(df)
        chg_5d = (latest["close"] / df["close"].iloc[max(0, df_len - 6)] - 1) * 100 if df_len > 5 else 0
        chg_10d = (latest["close"] / df["close"].iloc[max(0, df_len - 11)] - 1) * 100 if df_len > 10 else 0
        chg_20d = (latest["close"] / df["close"].iloc[max(0, df_len - 21)] - 1) * 100 if df_len > 20 else 0
        analysis["change_5d"] = round(chg_5d, 2)
        analysis["change_10d"] = round(chg_10d, 2)
        analysis["change_20d"] = round(chg_20d, 2)
        return analysis

    def _analyze_volume(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        analysis = {}
        analysis["current_volume"] = int(latest["volume"])
        analysis["VOL_MA5"] = round(float(latest.get("VOL_MA5", 0)), 0)
        analysis["VOL_MA20"] = round(float(latest.get("VOL_MA20", 0)), 0)
        analysis["volume_ratio"] = round(float(latest.get("VOL_RATIO", 1.0)), 2)
        analysis["volume_zone"] = latest.get("VOL_RATIO_zone", "正常")
        analysis["OBV_divergence"] = int(latest.get("OBV_divergence", 0))
        if analysis["OBV_divergence"] == 1:
            analysis["OBV_signal"] = "底背离（看涨）"
        elif analysis["OBV_divergence"] == -1:
            analysis["OBV_signal"] = "顶背离（看跌）"
        else:
            analysis["OBV_signal"] = "无背离"

        recent_vol = df["volume"].tail(5)
        vol_trend = "放量" if recent_vol.iloc[-1] > recent_vol.mean() else "缩量"
        analysis["volume_trend"] = vol_trend
        return analysis

    def _analyze_volatility(self, df: pd.DataFrame) -> Dict[str, Any]:
        latest = df.iloc[-1]
        atr = float(latest.get("ATR", 0))
        atr_pct = float(latest.get("ATR_pct", 0))
        recent = df.tail(20)
        daily_range = ((recent["high"] - recent["low"]) / recent["close"] * 100).mean()
        return {
            "ATR": round(atr, 2),
            "ATR_pct": round(atr_pct, 2),
            "avg_daily_range": round(float(daily_range), 2),
            "volatility_level": "高波动" if atr_pct > 2 else ("中波动" if atr_pct > 1 else "低波动"),
        }

    def _find_support_resistance(self, df: pd.DataFrame) -> Dict[str, Any]:
        latest = df.iloc[-1]
        close_val = float(latest["close"])
        support = None
        resistance = None
        if "MA60" in latest and not pd.isna(latest["MA60"]):
            ma60 = float(latest["MA60"])
            if ma60 < close_val:
                support = ma60
            else:
                resistance = ma60
        if "MA20" in latest and not pd.isna(latest["MA20"]):
            ma20 = float(latest["MA20"])
            if ma20 < close_val:
                support = ma20
            else:
                resistance = ma20
        if "BOLL_DN" in latest and not pd.isna(latest["BOLL_DN"]):
            if support is None or float(latest["BOLL_DN"]) > support:
                support = float(latest["BOLL_DN"])
        if "BOLL_UP" in latest and not pd.isna(latest["BOLL_UP"]):
            if resistance is None or float(latest["BOLL_UP"]) < resistance:
                resistance = float(latest["BOLL_UP"])
        return {
            "support": round(support, 2) if support else None,
            "resistance": round(resistance, 2) if resistance else None,
            "current_distance_to_support": round((close_val - support) / close_val * 100, 2) if support else None,
            "current_distance_to_resistance": round((resistance - close_val) / close_val * 100, 2) if resistance else None,
        }

    def _daily_stats(self, df: pd.DataFrame, latest: pd.Series) -> Dict[str, Any]:
        change = float(latest["close"] - latest["open"])
        change_pct = (float(latest["close"]) / float(latest["open"]) - 1) * 100
        return {
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "high": round(float(latest["high"]), 2),
            "low": round(float(latest["low"]), 2),
        }

    def _compute_overall_score(self, result: Dict[str, Any]) -> float:
        score = 0.0
        trend = result["trend"]
        if trend["MA5"] > trend["MA20"]:
            score += 0.2
        if trend["MA10"] > trend["MA20"]:
            score += 0.15
        if trend["MA20"] > trend["MA60"]:
            score += 0.15
        macd = trend["MACD"]
        if macd["signal"] == 1:
            score += 0.15
        elif macd["DIF"] > macd["DEA"]:
            score += 0.08
        else:
            score -= 0.1
        if macd["HIST"] > 0:
            score += 0.05
        momentum = result["momentum"]
        rsi = momentum["RSI"]
        if 40 <= rsi <= 60:
            score += 0.05
        elif 30 <= rsi < 40:
            score += 0.08
        elif rsi < 30:
            score += 0.1
        elif 60 < rsi <= 70:
            score -= 0.05
        elif rsi > 70:
            score -= 0.1
        kdj = momentum["KDJ"]
        if kdj["signal"] >= 2:
            score += 0.1
        elif kdj["signal"] <= -2:
            score -= 0.1
        if momentum["change_5d"] > 0:
            score += 0.05
        volume = result["volume"]
        if volume["volume_ratio"] > 1.2:
            score += 0.1 if volume["volume_ratio"] < 2.0 else 0.05
        elif volume["volume_ratio"] < 0.7:
            score -= 0.05
        boll = trend["BOLL"]
        if boll["position"] < 0.2:
            score += 0.05
        elif boll["position"] > 0.8:
            score -= 0.05
        if trend["ADX"] > 25 and trend["ADX_direction"] == "上涨":
            score += 0.1
        elif trend["ADX"] > 25 and trend["ADX_direction"] == "下跌":
            score -= 0.05

        return round(max(-1.0, min(1.0, score)), 2)

    def _get_signal_label(self, score: float) -> str:
        if score >= 0.6:
            return "强烈看多"
        elif score >= 0.3:
            return "看多"
        elif score >= -0.2:
            return "观望"
        elif score >= -0.5:
            return "看空"
        else:
            return "强烈看空"

    def _generate_summary(self, result: Dict[str, Any]) -> str:
        parts = []
        trend = result["trend"]
        parts.append(f"趋势均线: {trend['description']}")
        parts.append(f"MACD状态: {trend['MACD']['status']}")
        parts.append(f"布林带: {trend['BOLL']['zone']}")
        momentum = result["momentum"]
        parts.append(f"RSI({momentum['RSI']}): {momentum['RSI_zone']}")
        parts.append(f"KDJ: {momentum['KDJ']['status']}")
        vol = result["volume"]
        parts.append(f"量能: {vol['volume_zone']}({vol['volume_ratio']}倍)")
        parts.append(f"5日涨幅: {momentum['change_5d']}%")
        return "; ".join(parts)
