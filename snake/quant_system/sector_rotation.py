"""
需求3: 板块轮动模块
计算行业20日/60日动量排名，筛选强势板块（均线向上过滤），输出轮动信号并绘制动量热力图
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Tuple, Optional

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

from config import SW_SECTORS, MOMENTUM_SHORT, MOMENTUM_LONG, REPORT_DIR
from data_fetcher import get_sector_daily, get_all_sectors

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC',
                                     'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 动量计算 ====================

def calc_momentum(df: pd.DataFrame, period: int) -> float:
    if df.empty or 'close' not in df.columns:
        return 0.0
    close = df['close'].dropna()
    if len(close) < period:
        return 0.0
    return (close.iloc[-1] / close.iloc[-period] - 1) * 100

def calc_ma_direction(df: pd.DataFrame, window: int = 20) -> str:
    if df.empty or 'close' not in df.columns:
        return '未知'
    ma = df['close'].rolling(window=window).mean().dropna()
    if len(ma) < 5:
        return '未知'
    recent = ma.tail(5).values
    if recent[-1] > recent[0] * 1.005:
        return '向上'
    elif recent[-1] < recent[0] * 0.995:
        return '向下'
    else:
        return '走平'

# ==================== 板块轮动分析 ====================

def analyze_sector_rotation(
    use_cache: bool = True
) -> pd.DataFrame:
    sectors = get_all_sectors(count=max(MOMENTUM_LONG, 80), use_cache=use_cache)
    if not sectors:
        logger.warning('未获取到行业板块数据')
        return pd.DataFrame()

    records = []
    for name, df in sectors.items():
        if df.empty or 'close' not in df.columns:
            continue

        momentum_20 = calc_momentum(df, MOMENTUM_SHORT)
        momentum_60 = calc_momentum(df, MOMENTUM_LONG)
        ma20_dir = calc_ma_direction(df, 20)
        ma60_dir = calc_ma_direction(df, 60)

        combined_momentum = momentum_20 * 0.6 + momentum_60 * 0.4
        ma_up = ma20_dir == '向上' or ma60_dir == '向上'

        records.append({
            'sector': name,
            'momentum_20d': round(momentum_20, 2),
            'momentum_60d': round(momentum_60, 2),
            'combined_momentum': round(combined_momentum, 2),
            'ma20_direction': ma20_dir,
            'ma60_direction': ma60_dir,
            'ma_up': ma_up,
            'rank_20d': 0,
            'rank_60d': 0,
        })

    if not records:
        return pd.DataFrame()

    result = pd.DataFrame(records)
    result['rank_20d'] = result['momentum_20d'].rank(ascending=False, method='min')
    result['rank_60d'] = result['momentum_60d'].rank(ascending=False, method='min')
    result['rank_combined'] = result['combined_momentum'].rank(ascending=False, method='min')
    result.sort_values('combined_momentum', ascending=False, inplace=True)
    result.reset_index(drop=True, inplace=True)
    result.index = result.index + 1

    return result

def get_rotation_signal(df: pd.DataFrame, top_n: int = 8) -> Dict:
    if df.empty:
        return {'signals': [], 'defensive': True}

    strong_sectors = df[df['ma_up']].head(top_n).copy()
    weak_sectors = df[~df['ma_up']].tail(top_n).copy()

    hot_sectors = df[df['combined_momentum'] > 5].copy() if 'combined_momentum' in df.columns else df.head(5).copy()

    top_momentum = df[df['combined_momentum'] > 5]
    if top_momentum.empty:
        hot_list = df.head(3)
    else:
        hot_list = top_momentum.head(5)

    signals = []
    for _, row in hot_list.iterrows():
        signals.append({
            'sector': row['sector'],
            'momentum_20d': row['momentum_20d'],
            'momentum_60d': row['momentum_60d'],
            'combined_momentum': row['combined_momentum'],
            'ma20_dir': row['ma20_direction'],
            'ma60_dir': row['ma60_direction'],
            'rank': int(row['rank_combined']),
        })

    defensive = signals == []

    return {
        'signals': signals,
        'defensive': defensive,
        'strong_count': len(strong_sectors),
        'total_sectors': len(df),
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
    }

# ==================== 可视化 ====================

def plot_momentum_heatmap(df: pd.DataFrame, save: bool = True) -> Optional[str]:
    if df.empty:
        return None

    plot_data = df.set_index('sector')
    plot_data = plot_data.head(25)

    fig, axes = plt.subplots(1, 2, figsize=(16, 10))
    fig.suptitle(f'申万一级行业动量热力图 ({datetime.now().strftime("%Y-%m-%d")})',
                 fontsize=14, fontweight='bold')

    # 20日动量
    ax1 = axes[0]
    momentum_20 = plot_data[['momentum_20d']].sort_values('momentum_20d')
    colors_20 = ['#E74C3C' if v > 0 else '#2ECC71' for v in momentum_20['momentum_20d']]
    ax1.barh(range(len(momentum_20)), momentum_20['momentum_20d'].values,
             color=colors_20, alpha=0.7)
    ax1.set_yticks(range(len(momentum_20)))
    ax1.set_yticklabels(momentum_20.index, fontsize=9)
    ax1.set_xlabel(f'{MOMENTUM_SHORT}日动量 (%)', fontsize=11)
    ax1.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
    ax1.grid(True, alpha=0.3, axis='x')

    # 60日动量
    ax2 = axes[1]
    momentum_60 = plot_data[['momentum_60d']].sort_values('momentum_60d')
    colors_60 = ['#E74C3C' if v > 0 else '#2ECC71' for v in momentum_60['momentum_60d']]
    ax2.barh(range(len(momentum_60)), momentum_60['momentum_60d'].values,
             color=colors_60, alpha=0.7)
    ax2.set_yticks(range(len(momentum_60)))
    ax2.set_yticklabels(momentum_60.index, fontsize=9)
    ax2.set_xlabel(f'{MOMENTUM_LONG}日动量 (%)', fontsize=11)
    ax2.axvline(x=0, color='gray', linestyle='-', linewidth=0.5)
    ax2.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()

    if save:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, 'sector_momentum_heatmap.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f'动量热力图已保存: {path}')
        return path

    plt.close(fig)
    return None

def plot_sector_rotation_chart(df: pd.DataFrame, save: bool = True) -> Optional[str]:
    if df.empty or len(df) < 5:
        return None

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.suptitle(f'行业板块轮动图 ({datetime.now().strftime("%Y-%m-%d")})',
                 fontsize=14, fontweight='bold')

    top20 = df.head(20).copy()
    colors = ['#E74C3C' if r['combined_momentum'] > 0 else '#2ECC71'
              for _, r in top20.iterrows()]
    sizes = [abs(r['combined_momentum']) * 10 + 20 for _, r in top20.iterrows()]

    scatter = ax.scatter(top20['momentum_20d'], top20['momentum_60d'],
                         c=colors, s=sizes, alpha=0.6, edgecolors='gray', linewidth=0.5)

    for _, row in top20.iterrows():
        ax.annotate(row['sector'][:4],
                     (row['momentum_20d'], row['momentum_60d']),
                     fontsize=7, alpha=0.8,
                     ha='center', va='bottom')

    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x=0, color='gray', linestyle='--', alpha=0.5)
    ax.set_xlabel(f'{MOMENTUM_SHORT}日动量 (%)', fontsize=11)
    ax.set_ylabel(f'{MOMENTUM_LONG}日动量 (%)', fontsize=11)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, 'sector_rotation_chart.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f'板块轮动图已保存: {path}')
        return path

    plt.close(fig)
    return None

# ==================== 主函数 ====================

def run_sector_rotation(use_cache: bool = True) -> Dict:
    result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'top_sectors': [],
        'rotation_signal': None,
        'defensive': False,
        'charts': {},
    }

    df = analyze_sector_rotation(use_cache=use_cache)
    if df.empty:
        logger.warning('板块轮动分析无数据')
        result['defensive'] = True
        return result

    signal = get_rotation_signal(df)
    result['rotation_signal'] = signal
    result['defensive'] = signal['defensive']

    top10 = df.head(10)
    for _, row in top10.iterrows():
        result['top_sectors'].append({
            'rank': int(row['rank_combined']),
            'sector': row['sector'],
            'momentum_20d': row['momentum_20d'],
            'momentum_60d': row['momentum_60d'],
            'ma20_dir': row['ma20_direction'],
            'ma60_dir': row['ma60_direction'],
        })

    heatmap_path = plot_momentum_heatmap(df)
    if heatmap_path:
        result['charts']['heatmap'] = heatmap_path

    chart_path = plot_sector_rotation_chart(df)
    if chart_path:
        result['charts']['rotation_chart'] = chart_path

    logger.info(f'板块轮动分析完成: {len(result["top_sectors"])}个强势板块')
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 板块轮动模块测试 ===')

    result = run_sector_rotation()
    print(f'\n分析日期: {result["date"]}')
    print(f'防御模式: {result["defensive"]}')

    print(f'\n前10强势板块:')
    print(f'{"排名":<5} {"板块":<8} {"20日动量":<10} {"60日动量":<10} {"MA20方向":<8}')
    print('-'*45)
    for s in result['top_sectors']:
        print(f'{s["rank"]:<5} {s["sector"]:<8} {s["momentum_20d"]:<10.2f} '
              f'{s["momentum_60d"]:<10.2f} {s["ma20_dir"]:<8}')
