import sys
sys.path.insert(0, 'd:/code/jiaoyixitong')

from data.fetcher import DataFetcher
from config.settings import get_config
import pandas as pd

config = get_config()
config.enable_cache = False  # 禁用缓存以便获取最新数据
fetcher = DataFetcher(config)

print("=" * 60)
print("数据获取调试 - 检查数据源和解析逻辑")
print("=" * 60)

# 1. 测试上证指数数据
print("\n--- 1. 测试上证指数数据 (000001) ---")
df = fetcher.fetch_index_daily('000001', period=10)
if df is not None and not df.empty:
    print(f"获取到 {len(df)} 条数据")
    print("数据头部:")
    print(df.head())
    print("\n数据尾部:")
    print(df.tail())
    print("\n数据信息:")
    print(df.info())
    print("\n日期范围:")
    print(f"最早日期: {df['date'].min()}")
    print(f"最晚日期: {df['date'].max()}")
    print(f"最新收盘价: {df['close'].iloc[-1]}")
else:
    print("获取失败")

# 2. 测试北向资金
print("\n--- 2. 测试北向资金数据 ---")
df = fetcher.fetch_north_flow(period=10)
if df is not None and not df.empty:
    print(f"获取到 {len(df)} 条数据")
    print("数据头部:")
    print(df.head())
    print("\n列名:", list(df.columns))
else:
    print("获取失败")

# 3. 测试行业资金流
print("\n--- 3. 测试行业资金流数据 ---")
df = fetcher.fetch_industry_flow()
if df is not None and not df.empty:
    print(f"获取到 {len(df)} 条数据")
    print("数据头部:")
    print(df.head())
    print("\n列名:", list(df.columns)[:20])
else:
    print("获取失败")

# 4. 测试市场情绪（涨停数据）
print("\n--- 4. 测试市场情绪数据 ---")
df = fetcher.fetch_market_sentiment()
if df is not None and not df.empty:
    print(f"获取到 {len(df)} 条数据")
    print("数据头部:")
    print(df.head())
    print("\n列名:", list(df.columns))
else:
    print("获取失败")

# 5. 测试东方财富直接数据源
print("\n--- 5. 直接测试东方财富数据源 ---")
df = fetcher._fetch_from_eastmoney('000001', period=10)
if df is not None and not df.empty:
    print(f"获取到 {len(df)} 条数据")
    print("数据:")
    print(df)
    print("\n日期范围:")
    print(f"最早日期: {df['date'].min()}")
    print(f"最晚日期: {df['date'].max()}")
else:
    print("获取失败")

print("\n" + "=" * 60)
print("调试完成")
print("=" * 60)