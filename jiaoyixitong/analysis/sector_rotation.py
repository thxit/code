import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from loguru import logger
from data.fetcher import DataFetcher
from config.settings import SystemConfig


class SectorRotationAnalyzer:
    SECTOR_NAMES = {
        "801010": "农林牧渔", "801020": "采掘", "801030": "化工", "801040": "钢铁",
        "801050": "有色金属", "801060": "电子", "801070": "家用电器", "801080": "食品饮料",
        "801090": "纺织服装", "801100": "轻工制造", "801110": "医药生物", "801120": "公用事业",
        "801130": "交通运输", "801140": "房地产", "801150": "商业贸易", "801160": "休闲服务",
        "801170": "综合", "801180": "建筑材料", "801190": "建筑装饰", "801200": "电气设备",
        "801210": "国防军工", "801220": "计算机", "801230": "传媒", "801240": "通信",
        "801710": "银行", "801720": "非银金融", "801730": "汽车", "801740": "机械设备",
        "801750": "采掘服务", "801760": "基础化工", "801770": "石油石化", "801780": "电力设备",
        "801790": "国防", "801880": "电子设备"
    }

    def __init__(self, config: SystemConfig, fetcher: DataFetcher):
        self.config = config
        self.fetcher = fetcher

    def analyze(self, period: int = 20) -> Dict[str, Any]:
        logger.info("Analyzing sector rotation")
        top_n = self.config.sector.top_n_sectors
        sector_codes = self.config.sector.sw_sectors

        sector_performance = self._get_sector_performance(sector_codes, period)
        if not sector_performance:
            logger.warning("Sector data unavailable, skipping rotation analysis")
            return {
                "top_sectors": [], "bottom_sectors": [],
                "rotation_signal": {"type": "unknown", "signal": "数据不可用", "description": "板块数据获取失败"},
                "all_sectors_ranked": [], "analysis_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
            }

        sector_strength = self._compute_sector_strength(sector_codes, period)
        sector_momentum = self._compute_sector_momentum(sector_codes, period)

        ranked_sectors = self._rank_sectors(sector_performance, sector_strength, sector_momentum)
        top_sectors = ranked_sectors[:top_n]
        bottom_sectors = ranked_sectors[-top_n:]

        rotation_signal = self._detect_rotation(ranked_sectors, period)

        return {
            "top_sectors": top_sectors,
            "bottom_sectors": bottom_sectors,
            "rotation_signal": rotation_signal,
            "all_sectors_ranked": ranked_sectors[:30],
            "analysis_date": pd.Timestamp.now().strftime("%Y-%m-%d"),
        }

    def _get_sector_performance(self, sector_codes: List[str], period: int) -> Dict[str, float]:
        performance = {}
        for code in sector_codes[:1]:
            try:
                df = self.fetcher.fetch_sector_daily(code, period=period + 5)
                if df is not None and not df.empty and len(df) >= 5:
                    close = df["close"].values
                    chg = (close[-1] / close[-min(6, len(df))] - 1) * 100
                    name = self.SECTOR_NAMES.get(code, code)
                    performance[name] = round(float(chg), 2)
            except Exception as e:
                logger.debug(f"Sector {code} perf error: {e}")
                continue
        return performance

    def _compute_sector_strength(self, sector_codes: List[str], period: int) -> Dict[str, float]:
        strength = {}
        for code in sector_codes[:3]:
            try:
                df = self.fetcher.fetch_sector_daily(code, period=period + 5)
                if df is not None and not df.empty and len(df) >= 20:
                    df["MA5"] = df["close"].rolling(5).mean()
                    df["MA20"] = df["close"].rolling(20).mean()
                    latest = df.iloc[-1]
                    ma_score = 1 if latest["MA5"] > latest["MA20"] else -1
                    rsi = self._simple_rsi(df["close"], 14)
                    rsi_score = 0
                    if rsi is not None and not np.isnan(rsi):
                        if 40 <= rsi <= 60:
                            rsi_score = 0
                        elif rsi > 60:
                            rsi_score = 0.5
                        else:
                            rsi_score = -0.5
                    vol = latest.get("volume", 1)
                    vol_ma = df["volume"].tail(5).mean()
                    vol_score = 1 if vol > vol_ma else 0
                    total = ma_score + rsi_score + vol_score
                    name = self.SECTOR_NAMES.get(code, code)
                    strength[name] = round(total, 2)
            except Exception as e:
                logger.debug(f"Sector {code} strength error: {e}")
                continue
        return strength

    def _simple_rsi(self, series: pd.Series, period: int = 14) -> Optional[float]:
        try:
            delta = series.diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta).where(delta < 0, 0).rolling(window=period).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = 100 - (100 / (1 + rs))
            return float(rsi.iloc[-1])
        except Exception:
            return None

    def _compute_sector_momentum(self, sector_codes: List[str], period: int) -> Dict[str, float]:
        momentum = {}
        for code in sector_codes[:3]:
            try:
                df = self.fetcher.fetch_sector_daily(code, period=period + 5)
                if df is not None and not df.empty and len(df) >= 10:
                    close = df["close"].values
                    short = close[-1] / close[-min(6, len(df))] - 1
                    long = close[-1] / close[-min(11, len(df))] - 1 if len(df) > 10 else short
                    momentum_val = short * 0.7 + long * 0.3
                    name = self.SECTOR_NAMES.get(code, code)
                    momentum[name] = round(float(momentum_val), 4)
            except Exception as e:
                logger.debug(f"Sector {code} momentum error: {e}")
                continue
        return momentum

    def _rank_sectors(self, performance: Dict, strength: Dict, momentum: Dict) -> List[Dict]:
        all_names = set(list(performance.keys()) + list(strength.keys()) + list(momentum.keys()))
        sectors = []
        for name in all_names:
            perf = performance.get(name, 0)
            wt = max(0, min(1, (perf + 5) / 15))
            stren = strength.get(name, 0)
            ws = max(0, min(1, (stren + 3) / 6))
            mom = momentum.get(name, 0)
            wm = max(0, min(1, (mom + 0.05) / 0.15))
            composite = wt * 0.4 + ws * 0.3 + wm * 0.3
            sectors.append({
                "name": name,
                "performance": perf,
                "strength_score": stren,
                "momentum_score": round(mom * 100, 2),
                "composite_score": round(composite, 3),
            })
        sectors.sort(key=lambda x: x["composite_score"], reverse=True)
        return sectors

    def _detect_rotation(self, ranked: List[Dict], period: int) -> Dict[str, Any]:
        if len(ranked) < 5:
            return {"type": "unknown", "signal": "数据不足", "description": "无法判断板块轮动"}

        top3 = [s["name"] for s in ranked[:3]]
        top3_scores = [s["composite_score"] for s in ranked[:3]]
        score_gap = top3_scores[0] - top3_scores[-1] if len(top3_scores) >= 3 else 0

        defensive = ["银行", "食品饮料", "公用事业", "医药生物", "农林牧渔"]
        cyclical = ["有色金属", "钢铁", "化工", "汽车", "建筑材料", "房地产"]
        growth = ["电子", "计算机", "通信", "传媒", "国防军工", "电气设备", "电力设备"]

        def_count = sum(1 for s in top3 if s in defensive)
        cyc_count = sum(1 for s in top3 if s in cyclical)
        gro_count = sum(1 for s in top3 if s in growth)

        if gro_count >= 2:
            rotation_type = "成长领涨"
            signal = "市场风险偏好高，成长股活跃"
        elif cyc_count >= 2:
            rotation_type = "周期轮动"
            signal = "经济复苏预期，周期股走强"
        elif def_count >= 2:
            rotation_type = "防御为主"
            signal = "市场避险情绪浓，防御板块受青睐"
        else:
            rotation_type = "结构分化"
            signal = "板块分化明显，需精选个股"

        return {
            "type": rotation_type,
            "signal": signal,
            "top3_sectors": top3,
            "score_gap": round(score_gap, 3),
            "description": f"当前{rotation_type}: {signal}。领涨板块: {', '.join(top3)}",
        }
