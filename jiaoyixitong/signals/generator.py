from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from config.settings import SystemConfig, SignalConfig


@dataclass
class TradingSignal:
    action: str
    strength: str
    score: float
    reasons: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    position_advice: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0


class SignalGenerator:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.signal_config = config.signal

    def generate(self,
                 market_trend: Dict[str, Any],
                 sector_rotation: Dict[str, Any],
                 capital_flow: Dict[str, Any],
                 sentiment: Dict[str, Any]) -> TradingSignal:

        scores = self._compute_component_scores(market_trend, sector_rotation, capital_flow, sentiment)

        total_score = (
            scores["trend"] * 0.30 +
            scores["sector"] * 0.20 +
            scores["flow"] * 0.20 +
            scores["sentiment"] * 0.15 +
            scores["technical"] * 0.15
        )

        reasons, warnings = self._collect_reasons(scores, market_trend, sector_rotation,
                                                    capital_flow, sentiment)

        if total_score >= self.signal_config.bullish_score_threshold:
            action = "开仓"
            strength = "强" if total_score >= 0.75 else "中"
        elif total_score <= self.signal_config.bearish_score_threshold:
            action = "清仓"
            strength = "强" if total_score <= 0.25 else "中"
        else:
            action = "观望"
            strength = "-"

        position_advice = self._calculate_position(total_score)

        return TradingSignal(
            action=action,
            strength=strength,
            score=round(total_score, 2),
            reasons=reasons,
            warnings=warnings,
            position_advice=round(position_advice, 2),
            stop_loss=self.signal_config.stop_loss_pct,
            take_profit=self.signal_config.take_profit_pct,
        )

    def _compute_component_scores(self, market_trend, sector_rotation,
                                    capital_flow, sentiment) -> Dict[str, float]:
        trend_score = market_trend.get("overall_score", 0.0)
        trend_score = (trend_score + 1) / 2
        scores = {"trend": trend_score}

        north = capital_flow.get("north_flow", {})
        north_signal = north.get("signal", "")
        if "积极看多" in north_signal:
            flow_score = 0.85
        elif "偏多" in north_signal:
            flow_score = 0.65
        elif "偏空" in north_signal:
            flow_score = 0.35
        elif "看空" in north_signal:
            flow_score = 0.15
        else:
            flow_score = 0.5

        ind_top = capital_flow.get("industry_flow_top", [])
        if ind_top:
            top_flows = sum(i.get("flow_yi", 0) for i in ind_top[:3])
            if top_flows > 30:
                flow_score = min(1.0, flow_score + 0.1)
            elif top_flows < -30:
                flow_score = max(0.0, flow_score - 0.1)
        scores["flow"] = flow_score

        rot = sector_rotation.get("rotation_signal", {})
        rot_type = rot.get("type", "")
        if rot_type == "成长领涨":
            scores["sector"] = 0.75
        elif rot_type == "周期轮动":
            scores["sector"] = 0.65
        elif rot_type == "防御为主":
            scores["sector"] = 0.35
        elif rot_type == "结构分化":
            scores["sector"] = 0.50
        else:
            scores["sector"] = 0.50

        sent = sentiment.get("sentiment_score", {})
        scores["sentiment"] = sent.get("score", 50) / 100.0

        trend_detail = market_trend.get("trend", {})
        macd = trend_detail.get("MACD", {})
        momentum = market_trend.get("momentum", {})
        kdj = momentum.get("KDJ", {})

        tech_score = 0.5
        if macd.get("signal") == 1:
            tech_score += 0.15
        elif macd.get("DIF", 0) > macd.get("DEA", 0):
            tech_score += 0.05
        else:
            tech_score -= 0.1

        if kdj.get("signal", 0) >= 2:
            tech_score += 0.1
        elif kdj.get("signal", 0) >= 1:
            tech_score += 0.05
        elif kdj.get("signal", 0) <= -2:
            tech_score -= 0.1

        rsi = momentum.get("RSI", 50)
        if 30 <= rsi <= 70:
            tech_score += 0.05

        vol = market_trend.get("volume", {})
        if vol.get("volume_ratio", 1.0) > 1.2:
            tech_score += 0.05

        scores["technical"] = max(0.0, min(1.0, tech_score))
        return scores

    def _collect_reasons(self, scores, market_trend, sector_rotation,
                          capital_flow, sentiment):
        reasons = []
        warnings = []

        if scores["trend"] > 0.65:
            reasons.append("大盘趋势偏多，均线支撑良好")
        elif scores["trend"] < 0.35:
            warnings.append("大盘趋势偏空，均线压制明显")
        else:
            reasons.append("大盘趋势中性")

        if scores["flow"] > 0.65:
            reasons.append("资金面偏多，北向资金净流入")
        elif scores["flow"] < 0.35:
            warnings.append("资金面偏空，北向资金净流出")

        if scores["sector"] > 0.65:
            reasons.append("板块轮动活跃，有明确主线")
        elif scores["sector"] < 0.35:
            warnings.append("板块轮动偏弱，防御为主")

        if scores["sentiment"] > 0.65:
            reasons.append("市场情绪偏暖，涨停家数较多")
        elif scores["sentiment"] < 0.35:
            warnings.append("市场情绪低迷，注意风险")

        trend_detail = market_trend.get("trend", {})
        macd = trend_detail.get("MACD", {})
        if macd.get("signal") == 1:
            reasons.append("MACD金叉信号")
        elif macd.get("signal") == -1:
            warnings.append("MACD死叉信号")

        return reasons, warnings

    def _calculate_position(self, total_score: float) -> float:
        max_pos = self.signal_config.position_sizing_max
        if total_score >= 0.75:
            return max_pos
        elif total_score >= 0.65:
            return max_pos * 0.7
        elif total_score >= 0.55:
            return max_pos * 0.4
        elif total_score >= 0.45:
            return max_pos * 0.3
        elif total_score >= 0.35:
            return max_pos * 0.15
        else:
            return 0.0


class RiskManager:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.signal_config = config.signal

    def evaluate_risk(self, market_trend: Dict[str, Any],
                      signal: TradingSignal) -> Dict[str, Any]:
        volatility = market_trend.get("volatility", {})
        atr_pct = volatility.get("ATR_pct", 1.0)
        vol_level = volatility.get("volatility_level", "中波动")

        if atr_pct > 3:
            risk_level = "极高"
            pos_adj = 0.3
        elif atr_pct > 2:
            risk_level = "高"
            pos_adj = 0.5
        elif atr_pct > 1:
            risk_level = "中"
            pos_adj = 0.8
        else:
            risk_level = "低"
            pos_adj = 1.0

        adjusted_position = round(signal.position_advice * pos_adj, 2)

        trend = market_trend.get("trend", {})
        adx = trend.get("ADX", 20)
        if adx < 20:
            adjusted_position *= 0.7

        return {
            "risk_level": risk_level,
            "volatility_level": vol_level,
            "ATR_pct": round(atr_pct, 2),
            "position_adjustment": pos_adj,
            "adjusted_position": adjusted_position,
            "stop_loss": self.signal_config.stop_loss_pct,
            "take_profit": self.signal_config.take_profit_pct,
            "max_drawdown_limit": self.signal_config.max_drawdown_limit,
            "max_daily_loss": self.signal_config.max_daily_loss,
            "single_stock_max": self.signal_config.single_stock_max,
        }

    def check_stop_conditions(self, current_pnl: float, daily_pnl: float) -> Dict[str, Any]:
        triggers = []
        if current_pnl <= self.signal_config.stop_loss_pct:
            triggers.append(f"触发止损({current_pnl*100:.1f}%)")
        if current_pnl >= self.signal_config.take_profit_pct:
            triggers.append(f"触发止盈({current_pnl*100:.1f}%)")
        if current_pnl <= self.signal_config.max_drawdown_limit:
            triggers.append(f"触发最大回撤({current_pnl*100:.1f}%)")
        if daily_pnl <= self.signal_config.max_daily_loss:
            triggers.append(f"触发日内最大亏损({daily_pnl*100:.1f}%)")

        return {
            "should_stop": len(triggers) > 0,
            "triggers": triggers,
            "current_pnl": round(current_pnl, 4),
            "daily_pnl": round(daily_pnl, 4),
        }
