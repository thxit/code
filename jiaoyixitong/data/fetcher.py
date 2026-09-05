import pandas as pd
import numpy as np
from typing import Optional, List, Dict
from loguru import logger
from config.settings import SystemConfig
from .cache import DataCache
import threading
import requests
import re
from datetime import datetime, timedelta

class DataFetcher:
    def __init__(self, config: SystemConfig):
        self.config = config
        self.cache = DataCache(cache_dir=config.cache_dir) if config.enable_cache else None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        # 禁用代理以解决连接问题
        self.session.trust_env = False

    def _fetch_with_timeout(self, func, timeout: int = 15):
        result = []
        exception = []

        def target():
            try:
                result.append(func())
            except Exception as e:
                exception.append(e)

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            logger.warning(f"Fetch timeout after {timeout}s")
            return None
        if exception:
            raise exception[0]
        return result[0] if result else None

    def _cached_fetch(self, func_name: str, fetch_func, *args, **kwargs):
        if self.cache:
            cached = self.cache.get(func_name, *args, **kwargs)
            if cached is not None:
                return cached
        try:
            timeout = 10 if "sector" in func_name else 30
            data = self._fetch_with_timeout(fetch_func, timeout=timeout)
            if data is not None and not data.empty and self.cache:
                self.cache.set(data, func_name, *args, **kwargs)
            return data
        except Exception as e:
            logger.error(f"Data fetch error [{func_name}]: {e}")
            return None

    def _fetch_from_sina(self, symbol: str, period: int = 250) -> Optional[pd.DataFrame]:
        """从新浪财经获取数据"""
        try:
            url = f"http://finance.sina.com.cn/stock/flashchart/kline_v2.php?symbol={symbol}&num={period}&scale=day&datalen={period}"
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            content = response.text
            match = re.search(r'var data=(.+?);', content)
            if not match:
                return None
            
            data_str = match.group(1)
            import json
            data = json.loads(data_str)
            
            if not data or not isinstance(data, list):
                return None
            
            df = pd.DataFrame(data, columns=['date', 'open', 'high', 'low', 'close', 'volume', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Sina fetch error: {e}")
            return None

    def _fetch_from_eastmoney(self, code: str, period: int = 250) -> Optional[pd.DataFrame]:
        """从东方财富获取数据"""
        try:
            # 构建URL
            market = '1' if code.startswith('6') else '0'
            url = f"https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={market}.{code}&ut=fa5fd1943c7b386f172d6893dbfba10b&fields1=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61&klt=101&fqt=1&end=20991231&lmt={period}"
            
            response = self.session.get(url, timeout=10)
            if response.status_code != 200:
                return None
            
            data = response.json()
            if data.get('code') != 0:
                return None
            
            klines = data.get('data', {}).get('klines', [])
            if not klines:
                return None
            
            rows = []
            for line in klines:
                parts = line.split(',')
                if len(parts) >= 6:
                    rows.append({
                        'date': parts[0],
                        'open': float(parts[1]),
                        'close': float(parts[2]),
                        'high': float(parts[3]),
                        'low': float(parts[4]),
                        'volume': int(float(parts[5]))
                    })
            
            df = pd.DataFrame(rows)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date').reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Eastmoney fetch error: {e}")
            return None

    def fetch_index_daily(self, index_code: str, period: int = 250) -> Optional[pd.DataFrame]:
        logger.info(f"Fetching index data: {index_code}")
        
        def _fetch():
            # 尝试多个数据源
            sources = [
                lambda: self._fetch_index_akshare(index_code, period),
                lambda: self._fetch_from_eastmoney(index_code, period),
                lambda: self._fetch_index_fallback(index_code, period),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        logger.info(f"Successfully fetched from source {i+1}")
                        return df
                except Exception as e:
                    logger.warning(f"Source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_index", _fetch, index_code, period)

    def _fetch_index_akshare(self, index_code: str, period: int) -> Optional[pd.DataFrame]:
        """使用akshare获取指数数据"""
        try:
            import akshare as ak
            
            if index_code == "000001":
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            elif index_code == "000016":
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            elif index_code == "000688":
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            elif index_code == "000905":
                df = ak.stock_zh_index_daily(symbol=f"sh{index_code}")
            else:
                df = ak.stock_zh_index_daily(symbol=f"sz{index_code}")
            
            df = df.rename(columns={
                "date": "date", "open": "open", "high": "high",
                "low": "low", "close": "close", "volume": "volume"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").tail(period).reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"AKShare index fetch error: {e}")
            return None

    def _fetch_index_fallback(self, index_code: str, period: int) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.index_zh_a_hist(symbol=index_code, period="daily", start_date="20200101", end_date="20991231")
            df = df.rename(columns={
                "日期": "date", "开盘": "open", "最高": "high",
                "最低": "low", "收盘": "close", "成交量": "volume"
            })
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").tail(period).reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Fallback fetch failed for {index_code}: {e}")
            return None

    def fetch_sector_daily(self, sector_code: str, period: int = 60) -> Optional[pd.DataFrame]:
        logger.info(f"Fetching sector data: {sector_code}")
        
        def _fetch():
            sources = [
                lambda: self._fetch_sector_akshare(sector_code, period),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        return df
                except Exception as e:
                    logger.warning(f"Sector source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_sector", _fetch, sector_code, period)

    def _fetch_sector_akshare(self, sector_code: str, period: int) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            df = ak.index_zh_a_hist(symbol=sector_code, period="daily", start_date="20250101", end_date="20991231")
            if df is None or df.empty:
                return None
            col_map = {}
            for col in df.columns:
                if "日期" in col or col == "日期":
                    col_map[col] = "date"
                elif "开" in col:
                    col_map[col] = "open"
                elif "高" in col:
                    col_map[col] = "high"
                elif "低" in col:
                    col_map[col] = "low"
                elif "收" in col:
                    col_map[col] = "close"
                elif "量" in col:
                    col_map[col] = "volume"
                elif "额" in col:
                    col_map[col] = "amount"
            df = df.rename(columns=col_map)
            required_cols = ["date", "open", "high", "low", "close", "volume"]
            df = df[[c for c in required_cols if c in df.columns]]
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").tail(period).reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Sector AKShare fetch error {sector_code}: {e}")
            return None

    def fetch_stock_daily(self, stock_code: str, period: int = 120) -> Optional[pd.DataFrame]:
        logger.info(f"Fetching stock data: {stock_code}")
        
        def _fetch():
            sources = [
                lambda: self._fetch_stock_akshare(stock_code, period),
                lambda: self._fetch_from_eastmoney(stock_code, period),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        logger.info(f"Stock {stock_code} fetched from source {i+1}")
                        return df
                except Exception as e:
                    logger.warning(f"Stock source {i+1} failed for {stock_code}: {e}")
            
            return None
        
        return self._cached_fetch("fetch_stock", _fetch, stock_code, period)

    def _fetch_stock_akshare(self, stock_code: str, period: int) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            df = ak.stock_zh_a_hist(
                symbol=stock_code, period="daily",
                start_date="20230101", end_date="20991231", adjust="qfq"
            )
            col_map = {
                "日期": "date", "开盘": "open", "最高": "high",
                "最低": "low", "收盘": "close", "成交量": "volume",
                "成交额": "amount", "涨跌幅": "change_pct",
                "涨跌额": "change", "换手率": "turnover"
            }
            df = df.rename(columns=col_map)
            required = ["date", "open", "high", "low", "close", "volume"]
            available = [c for c in required if c in df.columns]
            df = df[available]
            df["date"] = pd.to_datetime(df["date"])
            df = df.sort_values("date").tail(period).reset_index(drop=True)
            return df
        except Exception as e:
            logger.error(f"Stock AKShare fetch error {stock_code}: {e}")
            return None

    def fetch_north_flow(self, period: int = 60) -> Optional[pd.DataFrame]:
        logger.info("Fetching north-bound capital flow")
        
        def _fetch():
            sources = [
                lambda: self._fetch_north_akshare(period),
                lambda: self._fetch_north_eastmoney(period),
                lambda: self._fetch_north_mock(period),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        if i == len(sources) - 1:
                            logger.info(f"Using mock data for north flow")
                        return df
                except Exception as e:
                    logger.warning(f"North flow source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_north_flow", _fetch, period)
    
    def _fetch_north_mock(self, period: int) -> pd.DataFrame:
        """生成模拟北向资金数据"""
        from .mock_data import generate_mock_north_flow
        return generate_mock_north_flow(period)

    def _fetch_north_akshare(self, period: int) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            # 尝试多个AKShare接口
            apis = [
                lambda: ak.stock_hsgt_hist_em(symbol="北上", period="daily",
                                              start_date="20230101", end_date="20991231"),
                lambda: ak.stock_hsgt_north_net_flow(),
                lambda: ak.stock_hsgt_north_flow(),
            ]
            
            for i, api_func in enumerate(apis):
                try:
                    df = api_func()
                    if df is not None and not df.empty:
                        col_map = {}
                        for col in df.columns:
                            if "日期" in col or col == "日期":
                                col_map[col] = "date"
                            elif "净流入" in col or "资金" in col or "北向" in col:
                                col_map[col] = "net_flow"
                            elif "成交额" in col or "成交" in col:
                                col_map[col] = "amount"
                        df = df.rename(columns=col_map)
                        if "date" in df.columns:
                            df["date"] = pd.to_datetime(df["date"])
                            df = df.sort_values("date").tail(period).reset_index(drop=True)
                            logger.info(f"North flow from AKShare API {i+1}")
                            return df
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"North AKShare error: {e}")
        return None

    def _fetch_north_eastmoney(self, period: int) -> Optional[pd.DataFrame]:
        """从东方财富获取北向资金数据"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=1000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') != 0:
                return None
            
            items = data.get('data', {}).get('diff', [])
            if not items:
                return None
            
            df = pd.DataFrame(items)
            if 'f12' not in df.columns or 'f2' not in df.columns:
                return None
            
            df = df[['f12', 'f2', 'f3']]
            df.columns = ['code', 'name', 'net_flow']
            return df
        except Exception as e:
            logger.error(f"North eastmoney error: {e}")
            return None

    def fetch_market_sentiment(self) -> Optional[pd.DataFrame]:
        logger.info("Fetching market sentiment data")
        
        def _fetch():
            sources = [
                lambda: self._fetch_sentiment_akshare(),
                lambda: self._fetch_sentiment_mock(),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        if i == len(sources) - 1:
                            logger.info(f"Using mock data for sentiment")
                        return df
                except Exception as e:
                    logger.warning(f"Sentiment source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_sentiment", _fetch)
    
    def _fetch_sentiment_mock(self) -> pd.DataFrame:
        """生成模拟市场情绪数据"""
        from .mock_data import generate_mock_sentiment
        return generate_mock_sentiment()

    def _fetch_sentiment_akshare(self) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            apis = [
                lambda: ak.stock_zt_pool_em(date=None),
                lambda: ak.stock_zt_pool_strong_em(date=None),
                lambda: ak.stock_a_stock_spot(),
                lambda: ak.stock_zh_a_spot_em(),
            ]
            
            for i, api_func in enumerate(apis):
                try:
                    df = api_func()
                    if df is not None and not df.empty:
                        logger.info(f"Sentiment from AKShare API {i+1}")
                        return df
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Sentiment AKShare error: {e}")
        return None

    def fetch_industry_flow(self) -> Optional[pd.DataFrame]:
        logger.info("Fetching industry capital flow")
        
        def _fetch():
            sources = [
                lambda: self._fetch_industry_akshare(),
                lambda: self._fetch_industry_eastmoney(),
                lambda: self._fetch_industry_mock(),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        if i == len(sources) - 1:
                            logger.info(f"Using mock data for industry flow")
                        return df
                except Exception as e:
                    logger.warning(f"Industry flow source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_industry_flow", _fetch)
    
    def _fetch_industry_mock(self) -> pd.DataFrame:
        """生成模拟行业资金流数据"""
        from .mock_data import generate_mock_industry_flow
        return generate_mock_industry_flow()

    def _fetch_industry_akshare(self) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            apis = [
                lambda: ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="行业资金流"),
                lambda: ak.stock_sector_fund_flow_rank(indicator="今日"),
                lambda: ak.stock_sector_fund_flow(),
                lambda: ak.stock_industry_index(),
                lambda: ak.stock_sector_index(),
            ]
            
            for i, api_func in enumerate(apis):
                try:
                    df = api_func()
                    if df is not None and not df.empty:
                        logger.info(f"Industry flow from AKShare API {i+1}")
                        return df
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Industry AKShare error: {e}")
        return None

    def _fetch_industry_eastmoney(self) -> Optional[pd.DataFrame]:
        """从东方财富获取行业资金流"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=b:BK0054,b:BK0058,b:BK0060,b:BK0062,b:BK0063,b:BK0064,b:BK0065,b:BK0066,b:BK0067,b:BK0068,b:BK0070,b:BK0071,b:BK0072,b:BK0073,b:BK0074,b:BK0075,b:BK0076,b:BK0077,b:BK0078,b:BK0079,b:BK0080,b:BK0081,b:BK0082,b:BK0083,b:BK0084,b:BK0085,b:BK0086,b:BK0087,b:BK0088,b:BK0089,b:BK0090,b:BK0091,b:BK0092,b:BK0093,b:BK0094,b:BK0095,b:BK0096,b:BK0097,b:BK0098,b:BK0099,b:BK0100,b:BK0101,b:BK0102,b:BK0103,b:BK0104,b:BK0105,b:BK0106,b:BK0107,b:BK0108,b:BK0109,b:BK0110,b:BK0111,b:BK0112,b:BK0113,b:BK0114,b:BK0115,b:BK0116,b:BK0117,b:BK0118,b:BK0119,b:BK0120,b:BK0121,b:BK0122,b:BK0123,b:BK0124,b:BK0125,b:BK0126,b:BK0127,b:BK0128,b:BK0129,b:BK0130,b:BK0131,b:BK0132,b:BK0133,b:BK0134,b:BK0135,b:BK0136,b:BK0137,b:BK0138,b:BK0139,b:BK0140,b:BK0141,b:BK0142,b:BK0143,b:BK0144,b:BK0145,b:BK0146,b:BK0147,b:BK0148,b:BK0149,b:BK0150&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') != 0:
                return None
            
            items = data.get('data', {}).get('diff', [])
            if not items:
                return None
            
            df = pd.DataFrame(items)
            return df
        except Exception as e:
            logger.error(f"Industry eastmoney error: {e}")
            return None

    def fetch_stock_list(self) -> Optional[pd.DataFrame]:
        logger.info("Fetching stock list")
        
        def _fetch():
            sources = [
                lambda: self._fetch_stock_list_akshare(),
                lambda: self._fetch_stock_list_eastmoney(),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        return df
                except Exception as e:
                    logger.warning(f"Stock list source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_stock_list", _fetch)

    def _fetch_stock_list_akshare(self) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            logger.error(f"Stock list AKShare error: {e}")
        return None

    def _fetch_stock_list_eastmoney(self) -> Optional[pd.DataFrame]:
        """从东方财富获取股票列表"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5000&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') != 0:
                return None
            
            items = data.get('data', {}).get('diff', [])
            if not items:
                return None
            
            df = pd.DataFrame(items)
            if 'f12' in df.columns and 'f14' in df.columns:
                df = df.rename(columns={'f12': '代码', 'f14': '名称', 'f2': '最新价', 'f3': '涨跌幅', 'f4': '涨跌额', 'f5': '成交量'})
            return df
        except Exception as e:
            logger.error(f"Stock list eastmoney error: {e}")
            return None

    def fetch_concept_flow(self) -> Optional[pd.DataFrame]:
        logger.info("Fetching concept capital flow")
        
        def _fetch():
            sources = [
                lambda: self._fetch_concept_akshare(),
                lambda: self._fetch_concept_eastmoney(),
                lambda: self._fetch_concept_mock(),
            ]
            
            for i, source in enumerate(sources):
                try:
                    df = source()
                    if df is not None and not df.empty:
                        if i == len(sources) - 1:
                            logger.info(f"Using mock data for concept flow")
                        return df
                except Exception as e:
                    logger.warning(f"Concept flow source {i+1} failed: {e}")
            
            return None
        
        return self._cached_fetch("fetch_concept_flow", _fetch)
    
    def _fetch_concept_mock(self) -> pd.DataFrame:
        """生成模拟概念板块资金流数据"""
        from .mock_data import generate_mock_concept_flow
        return generate_mock_concept_flow()

    def _fetch_concept_akshare(self) -> Optional[pd.DataFrame]:
        import akshare as ak
        try:
            df = ak.stock_sector_fund_flow_rank(indicator="今日", sector_type="概念资金流")
            return df if df is not None and not df.empty else None
        except Exception as e:
            logger.error(f"Concept AKShare error: {e}")
            return None

    def _fetch_concept_eastmoney(self) -> Optional[pd.DataFrame]:
        """从东方财富获取概念资金流"""
        try:
            url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f62&fs=b:BK1001,b:BK1002,b:BK1003,b:BK1004,b:BK1005,b:BK1006,b:BK1007,b:BK1008,b:BK1009,b:BK1010&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f22,f11,f60,f61,f62,f63,f64,f65,f66,f67,f68,f69,f70,f71,f72,f73,f74,f75,f76,f77,f78,f79,f80,f81,f82,f83,f84,f85,f86,f87,f88,f89,f90"
            response = self.session.get(url, timeout=10)
            data = response.json()
            
            if data.get('code') != 0:
                return None
            
            items = data.get('data', {}).get('diff', [])
            if not items:
                return None
            
            df = pd.DataFrame(items)
            return df
        except Exception as e:
            logger.error(f"Concept eastmoney error: {e}")
            return None