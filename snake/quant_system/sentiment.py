"""
需求5: 短线情绪模块
构建涨跌比、涨停/跌停数、昨日涨停表现、炸板率、最高连板等指标，合成0-100情绪分数并输出评价
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from config import SENTIMENT_WEIGHTS, SENTIMENT_LEVELS, REPORT_DIR
from data_fetcher import (
    get_all_stocks_quote, get_limit_up_stocks,
    get_stock_kline, is_market_closed_today
)

logger = logging.getLogger(__name__)


# ==================== 基础指标计算 ====================

def calc_up_down_ratio(use_cache: bool = True) -> Tuple[float, int, int, int]:
    """计算涨跌比"""
    stocks = get_all_stocks_quote(use_cache=use_cache)
    if stocks.empty or 'pct_change' not in stocks.columns:
        return 50.0, 0, 0, 0

    df = stocks.copy()
    df['pct_change'] = pd.to_numeric(df['pct_change'], errors='coerce')
    df = df.dropna(subset=['pct_change'])

    up = (df['pct_change'] > 0).sum()
    down = (df['pct_change'] < 0).sum()
    flat = (df['pct_change'] == 0).sum()
    total = up + down + flat

    if total == 0:
        return 50.0, 0, 0, 0

    ratio = up / max(down, 1)
    score = min(ratio / 3 * 100, 100)

    logger.info(f'涨跌比: {up}/{down} ({ratio:.2f}), 评分: {score:.1f}')
    return round(score, 1), up, down, flat

def calc_limit_up_down_ratio(use_cache: bool = True) -> Tuple[float, int, int]:
    """计算涨停/跌停比"""
    limit_up = get_limit_up_stocks(use_cache=use_cache)
    up_count = len(limit_up) if not limit_up.empty else 0

    stocks = get_all_stocks_quote(use_cache=use_cache)
    down_count = 0
    if not stocks.empty and 'pct_change' in stocks.columns:
        df = stocks.copy()
        df['pct_change'] = pd.to_numeric(df['pct_change'], errors='coerce')
        down_count = (df['pct_change'] <= -9.8).sum()

    total = up_count + down_count
    if total == 0:
        ratio_score = 50.0
    else:
        ratio = up_count / max(down_count, 1)
        ratio_score = min(ratio / 5 * 100, 100)

    logger.info(f'涨停/跌停: {up_count}/{down_count}, 评分: {ratio_score:.1f}')
    return round(ratio_score, 1), up_count, down_count

def calc_prev_limit_up_performance(use_cache: bool = True) -> Tuple[float, float]:
    """计算昨日涨停今日表现"""
    limit_df = get_limit_up_stocks(use_cache=use_cache)
    if limit_df.empty:
        return 50.0, 0.0

    codes = limit_df['code'].tolist()[:20]
    if not codes:
        return 50.0, 0.0

    performances = []
    for code in codes:
        try:
            df = get_stock_kline(code, count=5)
            if not df.empty and 'pct_change' in df.columns and len(df) >= 2:
                perf = df['pct_change'].iloc[-1]
                if pd.notna(perf):
                    performances.append(perf)
        except Exception:
            continue

    if not performances:
        return 50.0, 0.0

    avg_perf = np.mean(performances)
    score = min(max((avg_perf + 5) / 10 * 100, 0), 100)

    logger.info(f'昨日涨停表现: {avg_perf:.2f}%, 评分: {score:.1f}')
    return round(score, 1), round(avg_perf, 2)

def calc_break_rate(use_cache: bool = True) -> Tuple[float, float, int, int]:
    """计算炸板率"""
    limit_df = get_limit_up_stocks(use_cache=use_cache)
    if limit_df.empty:
        return 50.0, 0.0, 0, 0

    total_limit = len(limit_df)

    if 'seal_time' in limit_df.columns:
        morning_seals = limit_df[
            limit_df['seal_time'] < '11:30'
        ] if 'seal_time' in limit_df.columns else limit_df
        first_time_seals = morning_seals if len(morning_seals) > 0 else limit_df.head(int(total_limit * 0.6))
        firm_seals = len(first_time_seals)
    else:
        firm_seals = int(total_limit * 0.6)

    broken = total_limit - firm_seals
    if total_limit > 0:
        rate = broken / total_limit * 100
    else:
        rate = 0

    score = max(100 - rate * 2, 0)

    logger.info(f'炸板率: {rate:.1f}% (炸板{broken}/涨停{total_limit}), 评分: {score:.1f}')
    return round(score, 1), round(rate, 1), broken, total_limit

def calc_max_continuous_limit(use_cache: bool = True) -> Tuple[float, int]:
    """计算最高连板数"""
    limit_df = get_limit_up_stocks(use_cache=use_cache)
    if limit_df.empty:
        return 30.0, 0

    codes = limit_df['code'].tolist()[:30]
    max_continuous = 0

    for code in codes:
        try:
            df = get_stock_kline(code, count=20)
            if df.empty or 'pct_change' not in df.columns:
                continue

            pcts = df['pct_change'].dropna().tail(15)
            continuous = 0
            for p in pcts:
                if p >= 9.8:
                    continuous += 1
                else:
                    if continuous > max_continuous:
                        max_continuous = continuous
                    continuous = 0
            if continuous > max_continuous:
                max_continuous = continuous

        except Exception:
            continue

    if max_continuous >= 7:
        score = 90
    elif max_continuous >= 5:
        score = 75
    elif max_continuous >= 3:
        score = 60
    elif max_continuous >= 2:
        score = 45
    elif max_continuous >= 1:
        score = 30
    else:
        score = 20

    logger.info(f'最高连板: {max_continuous}板, 评分: {score:.1f}')
    return round(score, 1), max_continuous

# ==================== 市场宽度 ====================

def calc_market_breadth(use_cache: bool = True) -> Tuple[float, float]:
    """计算市场宽度（站上20日均线比例）"""
    stocks = get_all_stocks_quote(use_cache=use_cache)
    if stocks.empty:
        return 50.0, 0.0

    codes = stocks['code'].tolist()[:200]
    above_ma = 0
    total = 0

    for code in codes:
        try:
            df = get_stock_kline(code, count=25)
            if df.empty or 'close' not in df.columns:
                continue
            ma20 = df['close'].rolling(20).mean()
            if len(ma20.dropna()) > 0 and len(df) > 0:
                if df['close'].iloc[-1] > ma20.iloc[-1]:
                    above_ma += 1
                total += 1
        except Exception:
            continue

    if total == 0:
        return 50.0, 0.0

    ratio = above_ma / total * 100
    score = min(ratio * 1.2, 100)

    logger.info(f'市场宽度: {above_ma}/{total} ({ratio:.1f}%), 评分: {score:.1f}')
    return round(score, 1), round(ratio, 1)

# ==================== 综合情绪评分 ====================

def compute_sentiment_score(use_cache: bool = True) -> Dict:
    """合成0-100情绪分数"""
    components = {}

    score, up, down, flat = calc_up_down_ratio(use_cache=use_cache)
    components['up_down_ratio'] = {
        'score': score, 'up': up, 'down': down,
        'detail': f'{up}/{down}',
    }

    score, up_count, down_count = calc_limit_up_down_ratio(use_cache=use_cache)
    components['limit_up_ratio'] = {
        'score': score, 'limit_up': up_count, 'limit_down': down_count,
        'detail': f'{up_count}/{down_count}',
    }

    score, avg_perf = calc_prev_limit_up_performance(use_cache=use_cache)
    components['prev_limit_up_perf'] = {
        'score': score, 'avg_performance': avg_perf,
        'detail': f'{avg_perf:+.2f}%',
    }

    score, rate, broken, total = calc_break_rate(use_cache=use_cache)
    components['break_rate'] = {
        'score': score, 'rate': rate, 'broken': broken, 'total': total,
        'detail': f'{rate:.1f}%',
    }

    score, max_c = calc_max_continuous_limit(use_cache=use_cache)
    components['max_continuous'] = {
        'score': score, 'boards': max_c,
        'detail': f'{max_c}板',
    }

    score, breadth = calc_market_breadth(use_cache=use_cache)
    components['market_breadth'] = {
        'score': score, 'breadth': breadth,
        'detail': f'{breadth:.1f}%',
    }

    total_score = 0
    for key, weight in SENTIMENT_WEIGHTS.items():
        if key in components:
            total_score += components[key]['score'] * weight

    total_score = round(total_score, 1)

    level = '未知'
    for low, high, desc in SENTIMENT_LEVELS:
        if low <= total_score < high:
            level = desc
            break
    if total_score >= 80:
        level = '极度亢奋'

    result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'total_score': total_score,
        'level': level,
        'components': components,
    }

    logger.info(f'综合情绪评分: {total_score} -> {level}')
    return result


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 短线情绪模块测试 ===')

    result = compute_sentiment_score()
    print(f'\n日期: {result["date"]}')
    print(f'综合情绪评分: {result["total_score"]} -> {result["level"]}')
    print(f'\n分项指标:')
    for key, val in result['components'].items():
        print(f'  {key}: {val["score"]} ({val["detail"]})')
