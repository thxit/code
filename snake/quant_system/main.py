"""
需求8: 系统整合
串联所有模块，每日收盘后自动运行，输出完整量化简报到txt文件和控制台
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional

from config import CACHE_DIR, REPORT_DIR
from data_fetcher import (
    get_all_indices, get_all_stocks_quote, get_limit_up_stocks,
    is_market_closed_today
)
from index_analyzer import analyze_all_indices
from sector_rotation import run_sector_rotation
from hot_spot import get_hot_spot_briefing
from sentiment import compute_sentiment_score
from etf_rotation import get_weekly_rotation_signal, run_etf_backtest, plot_etf_backtest
from risk_assessment import assess_comprehensive_risk, plot_risk_radar

logger = logging.getLogger(__name__)


# ==================== 日志配置 ====================

def setup_logging():
    log_format = '%(asctime)s [%(levelname)s] %(message)s'
    log_file = os.path.join(REPORT_DIR, f'quant_{datetime.now().strftime("%Y%m%d")}.log')

    os.makedirs(REPORT_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout),
        ]
    )


# ==================== 报告生成 ====================

def generate_report(
    index_result: Dict,
    sector_result: Dict,
    hot_spot_result: Dict,
    sentiment_result: Dict,
    etf_signal: Dict,
    etf_backtest: Dict,
    risk_result: Dict,
) -> str:
    lines = []
    sep = '=' * 65
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    lines.append(sep)
    lines.append(f'  A股量化分析系统 - 收盘简报')
    lines.append(f'  生成时间: {now}')
    lines.append(sep)
    lines.append('')

    # ----- 1. 指数分析 -----
    lines.append('【一、指数分析】')
    lines.append('-' * 50)
    for name, r in index_result.items():
        pe = r['details'].get('pe', {})
        pe_str = f"PE{pe.get('current_pe', 'N/A')}(分位{pe.get('percentile', 'N/A')}%)" if pe else 'PE:N/A'
        lines.append(f'  {name:<8} | 评分: {r["total_score"]:<5.1f} | '
                      f'{r["judgment"]:<8} | {pe_str}')
    lines.append('')

    # ----- 2. 板块轮动 -----
    lines.append('【二、板块轮动】')
    lines.append('-' * 50)
    if sector_result.get('defensive'):
        lines.append('  ⚠ 防御模式: 全市场板块动量偏弱')
    else:
        lines.append(f'  强势板块 TOP8:')
        for i, s in enumerate(sector_result.get('top_sectors', [])[:8], 1):
            lines.append(f'  {i}. {s["sector"]:<8} '
                          f'20日动量: {s["momentum_20d"]:+.1f}% '
                          f'60日动量: {s["momentum_60d"]:+.1f}% '
                          f'MA20: {s["ma20_dir"]}')
    lines.append('')

    # ----- 3. 热点识别 -----
    lines.append('【三、热点识别】')
    lines.append('-' * 50)
    limit_info = hot_spot_result.get('limit_up_analysis', {})
    lines.append(f'  涨停总数: {limit_info.get("total_limit", 0)}只')
    lines.append(f'  热点集中度: {limit_info.get("clustering_level", "N/A")}')
    lines.append(f'  核心热点: {limit_info.get("top_sector", "无")}')
    if limit_info.get('hot_sectors'):
        lines.append(f'  热点板块分布:')
        for s in limit_info['hot_sectors'][:5]:
            lines.append(f'    {s["sector"]:<8} {s["limit_up_count"]}只涨停 '
                          f'({s.get("ratio", 0)}%)')
    lines.append(f'  简报: {hot_spot_result.get("summary", "N/A")}')
    lines.append('')

    # ----- 4. 短线情绪 -----
    lines.append('【四、短线情绪】')
    lines.append('-' * 50)
    lines.append(f'  综合情绪评分: {sentiment_result["total_score"]}/100')
    lines.append(f'  情绪判定: {sentiment_result["level"]}')
    for key, val in sentiment_result.get('components', {}).items():
        lines.append(f'    {key}: {val["score"]} ({val["detail"]})')
    lines.append('')

    # ----- 5. ETF轮动信号 -----
    lines.append('【五、ETF轮动信号】')
    lines.append('-' * 50)
    if etf_signal.get('defensive'):
        lines.append('  ⚠ 防御模式: 所有ETF动量转负，建议持有现金/货币基金')
    else:
        lines.append(f'  建议持仓:')
        for h in etf_signal.get('holdings', []):
            lines.append(f'    {h["name"]:<12} 动量: {h.get("momentum", 0):+.1f}%')
    lines.append('')

    # ----- ETF回测 -----
    if etf_backtest and 'error' not in etf_backtest:
        lines.append('【六、ETF轮动回测】')
        lines.append('-' * 50)
        lines.append(f'  回测期间: {etf_backtest["start_date"]} ~ {etf_backtest["end_date"]}')
        lines.append(f'  累计收益: {etf_backtest["total_return"]:+.1f}% '
                      f'(基准: {etf_backtest["benchmark_return"]:+.1f}%)')
        lines.append(f'  年化收益: {etf_backtest["annual_return"]:+.1f}%')
        lines.append(f'  最大回撤: {etf_backtest["max_drawdown"]:.1f}%')
        lines.append(f'  夏普比率: {etf_backtest["sharpe_ratio"]:.2f}')
        lines.append('')

    # ----- 7. 风险评估 -----
    lines.append('【七、综合风险评估】')
    lines.append('-' * 50)
    lines.append(f'  风险评分: {risk_result["risk_score"]}/100')
    lines.append(f'  风险等级: {risk_result["risk_level"]}')
    lines.append(f'  各维度:')
    for dim_name, dim_data in risk_result.get('dimensions', {}).items():
        lines.append(f'    {dim_name:<20} {dim_data["score"]}分 - {dim_data["detail"]}')
    lines.append(f'  建议:')
    for s in risk_result.get('suggestions', []):
        lines.append(f'    → {s}')
    lines.append('')

    lines.append(sep)
    lines.append('  ⚡ 本报告由A股量化分析系统自动生成，仅供参考，不构成投资建议')
    lines.append(sep)

    return '\n'.join(lines)


# ==================== 保存报告 ====================

def save_report(report_text: str) -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f'quant_report_{datetime.now().strftime("%Y%m%d_%H%M")}.txt'
    path = os.path.join(REPORT_DIR, filename)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(report_text)

    logger.info(f'报告已保存: {path}')
    return path


# ==================== 主流程 ====================

def run_quant_system(use_cache: bool = True, skip_data_fetch: bool = False):
    logger.info('=' * 60)
    logger.info('  A股量化分析系统 - 开始运行')
    logger.info(f'  运行时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}')
    logger.info('=' * 60)

    # 数据状态
    if not skip_data_fetch:
        logger.info('\n>>> [1/7] 数据获取...')
        indices = get_all_indices(count=120, use_cache=use_cache)
        stocks = get_all_stocks_quote(use_cache=use_cache)
        limits = get_limit_up_stocks(use_cache=use_cache)
        logger.info(f'    指数: {len(indices)}个, 个股: {len(stocks)}只, 涨停: {len(limits)}只')

    # 1. 指数分析
    logger.info('\n>>> [2/7] 指数分析...')
    index_result = analyze_all_indices(use_cache=use_cache)

    # 2. 板块轮动
    logger.info('\n>>> [3/7] 板块轮动分析...')
    sector_result = run_sector_rotation(use_cache=use_cache)

    # 3. 热点识别
    logger.info('\n>>> [4/7] 热点识别...')
    hot_spot_result = get_hot_spot_briefing(use_cache=use_cache)

    # 4. 短线情绪
    logger.info('\n>>> [5/7] 短线情绪分析...')
    sentiment_result = compute_sentiment_score(use_cache=use_cache)

    # 5. ETF轮动
    logger.info('\n>>> [6/7] ETF轮动分析...')
    etf_signal = get_weekly_rotation_signal(use_cache=use_cache)
    etf_backtest = run_etf_backtest(use_cache=use_cache)
    if 'error' not in etf_backtest:
        plot_etf_backtest(etf_backtest)

    # 6. 综合风险评估
    logger.info('\n>>> [7/7] 综合风险评估...')
    risk_result = assess_comprehensive_risk(use_cache=use_cache)
    plot_risk_radar(risk_result)

    # 生成报告
    logger.info('\n>>> 生成报告...')
    report_text = generate_report(
        index_result=index_result,
        sector_result=sector_result,
        hot_spot_result=hot_spot_result,
        sentiment_result=sentiment_result,
        etf_signal=etf_signal,
        etf_backtest=etf_backtest,
        risk_result=risk_result,
    )

    report_path = save_report(report_text)

    print('\n' + report_text)

    logger.info(f'\n✓ 量化分析运行完成! 报告已保存至: {report_path}')
    return {
        'report': report_text,
        'report_path': report_path,
        'index_result': index_result,
        'sector_result': sector_result,
        'hot_spot_result': hot_spot_result,
        'sentiment_result': sentiment_result,
        'etf_signal': etf_signal,
        'etf_backtest': etf_backtest,
        'risk_result': risk_result,
    }


# ==================== 定时任务配置 ====================

"""
===== 定时任务配置说明 =====

1. Windows 任务计划程序
   - 打开"任务计划程序"
   - 创建基本任务
   - 触发器: 每日 15:30 (收盘后)
   - 操作: 启动程序
   - 程序: python D:\\code\\snake\\quant_system\\main.py
   - 起始于: D:\\code\\snake\\quant_system

2. Linux Crontab
   30 15 * * 1-5 cd /path/to/quant_system && python main.py >> /var/log/quant.log 2>&1

3. 使用Python调度 (APScheduler)
   pip install apscheduler
   参考代码:
   from apscheduler.schedulers.blocking import BlockingScheduler
   scheduler = BlockingScheduler()
   @scheduler.scheduled_job('cron', day_of_week='mon-fri', hour=15, minute=30)
   def scheduled_job():
       run_quant_system(use_cache=True)
   scheduler.start()
"""


# ==================== 入口 ====================

if __name__ == '__main__':
    setup_logging()

    import argparse
    parser = argparse.ArgumentParser(description='A股量化分析系统')
    parser.add_argument('--no-cache', action='store_true',
                        help='不使用缓存，重新获取数据')
    parser.add_argument('--skip-fetch', action='store_true',
                        help='跳过数据获取（仅使用缓存）')
    args = parser.parse_args()

    run_quant_system(
        use_cache=not args.no_cache,
        skip_data_fetch=args.skip_fetch,
    )
