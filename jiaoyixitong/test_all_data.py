import sys
sys.path.insert(0, 'd:/code/jiaoyixitong')

from data.fetcher import DataFetcher
from config.settings import get_config
import pandas as pd

config = get_config()
config.enable_cache = False
fetcher = DataFetcher(config)

print("=" * 60)
print("数据获取测试 - 完整结果")
print("=" * 60)

# 1. 上证指数
print("\n--- 1. 上证指数数据 (000001) ---")
df = fetcher.fetch_index_daily('000001', period=5)
if df is not None and not df.empty:
    print("SUCCESS - 获取成功")
    print(df[['date', 'close', 'volume']].to_string())
else:
    print("FAIL - 获取失败")

# 2. 北向资金
print("\n--- 2. 北向资金数据 ---")
df = fetcher.fetch_north_flow(period=5)
if df is not None and not df.empty:
    print("SUCCESS - 获取成功")
    print(df[['date', 'net_flow']].to_string())
else:
    print("FAIL - 获取失败")

# 3. 行业资金流
print("\n--- 3. 行业资金流数据 ---")
df = fetcher.fetch_industry_flow()
if df is not None and not df.empty:
    print("SUCCESS - 获取成功")
    print(df[['行业名称', '涨跌幅', '净流入']].head(5).to_string())
else:
    print("FAIL - 获取失败")

# 4. 市场情绪
print("\n--- 4. 市场情绪数据 ---")
df = fetcher.fetch_market_sentiment()
if df is not None and not df.empty:
    print("SUCCESS - 获取成功")
    print(df[['代码', '名称', '涨跌幅']].head(5).to_string())
else:
    print("FAIL - 获取失败")

# 5. 概念板块
print("\n--- 5. 概念板块数据 ---")
df = fetcher.fetch_concept_flow()
if df is not None and not df.empty:
    print("SUCCESS - 获取成功")
    print(df[['概念名称', '涨跌幅', '净流入']].head(5).to_string())
else:
    print("FAIL - 获取失败")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)