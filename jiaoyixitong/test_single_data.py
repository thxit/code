import sys
sys.path.insert(0, 'd:/code/jiaoyixitong')

from data.fetcher import DataFetcher
from config.settings import get_config

config = get_config()
fetcher = DataFetcher(config)

print('测试获取上证指数数据...')
df = fetcher.fetch_index_daily('000001', period=50)
if df is not None and not df.empty:
    print('成功! 获取到 %d 条数据' % len(df))
    last_date = df['date'].iloc[-1]
    last_close = df['close'].iloc[-1]
    print('最新日期:', last_date)
    print('最新收盘价:', last_close)
else:
    print('失败! 未能获取数据')