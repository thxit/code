import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from config.settings import StockScreeningConfig


class StockFilters:
    def __init__(self, config: StockScreeningConfig):
        self.config = config

    def filter_volume_ratio(self, df: pd.DataFrame) -> pd.DataFrame:
        vol_col = self._find_col(df, ["量比", "volume_ratio", "vol_ratio"])
        if vol_col:
            df[vol_col] = pd.to_numeric(df[vol_col], errors="coerce")
            return df[df[vol_col] >= self.config.min_volume_ratio]
        return df

    def filter_price_range(self, df: pd.DataFrame) -> pd.DataFrame:
        price_col = self._find_col(df, ["最新价", "close", "price"])
        if price_col:
            df[price_col] = pd.to_numeric(df[price_col], errors="coerce")
            df = df[df[price_col] >= self.config.min_price]
            df = df[df[price_col] <= self.config.max_price]
        return df

    def filter_change_range(self, df: pd.DataFrame) -> pd.DataFrame:
        chg_col = self._find_col(df, ["涨跌幅", "change_pct", "pct_chg"])
        if chg_col:
            df[chg_col] = pd.to_numeric(df[chg_col], errors="coerce")
            df = df[df[chg_col] >= self.config.min_change_pct]
            df = df[df[chg_col] <= self.config.max_change_pct]
        return df

    def filter_pe_range(self, df: pd.DataFrame) -> pd.DataFrame:
        pe_col = self._find_col(df, ["市盈率-动态", "pe", "pe_ttm", "市盈率"])
        if pe_col:
            df[pe_col] = pd.to_numeric(df[pe_col], errors="coerce")
            lo, hi = self.config.pe_range
            df = df[(df[pe_col] >= lo) & (df[pe_col] <= hi)]
        return df

    def filter_pb_range(self, df: pd.DataFrame) -> pd.DataFrame:
        pb_col = self._find_col(df, ["市净率", "pb", "pb_mrq"])
        if pb_col:
            df[pb_col] = pd.to_numeric(df[pb_col], errors="coerce")
            lo, hi = self.config.pb_range
            df = df[(df[pb_col] >= lo) & (df[pb_col] <= hi)]
        return df

    def filter_market_cap(self, df: pd.DataFrame) -> pd.DataFrame:
        cap_col = self._find_col(df, ["总市值", "market_cap", "market_capitalization"])
        if cap_col:
            df[cap_col] = pd.to_numeric(df[cap_col], errors="coerce")
            df = df[df[cap_col] >= self.config.min_market_cap]
        return df

    def filter_st_remove(self, df: pd.DataFrame) -> pd.DataFrame:
        name_col = self._find_col(df, ["名称", "name", "股票名称"])
        if name_col:
            df = df[~df[name_col].str.contains("ST|退市|\\*ST", na=False)]
        return df

    def filter_new_stock(self, df: pd.DataFrame) -> pd.DataFrame:
        code_col = self._find_col(df, ["代码", "code", "symbol"])
        if code_col:
            df = df[~df[code_col].str.contains("^3|^688", na=False)]
        return df

    def _find_col(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        for c in candidates:
            if c in df.columns:
                return c
        return None


class StockSelector:
    def __init__(self, fetch_func):
        self.fetcher = fetch_func
        self.filters = StockFilters(StockScreeningConfig())

    def screen(self, top_n: int = 20) -> List[Dict[str, Any]]:
        df = self.fetcher()
        if df is None or df.empty:
            return []

        df = df.copy()
        df = self.filters.filter_st_remove(df)
        df = self.filters.filter_new_stock(df)
        df = self.filters.filter_price_range(df)
        df = self.filters.filter_change_range(df)
        df = self.filters.filter_volume_ratio(df)
        df = self.filters.filter_pe_range(df)
        df = self.filters.filter_pb_range(df)
        df = self.filters.filter_market_cap(df)

        scored_df = self._score_stocks(df)
        top = scored_df.head(top_n)

        results = []
        for _, row in top.iterrows():
            stock = self._extract_stock_info(row)
            results.append(stock)

        return results

    def _score_stocks(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["_score"] = 0.0

        chg_col = self.filters._find_col(df, ["涨跌幅", "change_pct", "pct_chg"])
        if chg_col:
            df[chg_col] = pd.to_numeric(df[chg_col], errors="coerce")
            df["_score"] += (df[chg_col] / 10).clip(-0.3, 0.3) * 0.3

        vol_col = self.filters._find_col(df, ["量比", "volume_ratio", "vol_ratio"])
        if vol_col:
            df[vol_col] = pd.to_numeric(df[vol_col], errors="coerce")
            df["_score"] += np.log1p(df[vol_col].clip(0.5, 10)) * 0.2

        turn_col = self.filters._find_col(df, ["换手率", "turnover_rate", "turnover"])
        if turn_col:
            df[turn_col] = pd.to_numeric(df[turn_col], errors="coerce")
            df["_score"] += (df[turn_col] / 10).clip(0, 0.5) * 0.15

        amt_col = self.filters._find_col(df, ["成交额", "amount", "成交金额"])
        if amt_col:
            df[amt_col] = pd.to_numeric(df[amt_col], errors="coerce")
            if amt_col:
                median_amt = df[amt_col].median()
                if median_amt > 0:
                    df["_score"] += np.log1p(df[amt_col] / median_amt).clip(0, 2) * 0.1

        return df.sort_values("_score", ascending=False)

    def screen_by_strategy(self, strategy: str = "breakout", top_n: int = 10) -> List[Dict[str, Any]]:
        results = self.screen(top_n=50)
        if not results:
            return []

        if strategy == "breakout":
            return [s for s in results if s.get("score", 0) > 0.5][:top_n]
        elif strategy == "momentum":
            results.sort(key=lambda x: x.get("change_pct", 0), reverse=True)
            return results[:top_n]
        elif strategy == "volume_breakout":
            results.sort(key=lambda x: x.get("volume_ratio", 0), reverse=True)
            return results[:top_n]
        elif strategy == "oversold_reversal":
            return [s for s in results if s.get("change_pct", 0) < 0][:top_n]
        else:
            return results[:top_n]

    def _extract_stock_info(self, row: pd.Series) -> Dict[str, Any]:
        code_col = self.filters._find_col(pd.DataFrame([row]), ["代码", "code", "symbol"])
        name_col = self.filters._find_col(pd.DataFrame([row]), ["名称", "name", "股票名称"])
        chg_col = self.filters._find_col(pd.DataFrame([row]), ["涨跌幅", "change_pct", "pct_chg"])
        vol_col = self.filters._find_col(pd.DataFrame([row]), ["量比", "volume_ratio", "vol_ratio"])
        price_col = self.filters._find_col(pd.DataFrame([row]), ["最新价", "close", "price"])
        turn_col = self.filters._find_col(pd.DataFrame([row]), ["换手率", "turnover_rate", "turnover"])
        amt_col = self.filters._find_col(pd.DataFrame([row]), ["成交额", "amount", "成交金额"])
        pe_col = self.filters._find_col(pd.DataFrame([row]), ["市盈率-动态", "pe", "pe_ttm", "市盈率"])

        result = {}
        if code_col:
            result["code"] = str(row.get(code_col, ""))
        if name_col:
            result["name"] = str(row.get(name_col, ""))
        if price_col:
            result["price"] = float(row.get(price_col, 0)) if not pd.isna(row.get(price_col, 0)) else 0
        if chg_col:
            result["change_pct"] = float(row.get(chg_col, 0)) if not pd.isna(row.get(chg_col, 0)) else 0
        if vol_col:
            result["volume_ratio"] = float(row.get(vol_col, 1)) if not pd.isna(row.get(vol_col, 1)) else 1
        if turn_col:
            result["turnover_rate"] = float(row.get(turn_col, 0)) if not pd.isna(row.get(turn_col, 0)) else 0
        if amt_col:
            result["amount_yi"] = round(float(row.get(amt_col, 0)) / 1e8, 2) if not pd.isna(row.get(amt_col, 0)) else 0
        if pe_col:
            result["pe"] = float(row.get(pe_col, 0)) if not pd.isna(row.get(pe_col, 0)) else 0

        result["score"] = float(row.get("_score", 0))
        return result
