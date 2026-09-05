"""
需求6: ETF轮动模块
在指定ETF池中，按20日动量周度轮动持有最强两只，全负动量时转避险
回测并计算年化收益、最大回撤、夏普比率，绘制对比资金曲线
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import ETF_POOL, MOMENTUM_SHORT, RISK_FREE_RATE, REPORT_DIR
from data_fetcher import get_etf_daily

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC',
                                     'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 动量计算 ====================

def calc_etf_momentum(df: pd.DataFrame, period: int = 20) -> float:
    if df.empty or 'close' not in df.columns:
        return -999
    close = df['close'].dropna()
    if len(close) < period:
        return -999
    return (close.iloc[-1] / close.iloc[-period] - 1) * 100

# ==================== 轮动策略 ====================

def get_weekly_rotation_signal(
    use_cache: bool = True
) -> Dict:
    """按20日动量周度轮动持有最强两只，全负动量时转避险"""
    etfs = {}
    for code, name in ETF_POOL.items():
        df = get_etf_daily(code, name, count=MOMENTUM_SHORT + 10, use_cache=use_cache)
        if not df.empty:
            momentum = calc_etf_momentum(df, MOMENTUM_SHORT)
            latest_close = df['close'].iloc[-1] if 'close' in df.columns else 0
            etfs[name] = {
                'code': code,
                'momentum': momentum,
                'close': latest_close,
                'df': df,
            }

    if not etfs:
        return {'holdings': [], 'defensive': True, 'signal_date': datetime.now().strftime('%Y-%m-%d')}

    sorted_etfs = sorted(etfs.items(), key=lambda x: x[1]['momentum'], reverse=True)
    all_negative = all(v['momentum'] < 0 for _, v in sorted_etfs)

    if all_negative:
        logger.info('所有ETF动量均为负，转为避险模式')
        return {
            'holdings': [{'name': '避险(货币基金)', 'code': 'CASH', 'momentum': 0}],
            'defensive': True,
            'signal_date': datetime.now().strftime('%Y-%m-%d'),
            'all_momentum': {name: v['momentum'] for name, v in sorted_etfs},
        }

    top_two = sorted_etfs[:2]
    holdings = []
    for name, data in top_two:
        holdings.append({
            'name': name,
            'code': data['code'],
            'momentum': round(data['momentum'], 2),
            'close': round(data['close'], 3),
        })

    logger.info(f'ETF轮动信号: 持有 {holdings[0]["name"]}({holdings[0]["momentum"]}%) '
                f'+ {holdings[1]["name"]}({holdings[1]["momentum"]}%)')

    return {
        'holdings': holdings,
        'defensive': False,
        'signal_date': datetime.now().strftime('%Y-%m-%d'),
        'all_momentum': {name: round(v['momentum'], 2) for name, v in sorted_etfs},
    }

# ==================== 回测 ====================

def run_etf_backtest(
    initial_capital: float = 1000000,
    use_cache: bool = True
) -> Dict:
    """ETF动量轮动回测"""
    all_data = {}
    for code, name in ETF_POOL.items():
        df = get_etf_daily(code, name, count=500, use_cache=use_cache)
        if not df.empty:
            all_data[name] = df

    if not all_data:
        return {'error': '无ETF数据'}

    common_dates = None
    for name, df in all_data.items():
        if common_dates is None:
            common_dates = set(df.index)
        else:
            common_dates = common_dates & set(df.index)

    if not common_dates:
        return {'error': '无共同交易日期'}

    common_dates = sorted(common_dates)
    date_set = set(common_dates)

    strategy_nav = [initial_capital]
    benchmark_nav = [initial_capital]
    dates_list = [common_dates[0]]

    weekly_check_dates = []
    for i, d in enumerate(common_dates):
        if i == 0:
            weekly_check_dates.append(d)
        else:
            prev_d = common_dates[i - 1]
            if d.isocalendar()[1] != prev_d.isocalendar()[1] or d.year != prev_d.year:
                weekly_check_dates.append(d)

    for name, df in all_data.items():
        all_data[name] = df[df.index.isin(date_set)]

    start_idx = MOMENTUM_SHORT + 5

    strategy_holdings = []
    benchmark_value = initial_capital
    current_capital = initial_capital

    for i in range(start_idx, len(common_dates)):
        current_date = common_dates[i]
        prev_date = common_dates[i - 1]

        is_rebalance = current_date in weekly_check_dates

        if is_rebalance or not strategy_holdings:
            momentums = {}
            for name, df in all_data.items():
                idx = df.index.get_loc(current_date) if current_date in df.index else -1
                if idx >= MOMENTUM_SHORT:
                    sub_df = df.iloc[idx - MOMENTUM_SHORT:idx + 1]
                    mom = calc_etf_momentum(sub_df, MOMENTUM_SHORT)
                    momentums[name] = mom
                else:
                    momentums[name] = -999

            sorted_mom = sorted(momentums.items(), key=lambda x: x[1], reverse=True)
            all_neg = all(v < 0 for _, v in sorted_mom)

            if all_neg or not sorted_mom:
                strategy_holdings = []
            else:
                top_names = [sorted_mom[0][0], sorted_mom[1][0]]
                strategy_holdings = []
                for name in top_names:
                    df_in_date = all_data[name].loc[:current_date]
                    if not df_in_date.empty:
                        strategy_holdings.append({
                            'name': name,
                            'code': ETF_POOL.get(name, ''),
                            'buy_date': current_date,
                            'buy_price': df_in_date['close'].iloc[-1],
                        })

        if strategy_holdings:
            daily_return = 0
            for holding in strategy_holdings:
                name = holding['name']
                df_h = all_data[name].loc[:current_date]
                if len(df_h) >= 2 and 'close' in df_h.columns:
                    prev_close = df_h['close'].iloc[-2] if len(df_h) >= 2 else df_h['close'].iloc[-1]
                    curr_close = df_h['close'].iloc[-1]
                    if prev_close > 0:
                        ret = (curr_close / prev_close - 1) / len(strategy_holdings)
                        daily_return += ret

            current_capital *= (1 + daily_return)
        else:
            current_capital *= (1 + 0.02 / 365)

        strategy_nav.append(current_capital)

        bm_ret = 0
        bm_count = 0
        for name in list(ETF_POOL.keys())[:3]:
            name_map = {v: k for k, v in ETF_POOL.items()}
            try:
                df_bm = list(all_data.values())[0].loc[:current_date]
                if len(df_bm) >= 2:
                    prev_bm = df_bm['close'].iloc[-2]
                    curr_bm = df_bm['close'].iloc[-1]
                    if prev_bm > 0:
                        bm_ret += (curr_bm / prev_bm - 1)
                        bm_count += 1
            except (IndexError, KeyError):
                continue

        if bm_count > 0:
            bm_ret /= bm_count
        benchmark_value *= (1 + bm_ret)
        benchmark_nav.append(benchmark_value)

        dates_list.append(current_date)

    strategy_series = pd.Series(strategy_nav, index=dates_list)
    benchmark_series = pd.Series(benchmark_nav, index=dates_list)

    total_return = (strategy_series.iloc[-1] / strategy_series.iloc[0] - 1) * 100
    bm_total_return = (benchmark_series.iloc[-1] / benchmark_series.iloc[0] - 1) * 100

    daily_returns = strategy_series.pct_change().dropna()
    years = (dates_list[-1] - dates_list[0]).days / 365.25
    annual_return = ((1 + total_return / 100) ** (1 / max(years, 0.01)) - 1) * 100

    rolling_max = strategy_series.expanding().max()
    drawdown = (strategy_series - rolling_max) / rolling_max * 100
    max_drawdown = drawdown.min()

    if len(daily_returns) > 0:
        excess_returns = daily_returns - RISK_FREE_RATE / 252
        if excess_returns.std() > 0:
            sharpe = np.sqrt(252) * excess_returns.mean() / excess_returns.std()
        else:
            sharpe = 0
    else:
        sharpe = 0

    bm_daily_returns = benchmark_series.pct_change().dropna()
    bm_rolling_max = benchmark_series.expanding().max()
    bm_drawdown = (benchmark_series - bm_rolling_max) / bm_rolling_max * 100
    bm_max_drawdown = bm_drawdown.min()

    result = {
        'initial_capital': initial_capital,
        'final_value': round(strategy_series.iloc[-1], 2),
        'total_return': round(total_return, 2),
        'annual_return': round(annual_return, 2),
        'max_drawdown': round(max_drawdown, 2),
        'sharpe_ratio': round(sharpe, 2),
        'benchmark_return': round(bm_total_return, 2),
        'benchmark_max_drawdown': round(bm_max_drawdown, 2),
        'years': round(years, 2),
        'strategy_nav': strategy_series,
        'benchmark_nav': benchmark_series,
        'start_date': dates_list[0].strftime('%Y-%m-%d'),
        'end_date': dates_list[-1].strftime('%Y-%m-%d'),
    }

    logger.info(f'ETF回测完成: 年化{annual_return:.1f}%, 最大回撤{max_drawdown:.1f}%, '
                f'夏普{sharpe:.2f}')
    return result

# ==================== 可视化 ====================

def plot_etf_backtest(backtest_result: Dict, save: bool = True) -> Optional[str]:
    if 'strategy_nav' not in backtest_result or 'benchmark_nav' not in backtest_result:
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 10),
                              gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(f'ETF动量轮动回测结果 ({backtest_result["start_date"]} ~ {backtest_result["end_date"]})',
                 fontsize=14, fontweight='bold')

    ax1 = axes[0]
    ax1.plot(backtest_result['strategy_nav'].index,
             backtest_result['strategy_nav'].values,
             label=f'策略: {backtest_result["total_return"]:+.1f}%',
             color='#E74C3C', linewidth=1.5)
    ax1.plot(backtest_result['benchmark_nav'].index,
             backtest_result['benchmark_nav'].values,
             label=f'基准: {backtest_result["benchmark_return"]:+.1f}%',
             color='#3498DB', linewidth=1.5, alpha=0.7)
    ax1.legend(loc='best', fontsize=11)
    ax1.set_ylabel('资金曲线', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_title('策略 vs 基准 净值曲线', fontsize=11)

    ax2 = axes[1]
    strategy_series = backtest_result['strategy_nav']
    rolling_max = strategy_series.expanding().max()
    drawdown = (strategy_series - rolling_max) / rolling_max * 100
    ax2.fill_between(drawdown.index, 0, drawdown.values,
                      color='#E74C3C', alpha=0.4, label='回撤')
    ax2.axhline(y=backtest_result['max_drawdown'],
                color='red', linestyle='--', alpha=0.5,
                label=f"最大回撤 {backtest_result['max_drawdown']:.1f}%")
    ax2.set_ylabel('回撤 (%)', fontsize=11)
    ax2.legend(loc='best', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_title('策略回撤曲线', fontsize=11)

    plt.tight_layout()

    if save:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, 'etf_backtest.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f'回测曲线已保存: {path}')
        return path

    plt.close(fig)
    return None


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== ETF轮动模块测试 ===')

    signal = get_weekly_rotation_signal()
    print(f'\n轮动信号 ({signal["signal_date"]}):')
    if signal['defensive']:
        print('  防御模式: 全部转避险')
    else:
        for h in signal['holdings']:
            print(f'  持有: {h["name"]} (动量: {h["momentum"]}%)')

    print(f'\n全部ETF动量:')
    for name, mom in signal.get('all_momentum', {}).items():
        print(f'  {name}: {mom}%')

    print('\n=== ETF回测 ===')
    bt = run_etf_backtest()
    if 'error' not in bt:
        print(f'\n回测期间: {bt["start_date"]} ~ {bt["end_date"]} ({bt["years"]}年)')
        print(f'累计收益: {bt["total_return"]:+.1f}% (基准: {bt["benchmark_return"]:+.1f}%)')
        print(f'年化收益: {bt["annual_return"]:+.1f}%')
        print(f'最大回撤: {bt["max_drawdown"]:.1f}%')
        print(f'夏普比率: {bt["sharpe_ratio"]:.2f}')

        plot_etf_backtest(bt)
