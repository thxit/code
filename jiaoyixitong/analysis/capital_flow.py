import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, List
from loguru import logger
from data.fetcher import DataFetcher
from config.settings import SystemConfig


class CapitalFlowAnalyzer:
    def __init__(self, config: SystemConfig, fetcher: DataFetcher):
        self.config = config
        self.fetcher = fetcher

    def analyze(self) -> Dict[str, Any]:
        logger.info("Analyzing capital flow")
        north_flow = self._analyze_north_flow()
        industry_flow = self._analyze_industry_flow()
        concept_flow = self._analyze_concept_flow()
        flow_summary = self._generate_flow_summary(north_flow, industry_flow)
        return {
            "north_flow": north_flow,
            "industry_flow_top": industry_flow[:10],
            "concept_flow_top": concept_flow[:10],
            "industry_flow_bottom": industry_flow[-5:] if len(industry_flow) > 5 else [],
            "summary": flow_summary,
        }

    def _analyze_north_flow(self) -> Dict[str, Any]:
        df = self.fetcher.fetch_north_flow(period=60)
        result = {"recent_days": [], "trend": "数据缺失", "cumulative_flow": 0, "signal": "未知"}

        if df is None or df.empty:
            return result

        try:
            flow_col = None
            for col in df.columns:
                if "flow" in col.lower() or "净" in col or "资金" in col:
                    flow_col = col
                    break

            if flow_col is None and len(df.columns) >= 2:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    flow_col = numeric_cols[-1]

            if flow_col:
                df[flow_col] = pd.to_numeric(df[flow_col], errors="coerce")
                recent = df.tail(5)
                result["recent_days"] = [
                    {"date": str(r["date"].date()) if "date" in df.columns else "",
                     "flow": round(float(r[flow_col]), 2) if not pd.isna(r[flow_col]) else 0}
                    for _, r in recent.iterrows()
                ]
                total = df[flow_col].sum()
                recent_sum = df[flow_col].tail(20).sum()
                result["cumulative_flow"] = round(float(total), 2) if not pd.isna(total) else 0
                result["recent_20_flow"] = round(float(recent_sum), 2) if not pd.isna(recent_sum) else 0

                if recent_sum > 100:
                    result["trend"] = "大幅净流入"
                    result["signal"] = "北向资金积极看多"
                elif recent_sum > 0:
                    result["trend"] = "小幅净流入"
                    result["signal"] = "北向资金偏多"
                elif recent_sum > -50:
                    result["trend"] = "小幅净流出"
                    result["signal"] = "北向资金偏空"
                else:
                    result["trend"] = "大幅净流出"
                    result["signal"] = "北向资金看空"
        except Exception as e:
            logger.error(f"North flow analysis error: {e}")

        return result

    def _analyze_industry_flow(self) -> List[Dict[str, Any]]:
        df = self.fetcher.fetch_industry_flow()
        return self._parse_flow_data(df)

    def _analyze_concept_flow(self) -> List[Dict[str, Any]]:
        df = self.fetcher.fetch_concept_flow()
        return self._parse_flow_data(df)

    def _parse_flow_data(self, df: Optional[pd.DataFrame]) -> List[Dict[str, Any]]:
        if df is None or df.empty:
            return []

        results = []
        try:
            name_col = None
            flow_col = None
            for col in df.columns:
                col_lower = col.lower()
                if "名称" in col or "name" in col_lower or "板块" in col or "行业" in col:
                    name_col = col
                elif "净流入" in col or "净额" in col or "flow" in col_lower or "资金" in col:
                    flow_col = col

            if name_col is None and len(df.columns) > 0:
                name_col = df.columns[0]
            if flow_col is None and len(df.columns) > 1:
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    flow_col = numeric_cols[-1]

            if name_col:
                for _, row in df.iterrows():
                    name = str(row[name_col]).strip()
                    if name == "nan" or not name:
                        continue
                    flow_val = 0
                    if flow_col:
                        try:
                            flow_val = float(row[flow_col]) / 1e8
                        except (ValueError, TypeError):
                            pass
                    results.append({"name": name, "flow_yi": round(flow_val, 2)})

            results.sort(key=lambda x: x["flow_yi"], reverse=True)
        except Exception as e:
            logger.error(f"Flow data parse error: {e}")

        return results

    def _generate_flow_summary(self, north: Dict, industry: List) -> str:
        parts = []
        north_signal = north.get("signal", "未知")
        parts.append(f"北向资金: {north_signal}")
        if industry:
            top3 = [i["name"] for i in industry[:3]]
            parts.append(f"资金流入板块: {', '.join(top3)}")
            bottom3 = [i["name"] for i in industry[-3:]]
            parts.append(f"资金流出板块: {', '.join(bottom3)}")
        return "; ".join(parts)
