import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger

from config.settings import SystemConfig, get_config
from data.fetcher import DataFetcher
from analysis.market_trend import MarketTrendAnalyzer
from analysis.sector_rotation import SectorRotationAnalyzer
from analysis.capital_flow import CapitalFlowAnalyzer
from analysis.sentiment import SentimentAnalyzer
from signals.generator import SignalGenerator, RiskManager
from screening.selector import StockSelector
from backtest.engine import BacktestEngine


class QuantTradingSystem:
    def __init__(self, config: Optional[SystemConfig] = None):
        self.config = config or get_config()
        logger.remove()
        logger.add(sys.stderr, level=self.config.log_level)

        self.fetcher = DataFetcher(self.config)
        self.market_analyzer = MarketTrendAnalyzer(self.config, self.fetcher)
        self.sector_analyzer = SectorRotationAnalyzer(self.config, self.fetcher)
        self.flow_analyzer = CapitalFlowAnalyzer(self.config, self.fetcher)
        self.sentiment_analyzer = SentimentAnalyzer(self.config, self.fetcher)
        self.signal_generator = SignalGenerator(self.config)
        self.risk_manager = RiskManager(self.config)

    def run_full_analysis(self) -> Dict[str, Any]:
        logger.info("=" * 60)
        logger.info("A股短线量化交易系统 - 全面分析开始")
        logger.info(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        market_trend = self.market_analyzer.analyze("000001", period=250)
        sector_rotation = self.sector_analyzer.analyze(period=20)
        capital_flow = self.flow_analyzer.analyze()
        sentiment = self.sentiment_analyzer.analyze()

        signal = self.signal_generator.generate(
            market_trend, sector_rotation, capital_flow, sentiment
        )

        risk = self.risk_manager.evaluate_risk(market_trend, signal)

        stock_selector = StockSelector(lambda: self.fetcher.fetch_stock_list())
        recommended_stocks = stock_selector.screen(top_n=20)

        backtest_engine = BacktestEngine(self.config, self.fetcher)
        backtest_result = backtest_engine.run("000001", period=500)

        result = {
            "meta": {
                "system": "A股短线量化交易系统",
                "version": "1.0.0",
                "analysis_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            },
            "market_trend": market_trend,
            "sector_rotation": sector_rotation,
            "capital_flow": capital_flow,
            "sentiment": sentiment,
            "trading_signal": {
                "action": signal.action,
                "strength": signal.strength,
                "score": signal.score,
                "reasons": signal.reasons,
                "warnings": signal.warnings,
                "position_advice": signal.position_advice,
                "stop_loss": signal.stop_loss,
                "take_profit": signal.take_profit,
            },
            "risk_assessment": risk,
            "recommended_stocks": recommended_stocks,
            "backtest": {
                "total_return": backtest_result.total_return,
                "annual_return": backtest_result.annual_return,
                "sharpe_ratio": backtest_result.sharpe_ratio,
                "max_drawdown": backtest_result.max_drawdown,
                "win_rate": backtest_result.win_rate,
                "total_trades": backtest_result.total_trades,
                "profit_factor": backtest_result.profit_factor,
            },
        }

        logger.info("=" * 60)
        logger.info("全面分析完成!")
        logger.info("=" * 60)

        return result

    def quick_analysis(self) -> Dict[str, Any]:
        logger.info("快速分析中...")

        market_trend = self.market_analyzer.analyze("000001", period=120)
        capital_flow = self.flow_analyzer.analyze()
        sentiment = self.sentiment_analyzer.analyze()

        signal = self.signal_generator.generate(
            market_trend,
            {"rotation_signal": {}, "top_sectors": []},
            capital_flow,
            sentiment,
        )

        return {
            "market_trend": market_trend,
            "capital_flow": capital_flow,
            "sentiment": sentiment,
            "trading_signal": {
                "action": signal.action,
                "strength": signal.strength,
                "score": signal.score,
                "reasons": signal.reasons,
                "warnings": signal.warnings,
            },
        }

    def screen_stocks(self, strategy: str = "breakout", top_n: int = 20) -> list:
        selector = StockSelector(lambda: self.fetcher.fetch_stock_list())
        return selector.screen_by_strategy(strategy, top_n)

    def export_report(self, result: Dict[str, Any], filepath: str = "report.json"):
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"报告已导出到: {filepath}")

    def print_rich_report(self, result: Dict[str, Any]):
        try:
            from rich.console import Console
            from rich.table import Table
            from rich.panel import Panel
            from rich.text import Text
            from rich import box

            console = Console()
            console.rule("[bold cyan]A股短线量化交易系统 - 分析报告[/bold cyan]")

            meta = result["meta"]
            console.print(f"[dim]分析时间: {meta['analysis_time']}[/dim]")
            console.print()

            signal = result["trading_signal"]
            action = signal["action"]
            action_color = "green" if action == "开仓" else ("red" if action == "清仓" else "yellow")
            signal_panel = Panel(
                f"[bold {action_color}]交易建议: {action} ({signal['strength']})[/bold {action_color}]\n"
                f"综合评分: {signal['score']:.2f}\n"
                f"建议仓位: {signal['position_advice']*100:.0f}%\n"
                f"止损: {signal['stop_loss']*100:.0f}% | 止盈: {signal['take_profit']*100:.0f}%",
                title="[bold]交易信号[/bold]",
                border_style=action_color,
            )
            console.print(signal_panel)

            if signal["reasons"]:
                console.print("[bold green]看多理由:[/bold green]")
                for r in signal["reasons"]:
                    console.print(f"  [green]+ {r}[/green]")
            if signal["warnings"]:
                console.print("[bold red]风险提示:[/bold red]")
                for w in signal["warnings"]:
                    console.print(f"  [red]! {w}[/red]")
            console.print()

            mt = result["market_trend"]
            trend = mt.get("trend", {})
            mom = mt.get("momentum", {})
            vol = mt.get("volume", {})

            table = Table(title="大盘趋势分析", box=box.ROUNDED)
            table.add_column("指标", style="cyan", width=12)
            table.add_column("数值", style="white", width=18)
            table.add_column("状态", style="yellow", width=20)

            table.add_row("当前点位", f"{mt.get('current_price', '-')}", "")
            table.add_row("5日均线", f"{trend.get('MA5', '-')}",
                          "站上" if mt.get('current_price', 0) > trend.get('MA5', 0) else "下方")
            table.add_row("20日均线", f"{trend.get('MA20', '-')}",
                          "站上" if mt.get('current_price', 0) > trend.get('MA20', 0) else "下方")
            table.add_row("MACD", f"DIF:{trend.get('MACD', {}).get('DIF', '-')}",
                          trend.get('MACD', {}).get('status', '-'))
            table.add_row("RSI", f"{mom.get('RSI', '-')}", mom.get('RSI_zone', '-'))
            kdj = mom.get("KDJ", {})
            table.add_row("KDJ", f"K:{kdj.get('K','-')} D:{kdj.get('D','-')} J:{kdj.get('J','-')}",
                          kdj.get('status', '-'))
            table.add_row("量比", f"{vol.get('volume_ratio', '-')}", vol.get('volume_zone', '-'))
            table.add_row("5日涨幅", f"{mom.get('change_5d', '-')}%",
                          "上涨" if mom.get('change_5d', 0) > 0 else "下跌")
            table.add_row("ADX", f"{trend.get('ADX', '-')}", trend.get('ADX_strength', '-'))
            console.print(table)
            console.print(f"[dim]总结: {mt.get('summary', '')}[/dim]")
            console.print()

            sr = result["sector_rotation"]
            rot = sr.get("rotation_signal", {})
            console.print(f"[bold]板块轮动: [cyan]{rot.get('type', '-')}[/cyan][/bold]")
            console.print(f"[dim]{rot.get('description', '')}[/dim]")
            top = sr.get("top_sectors", [])[:5]
            if top:
                sector_table = Table(title="强势板块 TOP5", box=box.ROUNDED)
                sector_table.add_column("排名", style="cyan", width=6)
                sector_table.add_column("板块", style="white", width=16)
                sector_table.add_column("涨跌幅%", style="green", width=10)
                sector_table.add_column("综合评分", style="yellow", width=10)
                for i, s in enumerate(top):
                    sector_table.add_row(
                        str(i + 1), s["name"],
                        f"{s['performance']:.1f}%",
                        f"{s['composite_score']:.3f}",
                    )
                console.print(sector_table)
            console.print()

            cf = result["capital_flow"]
            console.print(f"[bold]资金流向:[/bold] {cf.get('summary', '')}")
            nf = cf.get("north_flow", {})
            console.print(f"  北向资金: {nf.get('signal', '-')} (20日累计: {nf.get('recent_20_flow', 0):.1f}亿)")
            ind_top = cf.get("industry_flow_top", [])[:5]
            if ind_top:
                flow_str = " | ".join([f"{i['name']}: {i['flow_yi']:.1f}亿" for i in ind_top])
                console.print(f"  行业流入TOP5: {flow_str}")
            console.print()

            sent = result["sentiment"]
            ss = sent.get("sentiment_score", {})
            console.print(f"[bold]情绪热点: [cyan]{ss.get('zone', '-')}[/cyan] (得分: {ss.get('score', '-')})[/bold]")
            console.print(f"  建议: {ss.get('suggestion', '')}")
            hc = sent.get("hot_concepts", [])[:5]
            if hc:
                hc_str = " | ".join([f"{c['name']}({c['limit_count']})" for c in hc])
                console.print(f"  热点概念: {hc_str}")
            console.print()

            risk = result["risk_assessment"]
            risk_color = "green" if risk.get("risk_level") == "低" else ("yellow" if risk.get("risk_level") == "中" else "red")
            console.print(f"[bold]风险评估: [{risk_color}]{risk.get('risk_level', '-')}风险[/{risk_color}][/bold]")
            console.print(f"  波动率: {risk.get('volatility_level', '-')} (ATR: {risk.get('ATR_pct', '-')}%)")
            console.print(f"  调整仓位: {risk.get('adjusted_position', 0)*100:.0f}%")
            console.print()

            stocks = result.get("recommended_stocks", [])[:10]
            if stocks:
                stk_table = Table(title="推荐股票 TOP10", box=box.ROUNDED)
                stk_table.add_column("排名", style="cyan", width=6)
                stk_table.add_column("代码", style="white", width=12)
                stk_table.add_column("名称", style="white", width=12)
                stk_table.add_column("价格", style="green", width=8)
                stk_table.add_column("涨跌幅%", style="yellow", width=10)
                stk_table.add_column("量比", style="yellow", width=8)
                stk_table.add_column("评分", style="magenta", width=8)
                for i, s in enumerate(stocks[:10]):
                    stk_table.add_row(
                        str(i + 1),
                        s.get("code", "-"),
                        s.get("name", "-"),
                        f"{s.get('price', 0):.2f}",
                        f"{s.get('change_pct', 0):.2f}",
                        f"{s.get('volume_ratio', 0):.2f}",
                        f"{s.get('score', 0):.3f}",
                    )
                console.print(stk_table)
            console.print()

            bt = result.get("backtest", {})
            bt_table = Table(title="策略回测", box=box.ROUNDED)
            bt_table.add_column("指标", style="cyan", width=14)
            bt_table.add_column("数值", style="white", width=14)
            bt_table.add_row("总收益率", f"{bt.get('total_return', '-')}%")
            bt_table.add_row("年化收益率", f"{bt.get('annual_return', '-')}%")
            bt_table.add_row("夏普比率", f"{bt.get('sharpe_ratio', '-')}")
            bt_table.add_row("最大回撤", f"{bt.get('max_drawdown', '-')}%")
            bt_table.add_row("胜率", f"{bt.get('win_rate', '-')}%")
            bt_table.add_row("交易次数", f"{bt.get('total_trades', '-')}")
            bt_table.add_row("盈亏比", f"{bt.get('profit_factor', '-')}")
            console.print(bt_table)

            console.rule("[bold cyan]报告结束[/bold cyan]")

        except ImportError:
            logger.warning("Rich库未安装，使用简单输出")
            self._print_simple_report(result)

    def _print_simple_report(self, result: Dict[str, Any]):
        print("\n" + "=" * 60)
        print("  A股短线量化交易系统 - 分析报告")
        print("=" * 60)

        signal = result.get("trading_signal", {})
        strength = signal.get("strength", "-")
        print(f"\n交易信号: {signal.get('action', '-')} ({strength})")
        print(f"综合评分: {signal.get('score', 0):.2f}")
        print(f"建议仓位: {signal.get('position_advice', 0)*100:.0f}%")

        if signal.get("reasons"):
            print("\n看多理由:")
            for r in signal["reasons"]:
                print(f"  + {r}")
        if signal.get("warnings"):
            print("\n风险提示:")
            for w in signal["warnings"]:
                print(f"  ! {w}")

        mt = result.get("market_trend", {})
        print(f"\n大盘趋势: {mt.get('summary', '-')}")

        sr = result.get("sector_rotation", {})
        rot = sr.get("rotation_signal", {})
        print(f"板块轮动: {rot.get('type', '-')} - {rot.get('description', '')}")

        cf = result.get("capital_flow", {})
        print(f"资金流向: {cf.get('summary', '-')}")

        sent = result.get("sentiment", {})
        ss = sent.get("sentiment_score", {})
        print(f"市场情绪: {ss.get('zone', '-')} ({ss.get('suggestion', '')})")

        risk = result.get("risk_assessment", {})
        print(f"风险评估: {risk.get('risk_level', '-')}, 仓位: {risk.get('adjusted_position', 0)*100:.0f}%")

        stocks = result.get("recommended_stocks", [])[:5]
        if stocks:
            print("\n推荐股票:")
            for i, s in enumerate(stocks):
                print(f"  {i+1}. {s.get('code','-')} {s.get('name','-')} "
                      f"价格:{s.get('price',0):.2f} 涨幅:{s.get('change_pct',0):.2f}%")

        bt = result.get("backtest", {})
        print(f"\n策略回测: 总收益{bt.get('total_return','-')}%, "
              f"夏普{bt.get('sharpe_ratio','-')}, "
              f"最大回撤{bt.get('max_drawdown','-')}%, "
              f"胜率{bt.get('win_rate','-')}%")

        print("\n" + "=" * 60)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="A股短线量化交易系统")
    parser.add_argument("--mode", choices=["full", "quick", "screen", "backtest"], default="full",
                        help="运行模式: full=全面分析, quick=快速分析, screen=选股, backtest=回测")
    parser.add_argument("--strategy", default="breakout",
                        choices=["breakout", "momentum", "volume_breakout", "oversold_reversal"],
                        help="选股策略")
    parser.add_argument("--output", default=None, help="输出报告文件路径")
    parser.add_argument("--config", default=None, help="配置文件路径")
    parser.add_argument("--simple", action="store_true", help="使用简单文本输出")
    parser.add_argument("--top-n", type=int, default=20, help="推荐股票数量")

    args = parser.parse_args()

    config = get_config(args.config) if args.config else None
    system = QuantTradingSystem(config)

    if args.mode == "screen":
        stocks = system.screen_stocks(strategy=args.strategy, top_n=args.top_n)
        print(f"\n选股结果 ({args.strategy}策略):")
        for i, s in enumerate(stocks[:args.top_n]):
            print(f"  {i+1}. {s.get('code','')} {s.get('name','')} "
                  f"价格:{s.get('price',0):.2f} 涨幅:{s.get('change_pct',0):.2f}% "
                  f"量比:{s.get('volume_ratio',0):.2f} 评分:{s.get('score',0):.3f}")
        return

    if args.mode == "backtest":
        engine = BacktestEngine(config or SystemConfig(), system.fetcher)
        result = engine.run("000001", period=500)
        print(f"\n回测结果:")
        print(f"  总收益率: {result.total_return}%")
        print(f"  年化收益率: {result.annual_return}%")
        print(f"  夏普比率: {result.sharpe_ratio}")
        print(f"  最大回撤: {result.max_drawdown}%")
        print(f"  胜率: {result.win_rate}%")
        print(f"  交易次数: {result.total_trades}")
        print(f"  盈亏比: {result.profit_factor}")
        return

    if args.mode == "quick":
        result = system.quick_analysis()
    else:
        result = system.run_full_analysis()

    if args.simple:
        system._print_simple_report(result)
    else:
        system.print_rich_report(result)

    if args.output:
        system.export_report(result, args.output)


if __name__ == "__main__":
    main()
