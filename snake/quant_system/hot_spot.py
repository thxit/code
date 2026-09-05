"""
需求4: 热点识别模块
通过成交额与20日均量比发现资金异动，统计涨停行业聚集，输出每日核心热点简报
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

from config import SW_SECTORS, VOLUME_RATIO_THRESHOLD, REPORT_DIR
from data_fetcher import (
    get_all_stocks_quote, get_limit_up_stocks,
    get_limit_up_sector_distribution, get_sector_daily
)

logger = logging.getLogger(__name__)


# ==================== 资金异动检测 ====================

def detect_volume_anomaly(
    use_cache: bool = True
) -> pd.DataFrame:
    """通过成交额与20日均量比（>1.5倍）发现资金异动"""
    stocks = get_all_stocks_quote(use_cache=use_cache)
    if stocks.empty or 'amount' not in stocks.columns:
        logger.warning('个股行情数据不足，无法检测资金异动')
        return pd.DataFrame()

    df = stocks.copy()
    df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
    df = df.dropna(subset=['amount'])

    if len(df) < 50:
        return pd.DataFrame()

    median_amount = df['amount'].median()
    df['volume_ratio'] = df['amount'] / median_amount
    anomalies = df[df['volume_ratio'] >= VOLUME_RATIO_THRESHOLD].copy()

    anomalies['anomaly_level'] = anomalies['volume_ratio'].apply(
        lambda x: '★★★' if x >= 3 else ('★★' if x >= 2 else '★')
    )
    anomalies.sort_values('volume_ratio', ascending=False, inplace=True)

    logger.info(f'资金异动检测: {len(anomalies)}只个股异动 (量比>{VOLUME_RATIO_THRESHOLD})')

    return anomalies

def detect_sector_volume_anomaly(use_cache: bool = True) -> pd.DataFrame:
    """检测行业板块的资金异动"""
    records = []
    for sector in SW_SECTORS:
        df = get_sector_daily(sector, count=30, use_cache=use_cache)
        if df.empty or 'amount' not in df.columns or 'volume' not in df.columns:
            continue

        amounts = df['amount'].dropna()
        if len(amounts) < 20:
            continue

        current_vol = amounts.iloc[-1]
        avg_vol = amounts.tail(20).iloc[:-1].mean() if len(amounts) > 1 else amounts.mean()

        if avg_vol <= 0:
            continue

        vol_ratio = current_vol / avg_vol

        if vol_ratio >= 1.3:
            records.append({
                'sector': sector,
                'current_amount': current_vol,
                'avg_20d_amount': avg_vol,
                'volume_ratio': round(vol_ratio, 2),
            })

    result = pd.DataFrame(records).sort_values('volume_ratio', ascending=False)
    if not result.empty:
        logger.info(f'行业资金异动: {len(result)}个行业放量 (量比>1.3)')

    return result

# ==================== 涨停行业聚集分析 ====================

def analyze_limit_up_clustering(use_cache: bool = True) -> Dict:
    """统计涨停行业聚集，识别热点方向"""
    limit_dist = get_limit_up_sector_distribution()
    if limit_dist.empty:
        return {'hot_sectors': [], 'total_limit': 0, 'clustering_level': '低'}

    total_limit = limit_dist['limit_up_count'].sum()
    limit_dist['ratio'] = (limit_dist['limit_up_count'] / total_limit * 100).round(1)
    limit_dist.sort_values('limit_up_count', ascending=False, inplace=True)

    hot_sectors = limit_dist[limit_dist['limit_up_count'] >= 3].head(10)

    if len(hot_sectors) >= 5:
        clustering_level = '高'
    elif len(hot_sectors) >= 3:
        clustering_level = '中'
    else:
        clustering_level = '低'

    result = {
        'hot_sectors': hot_sectors.to_dict('records') if not hot_sectors.empty else [],
        'total_limit': total_limit,
        'clustering_level': clustering_level,
        'top_sector': hot_sectors.iloc[0]['sector'] if not hot_sectors.empty else '无',
        'top_sector_count': int(hot_sectors.iloc[0]['limit_up_count']) if not hot_sectors.empty else 0,
    }

    logger.info(f'涨停聚集分析: {total_limit}只涨停, 热点集中度{clustering_level}')
    return result

# ==================== 热点综合分析 ====================

def get_hot_spot_briefing(use_cache: bool = True) -> Dict:
    """输出每日核心热点简报"""
    briefing = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'volume_anomalies': {
            'stock_count': 0,
            'top_anomalies': [],
            'sector_anomalies': [],
        },
        'limit_up_analysis': {
            'total_limit': 0,
            'hot_sectors': [],
            'clustering_level': '低',
            'top_sector': '无',
        },
        'summary': '',
    }

    sector_vol = detect_sector_volume_anomaly(use_cache=use_cache)
    if not sector_vol.empty:
        briefing['volume_anomalies']['sector_anomalies'] = (
            sector_vol.head(8).to_dict('records')
        )

    limit_analysis = analyze_limit_up_clustering(use_cache=use_cache)
    briefing['limit_up_analysis'] = {
        'total_limit': limit_analysis['total_limit'],
        'hot_sectors': limit_analysis['hot_sectors'][:5]
            if limit_analysis['hot_sectors'] else [],
        'clustering_level': limit_analysis['clustering_level'],
        'top_sector': limit_analysis['top_sector'],
        'top_sector_count': limit_analysis['top_sector_count'],
    }

    summary_parts = []

    if limit_analysis['total_limit'] > 0:
        summary_parts.append(
            f"今日涨停{limit_analysis['total_limit']}只, "
            f"热点集中在{limit_analysis['top_sector']}等板块"
        )

    hot_sectors_list = limit_analysis['hot_sectors'][:3]
    if hot_sectors_list:
        sector_names = [s['sector'] for s in hot_sectors_list]
        summary_parts.append(f"核心热点: {' > '.join(sector_names)}")

    if not sector_vol.empty:
        top_sectors = sector_vol.head(3)['sector'].tolist()
        summary_parts.append(f"资金异动行业: {', '.join(top_sectors)}")

    briefing['summary'] = ' | '.join(summary_parts) if summary_parts else '无明显热点'

    return briefing


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 热点识别模块测试 ===')

    briefing = get_hot_spot_briefing()
    print(f'\n日期: {briefing["date"]}')
    print(f'\n涨停分析:')
    print(f'  涨停总数: {briefing["limit_up_analysis"]["total_limit"]}')
    print(f'  核心热点: {briefing["limit_up_analysis"]["top_sector"]}')
    print(f'  集中度: {briefing["limit_up_analysis"]["clustering_level"]}')

    if briefing['limit_up_analysis']['hot_sectors']:
        print(f'\n热点板块:')
        for s in briefing['limit_up_analysis']['hot_sectors'][:5]:
            print(f'  {s["sector"]}: {s["limit_up_count"]}只涨停 ({s["ratio"]}%)')

    print(f'\n资金异动行业:')
    for s in briefing['volume_anomalies']['sector_anomalies'][:5]:
        print(f'  {s["sector"]}: 量比{s["volume_ratio"]}')

    print(f'\n简报摘要: {briefing["summary"]}')
