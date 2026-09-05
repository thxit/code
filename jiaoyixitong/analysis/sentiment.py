import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from loguru import logger
from data.fetcher import DataFetcher
from config.settings import SystemConfig


class SentimentAnalyzer:
    def __init__(self, config: SystemConfig, fetcher: DataFetcher):
        self.config = config
        self.fetcher = fetcher

    def analyze(self) -> Dict[str, Any]:
        logger.info("Analyzing market sentiment and hotspots")
        sentiment_data = self.fetcher.fetch_market_sentiment()
        limit_stats = self._analyze_limit_stats(sentiment_data)
        hot_concepts = self._analyze_hot_concepts(sentiment_data)
        sentiment_score = self._compute_sentiment_score(limit_stats)
        return {
            "limit_stats": limit_stats,
            "hot_concepts": hot_concepts,
            "sentiment_score": sentiment_score,
            "summary": self._generate_summary(limit_stats, hot_concepts, sentiment_score),
        }

    def _analyze_limit_stats(self, df: Optional[pd.DataFrame]) -> Dict[str, Any]:
        if df is None or df.empty:
            return {"limit_up": 0, "limit_down": 0, "status": "数据异常"}

        result = {}
        col_map = {}
        for col in df.columns:
            col_lower = col.lower()
            if "涨跌" in col or "涨幅" in col or "change" in col_lower:
                col_map["change_pct"] = col
            elif "名称" in col or "name" in col_lower:
                col_map["name"] = col
            elif "板块" in col or "概念" in col or "sector" in col_lower or "concept" in col_lower:
                col_map["sector"] = col

        if "change_pct" in col_map:
            try:
                pct_col = col_map["change_pct"]
                df[pct_col] = pd.to_numeric(df[pct_col], errors="coerce")
                limit_up = int((df[pct_col] >= 9.5).sum())
                limit_down = int((df[pct_col] <= -9.5).sum())
                result["limit_up_count"] = limit_up
                result["limit_down_count"] = limit_down
                result["total_count"] = len(df)
                result["limit_up_ratio"] = round(limit_up / max(len(df), 1), 3)
                result["limit_down_ratio"] = round(limit_down / max(len(df), 1), 3)

                if limit_up > 80:
                    result["status"] = "极度活跃"
                elif limit_up > 50:
                    result["status"] = "活跃"
                elif limit_up > 30:
                    result["status"] = "一般"
                elif limit_up > 10:
                    result["status"] = "低迷"
                else:
                    result["status"] = "冰点"
            except Exception as e:
                logger.error(f"Limit stats error: {e}")
                result["limit_up_count"] = 0
                result["limit_down_count"] = 0
                result["status"] = "计算失败"
        else:
            result["limit_up_count"] = 0
            result["limit_down_count"] = 0
            result["status"] = "数据格式异常"

        return result

    def _analyze_hot_concepts(self, df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        concept_counts = {}
        sector_col = None
        name_col = None
        for col in df.columns:
            col_lower = col.lower()
            if "板块" in col or "sector" in col_lower or "concept" in col_lower or "所属" in col:
                sector_col = col
            elif "名称" in col or "name" in col_lower:
                name_col = col

        if sector_col and name_col:
            try:
                for _, row in df.iterrows():
                    sector = str(row.get(sector_col, "")).strip()
                    if sector and sector != "nan":
                        concept_counts[sector] = concept_counts.get(sector, 0) + 1
            except Exception:
                pass

        hot_list = [
            {"name": k, "limit_count": v}
            for k, v in sorted(concept_counts.items(), key=lambda x: x[1], reverse=True)[:15]
        ]
        return hot_list

    def _compute_sentiment_score(self, limit_stats: Dict) -> Dict[str, Any]:
        up = limit_stats.get("limit_up_count", 0)
        down = limit_stats.get("limit_down_count", 0)
        total = limit_stats.get("total_count", 1)

        up_ratio = up / max(total, 1)
        down_ratio = down / max(total, 1)

        if up_ratio > 0.05:
            score = 80
        elif up_ratio > 0.03:
            score = 65
        elif up_ratio > 0.02:
            score = 50
        elif up_ratio > 0.01:
            score = 35
        else:
            score = 20

        if down_ratio > 0.03:
            score -= 20
        elif down_ratio > 0.01:
            score -= 10

        if down > up * 2:
            score = min(score, 20)

        score = max(0, min(100, score))

        if score >= 75:
            zone = "极度亢奋"
            suggestion = "注意追高风险，可适当参与"
        elif score >= 55:
            zone = "偏暖"
            suggestion = "短线机会较好，注意仓位"
        elif score >= 35:
            zone = "中性"
            suggestion = "控制仓位，精选个股"
        elif score >= 20:
            zone = "偏冷"
            suggestion = "减少操作，观望为主"
        else:
            zone = "冰点"
            suggestion = "空仓观望，等待机会"

        return {
            "score": score,
            "zone": zone,
            "suggestion": suggestion,
            "limit_up_count": up,
            "limit_down_count": down,
        }

    def _generate_summary(self, limit_stats: Dict, hot_concepts: List, score: Dict) -> str:
        parts = []
        parts.append(f"涨停: {limit_stats.get('limit_up_count', 0)}家, 跌停: {limit_stats.get('limit_down_count', 0)}家")
        parts.append(f"市场情绪: {score.get('zone', '未知')} (得分{score.get('score', '-')})")
        if hot_concepts:
            top3 = [c["name"] for c in hot_concepts[:3]]
            parts.append(f"热点概念: {', '.join(top3)}")
        parts.append(f"建议: {score.get('suggestion', '')}")
        return "; ".join(parts)
