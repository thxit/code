import pandas as pd
import numpy as np
from typing import Dict, Any
from config.settings import IndicatorConfig


class SentimentIndicators:
    def __init__(self, config: IndicatorConfig):
        self.config = config

    def compute_market_breadth(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"advance_count": 0, "decline_count": 0, "breadth_ratio": 0}
        df = df.copy()
        if "涨跌幅" in df.columns:
            df["change_pct"] = df["涨跌幅"]
        elif "change_pct" not in df.columns and "pct_chg" in df.columns:
            df["change_pct"] = df["pct_chg"]
        else:
            return {"advance_count": 0, "decline_count": 0, "breadth_ratio": 0}
        advance = (df["change_pct"] > 0).sum()
        decline = (df["change_pct"] < 0).sum()
        flat = (df["change_pct"] == 0).sum()
        total = len(df)
        return {
            "advance_count": int(advance),
            "decline_count": int(decline),
            "flat_count": int(flat),
            "total": total,
            "breadth_ratio": round(float(advance / max(decline, 1)), 2),
            "advance_pct": round(float(advance / total * 100), 1),
        }

    def compute_new_high_low(self, df: pd.DataFrame) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"nh_count": 0, "nl_count": 0}
        close_col = None
        for col in ["close", "收盘", "最新价"]:
            if col in df.columns:
                close_col = col
                break
        if close_col is None:
            return {"nh_count": 0, "nl_count": 0}
        df = df.copy()
        df["high_60"] = df[close_col].rolling(60).max()
        df["low_60"] = df[close_col].rolling(60).min()
        nh_count = len(df[df[close_col] >= df["high_60"].shift(1)])
        nl_count = len(df[df[close_col] <= df["low_60"].shift(1)])
        return {
            "nh_count": int(nh_count),
            "nl_count": int(nl_count),
            "nh_nl_ratio": round(float(nh_count / max(nl_count, 1)), 2),
        }

    def compute_fear_greed_index(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        score = 50.0
        details = {}
        breadth = market_data.get("breadth", {})
        adv_pct = breadth.get("advance_pct", 50)
        if adv_pct > 70:
            score += 15
            details["涨跌比"] = "贪婪"
        elif adv_pct < 30:
            score -= 15
            details["涨跌比"] = "恐惧"
        else:
            details["涨跌比"] = "中性"
        vol_ratio = market_data.get("volume_ratio", 1.0)
        if vol_ratio > 1.5:
            score += 10
            details["成交量"] = "放量"
        elif vol_ratio < 0.7:
            score -= 10
            details["成交量"] = "缩量"
        else:
            details["成交量"] = "正常"
        momentum = market_data.get("momentum_score", 0)
        score += momentum * 15
        if momentum > 0.5:
            details["动量"] = "强势"
        elif momentum < -0.5:
            details["动量"] = "弱势"
        else:
            details["动量"] = "中性"
        flow = market_data.get("capital_flow_score", 0)
        score += flow * 10
        if flow > 0:
            details["资金"] = "流入"
        else:
            details["资金"] = "流出"
        score = max(0, min(100, score))
        if score >= 75:
            zone = "极度贪婪"
        elif score >= 60:
            zone = "贪婪"
        elif score >= 40:
            zone = "中性"
        elif score >= 25:
            zone = "恐惧"
        else:
            zone = "极度恐惧"
        return {"score": round(score, 1), "zone": zone, "details": details}
