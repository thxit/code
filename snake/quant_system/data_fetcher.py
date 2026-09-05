"""
需求1: 数据获取模块
使用efinance免费接口获取A股数据，DataFrame返回，支持CSV缓存
"""

import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

from config import (
    INDEX_CONFIG, SW_SECTORS, ETF_POOL,
    CACHE_DIR, REPORT_DIR
)

logger = logging.getLogger(__name__)

# ==================== 缓存管理 ====================

def _ensure_dirs():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(REPORT_DIR, exist_ok=True)

def _cache_path(name: str) -> str:
    return os.path.join(CACHE_DIR, f'{name}.csv')

def _read_cache(name: str, max_age_days: float = 1.0) -> Optional[pd.DataFrame]:
    path = _cache_path(name)
    if not os.path.exists(path):
        return None
    mtime = datetime.fromtimestamp(os.path.getmtime(path))
    age = (datetime.now() - mtime).total_seconds() / 86400
    if age > max_age_days:
        logger.info(f'缓存 [{name}] 已过期 ({age:.1f}天)')
        return None
    try:
        df = pd.read_csv(path, index_col=0, parse_dates=True)
        logger.info(f'读取缓存 [{name}] ({len(df)}行)')
        return df
    except Exception as e:
        logger.warning(f'缓存读取失败 [{name}]: {e}')
        return None

def _write_cache(name: str, df: pd.DataFrame):
    _ensure_dirs()
    path = _cache_path(name)
    df.to_csv(path)
    logger.info(f'缓存已保存 [{name}] ({len(df)}行)')

# ==================== efinance接口封装 ====================

def _import_efinance():
    try:
        import efinance as ef
        return ef
    except ImportError:
        logger.warning('efinance 未安装，尝试安装...')
        import subprocess
        subprocess.check_call(['pip', 'install', 'efinance', '-i',
                               'https://pypi.tuna.tsinghua.edu.cn/simple'])
        import efinance as ef
        return ef

def _is_today_data(df: pd.DataFrame) -> bool:
    if df.empty:
        return False
    last_date = df.index[-1] if isinstance(df.index, pd.DatetimeIndex) else df.iloc[-1].name
    if isinstance(last_date, str):
        last_date = pd.to_datetime(last_date)
    today = pd.Timestamp.now().normalize()
    return last_date.date() == today.date()

# ==================== 指数数据获取 ====================

def get_index_daily(name: str, code: str, count: int = 120,
                    use_cache: bool = True) -> pd.DataFrame:
    cache_name = f'index_{name}'
    if use_cache:
        cached = _read_cache(cache_name)
        if cached is not None and len(cached) >= count:
            return cached.iloc[-count:]

    ef = _import_efinance()
    try:
        df = ef.stock.get_quote_history(f'{code}{INDEX_SUFFIX}',
                                         klt=101, fqt=1)
        if df is None or df.empty:
            raise ValueError(f'获取指数 [{name}] 数据为空')

        if '日期' in df.columns:
            df.rename(columns={'日期': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        col_map = {
            '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
            '成交量': 'volume', '成交额': 'amount', '涨跌额': 'change',
            '涨跌幅': 'pct_change', '换手率': 'turnover',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df.rename(columns={cn: en}, inplace=True)

        df = df[[c for c in ['open', 'close', 'high', 'low', 'volume', 'amount']
                 if c in df.columns]]

        if use_cache:
            _write_cache(cache_name, df)

        logger.info(f'获取指数 [{name}] ({code}) 成功: {len(df)}行')
        return df[-count:]

    except Exception as e:
        logger.error(f'获取指数 [{name}] ({code}) 失败: {e}')
        return pd.DataFrame()

def get_all_indices(count: int = 120, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    result = {}
    for name, code in INDEX_CONFIG.items():
        df = get_index_daily(name, code, count, use_cache)
        if not df.empty:
            result[name] = df
        time.sleep(0.3)
    return result

# ==================== 个股行情数据 ====================

def get_all_stocks_quote(use_cache: bool = True) -> pd.DataFrame:
    cache_name = 'all_stocks_quote'
    if use_cache:
        cached = _read_cache(cache_name, max_age_days=0.125)
        if cached is not None and _is_today_data(cached):
            return cached

    ef = _import_efinance()
    try:
        df = ef.stock.get_realtime_quotes()
        if df is None or df.empty:
            return pd.DataFrame()

        col_map = {
            '股票名称': 'name', '股票代码': 'code', '最新价': 'price',
            '涨跌幅': 'pct_change', '涨跌额': 'change', '成交量': 'volume',
            '成交额': 'amount', '换手率': 'turnover', '市盈率-动态': 'pe',
            '总市值': 'total_mv', '流通市值': 'float_mv',
            '60日涨跌幅': 'pct_60d',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df.rename(columns={cn: en}, inplace=True)

        keep_cols = [c for c in ['name', 'code', 'price', 'pct_change',
                                  'volume', 'amount', 'turnover', 'pe',
                                  'total_mv', 'float_mv']
                     if c in df.columns]
        df = df[keep_cols].copy()

        for col in ['price', 'pct_change', 'volume', 'amount',
                    'turnover', 'pe', 'total_mv', 'float_mv']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df['fetch_time'] = datetime.now()

        _write_cache(cache_name, df)
        logger.info(f'全市场行情获取成功: {len(df)}只个股')
        return df

    except Exception as e:
        logger.error(f'全市场行情获取失败: {e}')
        return pd.DataFrame()

# ==================== 涨停板数据 ====================

def get_limit_up_stocks(use_cache: bool = True) -> pd.DataFrame:
    cache_name = 'limit_up_stocks'
    if use_cache:
        cached = _read_cache(cache_name, max_age_days=0.125)
        if cached is not None and _is_today_data(cached):
            return cached

    try:
        import akshare as ak
        df = ak.stock_zt_pool_em(date=pd.Timestamp.now().strftime('%Y%m%d'))
        if df is None or df.empty:
            return pd.DataFrame()

        col_map = {
            '代码': 'code', '名称': 'name', '最新价': 'price',
            '涨跌幅': 'pct_change', '涨停价': 'limit_up_price',
            '封单额': 'seal_amount', '流通市值': 'float_mv',
            '换手率': 'turnover', '涨停次数': 'limit_up_count',
            '封板时间': 'seal_time', '所属行业': 'sector',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df.rename(columns={cn: en}, inplace=True)

        df['fetch_time'] = datetime.now()
        _write_cache(cache_name, df)
        logger.info(f'涨停板数据获取成功: {len(df)}只涨停')
        return df

    except ImportError:
        logger.warning('akshare 未安装，使用备用方案获取涨停数据')
    except Exception as e:
        logger.error(f'涨停板数据获取失败: {e}')

    return get_limit_up_fallback(use_cache)

def get_limit_up_fallback(use_cache: bool = True) -> pd.DataFrame:
    cache_name = 'limit_up_stocks_fb'
    if use_cache:
        cached = _read_cache(cache_name, max_age_days=0.125)
        if cached is not None:
            return cached

    ef = _import_efinance()
    try:
        df = ef.stock.get_realtime_quotes()
        codes = df['股票代码'].tolist() if '股票代码' in df.columns else df['code'].tolist()
        names = df['股票名称'].tolist() if '股票名称' in df.columns else df['name'].tolist()
        pct = df['涨跌幅'].tolist() if '涨跌幅' in df.columns else df.get('pct_change', [])

        limit_up_list = []
        for i, code in enumerate(codes):
            try:
                pct_val = float(pct[i]) if i < len(pct) else 0
                if pct_val >= 9.8:
                    limit_up_list.append({
                        'code': code,
                        'name': names[i] if i < len(names) else '',
                        'pct_change': pct_val
                    })
            except (ValueError, IndexError):
                continue

        result = pd.DataFrame(limit_up_list)
        if not result.empty:
            _write_cache(cache_name, result)
        logger.info(f'涨停板(备用)获取成功: {len(result)}只')
        return result

    except Exception as e:
        logger.error(f'涨停板(备用)获取失败: {e}')
        return pd.DataFrame()

# ==================== 板块/行业数据 ====================

def get_sector_daily(name: str, count: int = 120,
                     use_cache: bool = True) -> pd.DataFrame:
    cache_name = f'sector_{name}'
    if use_cache:
        cached = _read_cache(cache_name)
        if cached is not None and len(cached) >= count:
            return cached.iloc[-count:]

    ef = _import_efinance()
    try:
        df = ef.stock.get_quote_history(
            f'{name}',
            klt=101, fqt=1
        )

        if df is not None and not df.empty:
            if '日期' in df.columns:
                df.rename(columns={'日期': 'date'}, inplace=True)
            df['date'] = pd.to_datetime(df['date'])
            df.set_index('date', inplace=True)
            df.sort_index(inplace=True)

            col_map = {
                '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                '成交量': 'volume', '成交额': 'amount',
            }
            for cn, en in col_map.items():
                if cn in df.columns:
                    df.rename(columns={cn: en}, inplace=True)

            df = df[[c for c in ['open', 'close', 'high', 'low', 'volume', 'amount']
                     if c in df.columns]]

            if use_cache:
                _write_cache(cache_name, df)
            logger.info(f'获取行业板块 [{name}] 成功: {len(df)}行')
            return df[-count:]

    except Exception as e:
        logger.warning(f'行业板块 [{name}] 直连失败，尝试akshare: {e}')

    try:
        import akshare as ak
        df_sw = ak.stock_board_industry_hist_em(
            symbol=name,
            start_date=(datetime.now() - timedelta(days=count * 1.5)).strftime('%Y%m%d'),
            end_date=datetime.now().strftime('%Y%m%d')
        )
        if df_sw is not None and not df_sw.empty:
            if '日期' in df_sw.columns:
                df_sw.rename(columns={'日期': 'date'}, inplace=True)
            df_sw['date'] = pd.to_datetime(df_sw['date'])
            df_sw.set_index('date', inplace=True)
            df_sw.sort_index(inplace=True)

            col_map = {
                '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
                '成交量': 'volume', '成交额': 'amount',
            }
            for cn, en in col_map.items():
                if cn in df_sw.columns:
                    df_sw.rename(columns={cn: en}, inplace=True)

            df_sw = df_sw[[c for c in ['open', 'close', 'high', 'low', 'volume', 'amount']
                          if c in df_sw.columns]]

            if use_cache:
                _write_cache(cache_name, df_sw)
            logger.info(f'获取行业板块 [{name}] (akshare) 成功: {len(df_sw)}行')
            return df_sw[-count:]

    except Exception as e:
        logger.error(f'获取行业板块 [{name}] (akshare) 失败: {e}')

    return pd.DataFrame()

def get_all_sectors(count: int = 120, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    result = {}
    for sector in SW_SECTORS:
        df = get_sector_daily(sector, count, use_cache)
        if not df.empty:
            result[sector] = df
        time.sleep(0.2)
    return result

# ==================== ETF数据 ====================

def get_etf_daily(code: str, name: str, count: int = 250,
                  use_cache: bool = True) -> pd.DataFrame:
    cache_name = f'etf_{code}'
    if use_cache:
        cached = _read_cache(cache_name)
        if cached is not None and len(cached) >= count:
            return cached.iloc[-count:]

    ef = _import_efinance()
    try:
        df = ef.stock.get_quote_history(f'{code}',
                                         klt=101, fqt=1)
        if df is None or df.empty:
            raise ValueError(f'获取ETF [{name}] ({code}) 数据为空')

        if '日期' in df.columns:
            df.rename(columns={'日期': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        col_map = {
            '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
            '成交量': 'volume', '成交额': 'amount',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df.rename(columns={cn: en}, inplace=True)

        df = df[[c for c in ['open', 'close', 'high', 'low', 'volume', 'amount']
                 if c in df.columns]]

        if use_cache:
            _write_cache(cache_name, df)

        logger.info(f'获取ETF [{name}] ({code}) 成功: {len(df)}行')
        return df[-count:]

    except Exception as e:
        logger.error(f'获取ETF [{name}] ({code}) 失败: {e}')
        return pd.DataFrame()

def get_all_etfs(count: int = 250, use_cache: bool = True) -> Dict[str, pd.DataFrame]:
    result = {}
    for code, name in ETF_POOL.items():
        df = get_etf_daily(code, name, count, use_cache)
        if not df.empty:
            result[name] = df
        time.sleep(0.3)
    return result

# ==================== 指数PE数据 ====================

def get_index_pe(name: str, code: str) -> Optional[Dict]:
    """获取指数PE历史分位数"""
    try:
        import akshare as ak
        df_pe = ak.stock_index_pe_lg(symbol=code.replace('.', ''))
        if df_pe is None or df_pe.empty:
            return None

        if '日期' in df_pe.columns:
            df_pe.rename(columns={'日期': 'date'}, inplace=True)
        df_pe['date'] = pd.to_datetime(df_pe['date'])
        df_pe.set_index('date', inplace=True)
        df_pe.sort_index(inplace=True)

        if '平均PE' in df_pe.columns:
            pe_col = '平均PE'
        elif 'pe' in df_pe.columns:
            pe_col = 'pe'
        else:
            pe_col = df_pe.select_dtypes(include=[np.number]).columns[0]

        pe_series = df_pe[pe_col].dropna()
        if pe_series.empty:
            return None

        current_pe = pe_series.iloc[-1]
        percentile = (pe_series < current_pe).sum() / len(pe_series) * 100

        return {
            'current_pe': round(current_pe, 2),
            'pe_percentile': round(percentile, 1),
            'pe_min': round(pe_series.min(), 2),
            'pe_max': round(pe_series.max(), 2),
            'pe_mean': round(pe_series.mean(), 2),
            'pe_median': round(pe_series.median(), 2),
        }

    except Exception as e:
        logger.error(f'获取指数PE [{name}] 失败: {e}')
        return None

# ==================== 股票K线数据 ====================

def get_stock_kline(code: str, count: int = 120) -> pd.DataFrame:
    ef = _import_efinance()
    try:
        df = ef.stock.get_quote_history(f'{code}',
                                         klt=101, fqt=1)
        if df is None or df.empty:
            return pd.DataFrame()

        if '日期' in df.columns:
            df.rename(columns={'日期': 'date'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)

        col_map = {
            '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low',
            '成交量': 'volume', '成交额': 'amount', '涨跌幅': 'pct_change',
        }
        for cn, en in col_map.items():
            if cn in df.columns:
                df.rename(columns={cn: en}, inplace=True)

        df = df[[c for c in ['open', 'close', 'high', 'low', 'volume', 'amount', 'pct_change']
                 if c in df.columns]]
        return df[-count:]

    except Exception as e:
        logger.error(f'获取股票K线 [{code}] 失败: {e}')
        return pd.DataFrame()

# ==================== 涨停板行业分布 ====================

def get_limit_up_sector_distribution() -> pd.DataFrame:
    """统计涨停股票的行业分布"""
    limit_df = get_limit_up_stocks()
    if limit_df.empty:
        return pd.DataFrame()

    if 'sector' in limit_df.columns:
        dist = limit_df['sector'].value_counts().reset_index()
        dist.columns = ['sector', 'limit_up_count']
        dist['ratio'] = (dist['limit_up_count'] / dist['limit_up_count'].sum() * 100).round(1)
        return dist

    stocks_df = get_all_stocks_quote()
    if stocks_df.empty:
        return pd.DataFrame()

    limit_codes = set(limit_df['code'].tolist())
    if 'code' not in stocks_df.columns:
        return pd.DataFrame()

    limit_with_sector = []
    for _, row in stocks_df.iterrows():
        if row['code'] in limit_codes:
            limit_with_sector.append({
                'code': row['code'],
                'name': row.get('name', ''),
                'sector': row.get('sector', '未知'),
            })

    if limit_with_sector:
        result = pd.DataFrame(limit_with_sector)
        dist = result['sector'].value_counts().reset_index()
        dist.columns = ['sector', 'limit_up_count']
        dist['ratio'] = (dist['limit_up_count'] / dist['limit_up_count'].sum() * 100).round(1)
        return dist

    return pd.DataFrame()

# ==================== 数据更新检查 ====================

def is_market_open() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    morning_start = now.replace(hour=9, minute=30, second=0)
    morning_end = now.replace(hour=11, minute=30, second=0)
    afternoon_start = now.replace(hour=13, minute=0, second=0)
    afternoon_end = now.replace(hour=15, minute=0, second=0)
    return (morning_start <= now <= morning_end) or (afternoon_start <= now <= afternoon_end)

def is_market_closed_today() -> bool:
    now = datetime.now()
    market_end = now.replace(hour=15, minute=0, second=0)
    return now > market_end


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')
    print('=== 数据获取模块测试 ===')

    indices = get_all_indices(count=60)
    print(f'\n指数数据: {list(indices.keys())}')

    stocks = get_all_stocks_quote()
    print(f'\n个股行情: {len(stocks)}只')

    limits = get_limit_up_stocks()
    print(f'\n涨停板: {len(limits)}只')

    sectors = get_all_sectors(count=60)
    print(f'\n行业板块: {list(sectors.keys())}')
