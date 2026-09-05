from dataclasses import dataclass, field
from typing import List, Dict, Optional
import json
import os


@dataclass
class MarketConfig:
    major_indices: List[str] = field(default_factory=lambda: [
        "000001", "399001", "399006", "000688", "000016", "000905"
    ])
    index_names: Dict[str, str] = field(default_factory=lambda: {
        "000001": "上证指数",
        "399001": "深证成指",
        "399006": "创业板指",
        "000688": "科创50",
        "000016": "上证50",
        "000905": "中证500"
    })
    default_period: int = 250


@dataclass
class SectorConfig:
    rotation_window: int = 20
    top_n_sectors: int = 10
    sw_sectors: List[str] = field(default_factory=lambda: [
        "801010", "801020", "801030", "801040", "801050",
        "801060", "801070", "801080", "801090", "801100",
        "801110", "801120", "801130", "801140", "801150",
        "801160", "801170", "801180", "801190", "801200",
        "801210", "801220", "801230", "801240", "801710",
        "801720", "801730", "801740", "801750", "801760",
        "801770", "801780", "801790", "801880"
    ])


@dataclass
class IndicatorConfig:
    ma_periods: List[int] = field(default_factory=lambda: [5, 10, 20, 60, 120, 250])
    ma_short: int = 5
    ma_long: int = 20
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9
    rsi_period: int = 14
    rsi_oversold: float = 30.0
    rsi_overbought: float = 70.0
    kdj_n: int = 9
    kdj_m1: int = 3
    kdj_m2: int = 3
    boll_period: int = 20
    boll_std: float = 2.0
    atr_period: int = 14
    volume_ma_period: int = 20
    volume_ratio_threshold: float = 1.5


@dataclass
class SignalConfig:
    bullish_score_threshold: float = 0.6
    bearish_score_threshold: float = 0.4
    position_sizing_max: float = 0.3
    single_stock_max: float = 0.1
    stop_loss_pct: float = -0.05
    take_profit_pct: float = 0.10
    max_drawdown_limit: float = -0.15
    max_daily_loss: float = -0.03


@dataclass
class StockScreeningConfig:
    min_volume_ratio: float = 1.2
    min_ma_alignment_score: float = 1.0
    pe_range: tuple = (0, 200)
    pb_range: tuple = (0, 20)
    min_market_cap: float = 50e8
    max_price: float = 100.0
    min_price: float = 3.0
    min_change_pct: float = -0.05
    max_change_pct: float = 0.095


@dataclass
class SystemConfig:
    market: MarketConfig = field(default_factory=MarketConfig)
    sector: SectorConfig = field(default_factory=SectorConfig)
    indicator: IndicatorConfig = field(default_factory=IndicatorConfig)
    signal: SignalConfig = field(default_factory=SignalConfig)
    screening: StockScreeningConfig = field(default_factory=StockScreeningConfig)
    cache_dir: str = "./data_cache"
    enable_cache: bool = True
    log_level: str = "INFO"
    output_format: str = "rich"


def get_config(config_path: Optional[str] = None) -> SystemConfig:
    if config_path and os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SystemConfig(
            market=MarketConfig(**data.get("market", {})),
            sector=SectorConfig(**data.get("sector", {})),
            indicator=IndicatorConfig(**data.get("indicator", {})),
            signal=SignalConfig(**data.get("signal", {})),
            screening=StockScreeningConfig(**data.get("screening", {})),
            cache_dir=data.get("cache_dir", "./data_cache"),
            enable_cache=data.get("enable_cache", True),
        )
    return SystemConfig()
