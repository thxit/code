import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from loguru import logger
from data.fetcher import DataFetcher
from indicators.trend import TrendIndicators
from indicators.momentum import MomentumIndicators
from indicators.volume import VolumeIndicators
from config.settings import SystemConfig, IndicatorConfig


@dataclass
class Trade:
    date: str
    action: str
    price: float
    shares: int = 0
    amount: float = 0.0
    reason: str = ""


@dataclass
class BacktestResult:
    total_return: float = 0.0
    annual_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_profit: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[float] = field(default_factory=list)


class BacktestEngine:
    def __init__(self, config: SystemConfig, fetcher: DataFetcher = None):
        self.config = config
        self.fetcher = fetcher
        self.trend_ind = TrendIndicators(config.indicator)
        self.momentum_ind = MomentumIndicators(config.indicator)
        self.volume_ind = VolumeIndicators(config.indicator)
        self.trades: List[Trade] = []
        self.equity: List[float] = []

    def run(self, index_code: str = "000001", period: int = 500,
            initial_capital: float = 100000.0) -> BacktestResult:

        if self.fetcher is None:
            logger.error("No data fetcher available")
            return BacktestResult()

        df = self.fetcher.fetch_index_daily(index_code, period=period)
        if df is None or df.empty:
            logger.error(f"No data for index {index_code}")
            return BacktestResult()

        df = self.trend_ind.compute_all(df)
        df = self.momentum_ind.compute_all(df)
        df = self.volume_ind.compute_all(df)

        signals = self._generate_signals(df)
        self.trades = self._simulate_trades(signals, initial_capital)

        return self._calculate_result(initial_capital)

    def _generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["signal"] = 0

        golden = (df["MACD_DIF"] > df["MACD_DEA"]) & (df["MACD_DIF"].shift(1) <= df["MACD_DEA"].shift(1))
        dead = (df["MACD_DIF"] < df["MACD_DEA"]) & (df["MACD_DIF"].shift(1) >= df["MACD_DEA"].shift(1))

        df.loc[golden, "signal"] = 1
        df.loc[dead, "signal"] = -2

        df["ma_trend"] = df["MA5"] > df["MA20"]
        df["vol_ok"] = df["VOL_MA5"] > df["VOL_MA10"]

        bullish = df["ma_trend"] & df["vol_ok"] & (
            (df["KDJ_J"] < 30) | (df["RSI"] < 40)
        )
        df.loc[bullish & (df["signal"] == 0), "signal"] = 2

        df["pct"] = df["close"].pct_change()
        df.loc[df["pct"] < -0.05, "signal"] = -1

        return df

    def _simulate_trades(self, signals: pd.DataFrame, initial_capital: float) -> List[Trade]:
        trades = []
        capital = initial_capital
        position = 0
        entry_price = 0
        equity = [initial_capital]

        window = 30
        for i in range(window, len(signals)):
            row = signals.iloc[i]
            signal = row["signal"]
            price = row["close"]
            date = str(row["date"].date()) if "date" in signals.columns else str(i)

            if signal >= 1 and position == 0:
                position = capital / price
                entry_price = price
                capital = 0
                trades.append(Trade(date=date, action="BUY", price=price,
                                    shares=int(position), amount=position * price,
                                    reason=f"Signal={signal}"))

            elif signal <= -1 and position > 0:
                capital = position * price
                pnl_pct = (price / entry_price - 1) * 100
                trades.append(Trade(date=date, action="SELL", price=price,
                                    shares=int(position), amount=position * price,
                                    reason=f"PNL={pnl_pct:.1f}%"))
                position = 0
                entry_price = 0

            if position > 0:
                current_equity = position * price
            else:
                current_equity = capital
            equity.append(current_equity)

        if position > 0:
            last_price = signals.iloc[-1]["close"]
            capital = position * last_price
            trades.append(Trade(date=str(signals.iloc[-1]["date"].date()),
                                action="SELL", price=last_price,
                                shares=int(position), amount=position * last_price,
                                reason="强制平仓"))

        self.equity = equity
        return trades

    def _calculate_result(self, initial_capital: float) -> BacktestResult:
        if not self.trades:
            return BacktestResult()

        buy_trades = [t for t in self.trades if t.action == "BUY"]
        sell_trades = [t for t in self.trades if t.action == "SELL"]

        if not buy_trades or not sell_trades:
            return BacktestResult()

        profits = []
        for i, sell in enumerate(sell_trades):
            if i < len(buy_trades):
                buy = buy_trades[i]
                pnl = (sell.price / buy.price - 1)
                profits.append(pnl)

        if not profits:
            return BacktestResult()

        total_return = np.prod([1 + p for p in profits]) - 1

        winning = [p for p in profits if p > 0]
        losing = [p for p in profits if p <= 0]

        win_rate = len(winning) / len(profits) if profits else 0
        avg_profit = np.mean(winning) if winning else 0
        avg_loss = np.mean(losing) if losing else 0

        df_pnl = pd.Series(np.cumprod([1 + p for p in profits]))
        rolling_max = df_pnl.expanding().max()
        drawdown = (df_pnl - rolling_max) / rolling_max
        max_drawdown = drawdown.min()

        if len(profits) > 0:
            daily_returns = pd.Series(profits)
            sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0
        else:
            sharpe = 0

        return BacktestResult(
            total_return=round(total_return * 100, 2),
            annual_return=round(((1 + total_return) ** (252 / len(profits)) - 1) * 100, 2),
            sharpe_ratio=round(sharpe, 2),
            max_drawdown=round(max_drawdown * 100, 2),
            win_rate=round(win_rate * 100, 1),
            total_trades=len(profits),
            winning_trades=len(winning),
            losing_trades=len(losing),
            avg_profit=round(avg_profit * 100, 2),
            avg_loss=round(avg_loss * 100, 2),
            profit_factor=round(abs(avg_profit / avg_loss) if avg_loss != 0 else 0, 2),
            trades=self.trades[-20:],
            equity_curve=self.equity[-100:],
        )
