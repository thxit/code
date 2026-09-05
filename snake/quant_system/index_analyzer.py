"""
需求2: 指数分析模块
计算MA20/MA60均线趋势、指数PE历史分位数，综合评分判定，可视化K线与均线
"""

import os
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import mplfinance as mpf

from config import (
    INDEX_CONFIG, MA_SHORT, MA_LONG,
    INDEX_SCORE_THRESHOLDS, REPORT_DIR
)
from data_fetcher import get_index_daily, get_index_pe, get_all_indices

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC',
                                     'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 均线计算 ====================

def calc_ma(df: pd.DataFrame, window: int) -> pd.Series:
    if 'close' not in df.columns or df.empty:
        return pd.Series(dtype=float)
    return df['close'].rolling(window=window).mean()

def calc_ma_trend(ma_series: pd.Series) -> str:
    if len(ma_series) < 5:
        return '未知'
    recent = ma_series.dropna().tail(5).values
    if len(recent) < 5:
        return '未知'
    if recent[-1] > recent[0] * 1.01:
        return '上行'
    elif recent[-1] < recent[0] * 0.99:
        return '下行'
    else:
        return '震荡'

# ==================== PE分析 ====================

def analyze_pe(name: str, code: str) -> Dict:
    pe_data = get_index_pe(name, code)
    if pe_data is None:
        return {'score': 50, 'detail': 'PE数据不可用'}

    percentile = pe_data['pe_percentile']
    if percentile < 20:
        score = 80
        eval_text = '低估'
    elif percentile < 40:
        score = 65
        eval_text = '偏低'
    elif percentile < 60:
        score = 50
        eval_text = '适中'
    elif percentile < 80:
        score = 35
        eval_text = '偏高'
    else:
        score = 20
        eval_text = '高估'

    return {
        'score': score,
        'current_pe': pe_data['current_pe'],
        'percentile': percentile,
        'min_pe': pe_data['pe_min'],
        'max_pe': pe_data['pe_max'],
        'mean_pe': pe_data['pe_mean'],
        'evaluation': eval_text,
    }

# ==================== 综合评分 ====================

def score_index(name: str, df: pd.DataFrame, pe_code: str) -> Dict:
    result = {
        'name': name,
        'ma20_score': 50,
        'ma60_score': 50,
        'trend_score': 50,
        'pe_score': 50,
        'total_score': 50,
        'judgment': '中性',
        'details': {},
    }

    if df.empty:
        return result

    ma20 = calc_ma(df, MA_SHORT)
    ma60 = calc_ma(df, MA_LONG)
    close = df['close']

    # MA20评分: 价格在MA20上方加分
    if not ma20.dropna().empty and not close.dropna().empty:
        latest_close = close.iloc[-1]
        latest_ma20 = ma20.iloc[-1]
        if pd.notna(latest_ma20):
            ratio = (latest_close / latest_ma20 - 1) * 100
            if ratio > 3:
                ma20_score = 85
            elif ratio > 1:
                ma20_score = 70
            elif ratio > -1:
                ma20_score = 55
            elif ratio > -3:
                ma20_score = 40
            else:
                ma20_score = 25
        else:
            ma20_score = 50
    else:
        ma20_score = 50
    result['ma20_score'] = ma20_score

    # MA60评分: 价格在MA60上方加分
    if not ma60.dropna().empty and not close.dropna().empty:
        latest_ma60 = ma60.iloc[-1]
        if pd.notna(latest_ma60):
            ratio = (latest_close / latest_ma60 - 1) * 100
            if ratio > 3:
                ma60_score = 85
            elif ratio > 1:
                ma60_score = 70
            elif ratio > -1:
                ma60_score = 55
            elif ratio > -3:
                ma60_score = 40
            else:
                ma60_score = 25
        else:
            ma60_score = 50
    else:
        ma60_score = 50
    result['ma60_score'] = ma60_score

    # 趋势评分: 均线方向
    ma20_trend = calc_ma_trend(ma20)
    ma60_trend = calc_ma_trend(ma60)
    trend_scores = {'上行': 80, '震荡': 55, '下行': 25, '未知': 50}
    trend_score = (trend_scores.get(ma20_trend, 50) * 0.6 +
                   trend_scores.get(ma60_trend, 50) * 0.4)
    result['trend_score'] = trend_score
    result['details']['ma20_trend'] = ma20_trend
    result['details']['ma60_trend'] = ma60_trend

    # PE评分
    pe_code_full = pe_code
    pe_result = analyze_pe(name, pe_code_full)
    result['pe_score'] = pe_result['score']
    result['details']['pe'] = pe_result

    # 综合评分 (均线60% + PE40%)
    total = (ma20_score * 0.25 + ma60_score * 0.25 +
             trend_score * 0.10 + pe_result['score'] * 0.40)
    result['total_score'] = round(total, 1)

    # 判定
    if total >= 60:
        result['judgment'] = '适宜操作'
    elif total >= 40:
        result['judgment'] = '中性'
    else:
        result['judgment'] = '防御'

    return result

# ==================== K线可视化 ====================

def plot_index_kline(name: str, df: pd.DataFrame,
                     save: bool = True) -> Optional[str]:
    if df.empty or 'close' not in df.columns:
        logger.warning(f'指数 [{name}] 数据不足，无法绘图')
        return None

    fig, axes = plt.subplots(2, 1, figsize=(14, 9),
                              gridspec_kw={'height_ratios': [3, 1]})
    fig.suptitle(f'{name} 走势分析 ({datetime.now().strftime("%Y-%m-%d")})',
                 fontsize=14, fontweight='bold')

    ax1, ax2 = axes

    # K线 + 均线
    ma20 = calc_ma(df, MA_SHORT)
    ma60 = calc_ma(df, MA_LONG)

    ax1.plot(df.index, df['close'], label='收盘价', color='#333', linewidth=1.5)
    ax1.plot(df.index, ma20, label=f'MA{MA_SHORT}', color='#E67E22', linewidth=1.2)
    ax1.plot(df.index, ma60, label=f'MA{MA_LONG}', color='#2980B9', linewidth=1.2)

    latest = df.iloc[-1]
    if 'close' in latest:
        ax1.axhline(y=latest['close'], color='gray', linestyle='--',
                    alpha=0.3, linewidth=0.8)

    ax1.legend(loc='best', fontsize=10)
    ax1.set_ylabel('点位', fontsize=11)
    ax1.grid(True, alpha=0.3)
    ax1.set_title(f'价格走势与MA{MA_SHORT}/MA{MA_LONG}均线', fontsize=11)

    # 成交量
    if 'volume' in df.columns:
        diffs = df['close'].diff().fillna(0)
        colors = ['#e74c3c' if v > 0 else '#2ecc71' for v in diffs]
        ax2.bar(df.index, df['volume'], color=colors, alpha=0.4, width=1)
        ax2.set_ylabel('成交量', fontsize=11)
        ax2.grid(True, alpha=0.3)

    ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    plt.xticks(rotation=45)

    plt.tight_layout()

    if save:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, f'{name}_kline.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f'K线图已保存: {path}')
        return path

    plt.close(fig)
    return None

def plot_index_pe(name: str, pe_data: Dict) -> Optional[str]:
    if pe_data is None:
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.suptitle(f'{name} PE估值分析', fontsize=13, fontweight='bold')

    metrics = ['current_pe', 'min_pe', 'max_pe', 'mean_pe', 'pe_percentile']
    labels = ['当前PE', '最低PE', '最高PE', '平均PE', 'PE分位数(%)']
    values = [pe_data.get(m, 0) for m in metrics]

    bars = ax.bar(labels, values, color=['#E74C3C', '#2ECC71', '#3498DB',
                                          '#F39C12', '#9B59B6'], alpha=0.7)

    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                str(val), ha='center', va='bottom', fontsize=10)

    ax.set_ylabel('数值', fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    plt.tight_layout()

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, f'{name}_pe.png')
    plt.savefig(path, dpi=150, bbox_inches='tight')
    plt.close(fig)
    return path

# ==================== 主函数 ====================

def analyze_all_indices(use_cache: bool = True) -> Dict:
    indices = get_all_indices(count=120, use_cache=use_cache)
    results = {}

    for name, df in indices.items():
        code = INDEX_CONFIG[name]
        result = score_index(name, df, code)

        pe_data = get_index_pe(name, code)
        result['details']['pe_data'] = pe_data

        plot_index_kline(name, df)
        if pe_data:
            plot_index_pe(name, pe_data)

        results[name] = result
        logger.info(f'指数 [{name}] 评分: {result["total_score"]} -> {result["judgment"]}')

    return results


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 指数分析模块测试 ===')

    results = analyze_all_indices()
    print(f'\n{"="*60}')
    for name, r in results.items():
        print(f'{name}: 评分 {r["total_score"]} -> {r["judgment"]}')
        details = r['details']
        pe = details.get('pe', {})
        print(f'  PE: {pe.get("current_pe", "N/A")} '
              f'(分位: {pe.get("percentile", "N/A")}%)')
        print(f'  均线: MA20 {details.get("ma20_trend", "N/A")}, '
              f'MA60 {details.get("ma60_trend", "N/A")}')
