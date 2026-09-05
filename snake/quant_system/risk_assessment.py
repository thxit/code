"""
需求7: 综合风险评估模块
整合指数评分、板块动量衰减、情绪极端、热点切换四个维度，生成0-100风险分并划分等级
"""

import os
import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from config import RISK_WEIGHTS, RISK_LEVELS, REPORT_DIR
from index_analyzer import analyze_all_indices
from sector_rotation import analyze_sector_rotation
from sentiment import compute_sentiment_score
from hot_spot import get_hot_spot_briefing

logger = logging.getLogger(__name__)

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'PingFang SC',
                                     'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ==================== 维度评分 ====================

def score_index_dimension(use_cache: bool = True) -> Dict:
    """指数评分维度：指数评分越低风险越高"""
    index_results = analyze_all_indices(use_cache=use_cache)
    if not index_results:
        return {'score': 50, 'detail': '指数数据不可用'}

    scores = [r['total_score'] for r in index_results.values()]
    avg_score = np.mean(scores)

    risk_score = 100 - avg_score
    risk_score = max(0, min(100, risk_score))

    min_score = min(scores)
    max_score = max(scores)

    worst_index = [n for n, r in index_results.items()
                   if r['total_score'] == min_score][0]
    best_index = [n for n, r in index_results.items()
                  if r['total_score'] == max_score][0]

    return {
        'score': round(risk_score, 1),
        'avg_index_score': round(avg_score, 1),
        'best_index': best_index,
        'worst_index': worst_index,
        'detail': f'指数均分{avg_score:.1f}, 最优{best_index}, 最弱{worst_index}',
    }

def score_momentum_dimension(use_cache: bool = True) -> Dict:
    """板块动量衰减维度：强势板块减少/动量衰减 => 风险上升"""
    sector_df = analyze_sector_rotation(use_cache=use_cache)
    if sector_df.empty:
        return {'score': 50, 'detail': '板块数据不可用'}

    positive_momentum = (sector_df['combined_momentum'] > 0).sum()
    total = len(sector_df)
    positive_ratio = positive_momentum / total if total > 0 else 0

    avg_momentum = sector_df['combined_momentum'].mean()
    top5_avg = sector_df['combined_momentum'].head(5).mean()
    momentum_strength = top5_avg / max(abs(avg_momentum), 1)

    if positive_ratio > 0.7:
        decay_score = 15
    elif positive_ratio > 0.5:
        decay_score = 30
    elif positive_ratio > 0.3:
        decay_score = 50
    elif positive_ratio > 0.15:
        decay_score = 70
    else:
        decay_score = 85

    if avg_momentum < -5:
        decay_score = min(decay_score + 10, 100)
    elif avg_momentum > 5:
        decay_score = max(decay_score - 10, 0)

    return {
        'score': round(decay_score, 1),
        'positive_ratio': round(positive_ratio * 100, 1),
        'avg_momentum': round(avg_momentum, 2),
        'top5_avg_momentum': round(top5_avg, 2),
        'detail': (f'强势板块占比{positive_ratio*100:.1f}%, '
                   f'平均动量{avg_momentum:.1f}%'),
    }

def score_sentiment_dimension(use_cache: bool = True) -> Dict:
    """情绪极端维度：情绪过高（亢奋）或过低（恐慌）都对应高风险"""
    sentiment = compute_sentiment_score(use_cache=use_cache)
    score = sentiment['total_score']

    if 40 <= score <= 60:
        risk_score = 10
    elif 30 <= score <= 70:
        risk_score = 25
    elif 20 <= score <= 80:
        risk_score = 50
    elif 10 <= score <= 90:
        risk_score = 70
    else:
        risk_score = 85

    if score > 80:
        risk_score = min(risk_score + 15, 100)
        overheat = True
    elif score < 20:
        risk_score = min(risk_score + 10, 100)
        overheat = False
    else:
        overheat = False

    return {
        'score': round(risk_score, 1),
        'sentiment_score': score,
        'sentiment_level': sentiment['level'],
        'overheat': overheat,
        'detail': f'情绪{score:.1f}({sentiment["level"]})',
    }

def score_hotspot_dimension(use_cache: bool = True) -> Dict:
    """热点切换维度：无明确热点或热点分散 => 风险上升"""
    briefing = get_hot_spot_briefing(use_cache=use_cache)

    limit_analysis = briefing['limit_up_analysis']
    total_limit = limit_analysis['total_limit']
    clustering = limit_analysis['clustering_level']
    hot_sectors = limit_analysis.get('hot_sectors', [])

    if total_limit < 20:
        base_risk = 70
    elif total_limit < 40:
        base_risk = 50
    elif total_limit < 70:
        base_risk = 35
    else:
        base_risk = 25

    if clustering == '高':
        base_risk -= 15
    elif clustering == '中':
        base_risk -= 5
    elif clustering == '低':
        base_risk += 10

    if total_limit == 0:
        base_risk = 80

    base_risk = max(0, min(100, base_risk))

    return {
        'score': round(base_risk, 1),
        'total_limit': total_limit,
        'clustering': clustering,
        'hot_sector_count': len(hot_sectors),
        'top_sector': limit_analysis.get('top_sector', '无'),
        'detail': (f'涨停{total_limit}只, 集中度{clustering}, '
                   f'热点{limit_analysis.get("top_sector", "无")}'),
    }

# ==================== 综合评估 ====================

def assess_comprehensive_risk(use_cache: bool = True) -> Dict:
    """生成0-100风险分并划分低/中/高/极高四档"""
    dimensions = {
        'index_system': score_index_dimension(use_cache=use_cache),
        'momentum_decay': score_momentum_dimension(use_cache=use_cache),
        'sentiment_extreme': score_sentiment_dimension(use_cache=use_cache),
        'hotspot_shift': score_hotspot_dimension(use_cache=use_cache),
    }

    total_risk = 0
    dim_keys = list(RISK_WEIGHTS.keys())
    dim_names = ['index_system', 'momentum_decay', 'sentiment_extreme', 'hotspot_shift']
    for i, dim_key in enumerate(dim_names):
        weight = RISK_WEIGHTS[dim_keys[i]]
        total_risk += dimensions[dim_key]['score'] * weight

    total_risk = round(total_risk, 1)

    level = '未知'
    for low, high, desc in RISK_LEVELS:
        if low <= total_risk < high:
            level = desc
            break
    if total_risk >= 75:
        level = '极高风险'

    suggestions = _get_risk_suggestions(total_risk, dimensions)

    result = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'risk_score': total_risk,
        'risk_level': level,
        'dimensions': dimensions,
        'suggestions': suggestions,
    }

    logger.info(f'综合风险评分: {total_risk} -> {level}')
    return result

def _get_risk_suggestions(
    risk_score: float, dimensions: Dict
) -> List[str]:
    suggestions = []

    if risk_score >= 75:
        suggestions.append('【极高风险】建议空仓或持有现金避险，等待市场企稳')
    elif risk_score >= 50:
        suggestions.append('【高风险】控制仓位在3成以下，仅关注最强板块')
    elif risk_score >= 25:
        suggestions.append('【中风险】仓位5成左右，均衡配置，注意轮动节奏')
    else:
        suggestions.append('【低风险】可积极操作，仓位7-8成，顺势而为')

    if dimensions.get('sentiment_extreme', {}).get('overheat'):
        suggestions.append('情绪过热，警惕短期回调，避免追高')
    elif dimensions.get('sentiment_extreme', {}).get('sentiment_score', 50) < 20:
        suggestions.append('情绪恐慌，关注超跌反弹机会')

    dim = dimensions.get('momentum_decay', {})
    if dim.get('positive_ratio', 50) < 30:
        suggestions.append('板块普跌，赚钱效应差，不宜盲目抄底')

    dim = dimensions.get('hotspot_shift', {})
    if dim.get('total_limit', 0) < 20:
        suggestions.append('涨停家数稀少，市场活跃度低')

    return suggestions

# ==================== 可视化 ====================

def plot_risk_radar(result: Dict, save: bool = True) -> Optional[str]:
    if 'dimensions' not in result:
        return None

    categories = ['指数系统', '动量衰减', '情绪极端', '热点切换']
    dim_names = ['index_system', 'momentum_decay', 'sentiment_extreme', 'hotspot_shift']
    values = [result['dimensions'][d]['score'] for d in dim_names]

    angles = np.linspace(0, 2 * np.pi, len(categories), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6),
                                    subplot_kw={'projection': 'polar'})

    ax1.plot(angles, values, 'o-', linewidth=2, color='#E74C3C')
    ax1.fill(angles, values, alpha=0.25, color='#E74C3C')
    ax1.set_xticks(angles[:-1])
    ax1.set_xticklabels(categories, fontsize=11)
    ax1.set_ylim(0, 100)
    ax1.set_title(f'综合风险评估: {result["risk_score"]}分 - {result["risk_level"]}',
                   fontsize=13, fontweight='bold', pad=20)

    for angle, val, cat in zip(angles[:-1], values[:-1], categories):
        ax1.text(angle, val + 5, f'{val:.0f}', ha='center', fontsize=9)

    ax2.axis('off')
    ax2.text(0.5, 0.85, f'综合风险评分', fontsize=14, fontweight='bold',
             ha='center', transform=ax2.transAxes)
    ax2.text(0.5, 0.65, f'{result["risk_score"]} 分', fontsize=36,
             fontweight='bold',
             color='#E74C3C' if result['risk_score'] >= 50 else '#2ECC71',
             ha='center', transform=ax2.transAxes)
    ax2.text(0.5, 0.50, f'风险等级: {result["risk_level"]}', fontsize=14,
             color='#E74C3C' if result['risk_score'] >= 50 else '#2ECC71',
             ha='center', transform=ax2.transAxes)

    suggestions = result.get('suggestions', [])
    y_pos = 0.35
    for sug in suggestions[:4]:
        ax2.text(0.5, y_pos, f'• {sug}', fontsize=9, ha='center',
                 transform=ax2.transAxes, wrap=True)
        y_pos -= 0.08

    plt.tight_layout()

    if save:
        os.makedirs(REPORT_DIR, exist_ok=True)
        path = os.path.join(REPORT_DIR, 'risk_assessment.png')
        plt.savefig(path, dpi=150, bbox_inches='tight')
        plt.close(fig)
        logger.info(f'风险评估图已保存: {path}')
        return path

    plt.close(fig)
    return None


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 综合风险评估模块测试 ===')

    result = assess_comprehensive_risk()
    print(f'\n日期: {result["date"]}')
    print(f'综合风险评分: {result["risk_score"]} -> {result["risk_level"]}')
    print(f'\n各维度评分:')
    for dim, data in result['dimensions'].items():
        print(f'  {dim}: {data["score"]}分 - {data["detail"]}')

    print(f'\n操作建议:')
    for s in result['suggestions']:
        print(f'  {s}')

    plot_risk_radar(result)
