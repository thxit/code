import urllib.request
import json
import time

print("测试 /api/quick 分析接口...")
print("这可能需要10-30秒，请耐心等待...")
print()

start_time = time.time()
try:
    response = urllib.request.urlopen('http://127.0.0.1:5000/api/quick', timeout=120)
    elapsed = time.time() - start_time
    
    data = json.loads(response.read().decode('utf-8'))
    
    if 'error' in data:
        print("ERROR: 分析失败")
        print("错误信息:", data['error'])
        if 'traceback' in data:
            print("\n详细错误:")
            print(data['traceback'])
    else:
        print("SUCCESS: 分析成功!")
        print("耗时: %.2f 秒" % elapsed)
        print()
        print("=" * 50)
        print("分析结果摘要")
        print("=" * 50)
        
        # 元数据
        if 'meta' in data:
            print("\n分析信息:")
            print("  分析时间:", data['meta'].get('analysis_time', 'N/A'))
            print("  分析模式:", data['meta'].get('mode', 'N/A'))
        
        # 大盘趋势
        if 'market_trend' in data:
            trend = data['market_trend']
            print("\n大盘趋势分析:")
            print("  摘要:", trend.get('summary', 'N/A'))
            print("  趋势方向:", trend.get('trend_direction', 'N/A'))
            print("  趋势强度:", trend.get('trend_strength', 'N/A'))
        
        # 交易信号
        if 'trading_signal' in data:
            signal = data['trading_signal']
            print("\n交易信号:")
            print("  操作建议:", signal.get('action', 'N/A'))
            print("  信号强度:", signal.get('strength', 'N/A'))
            print("  信号评分:", signal.get('score', 'N/A'))
            if 'reasons' in signal and signal['reasons']:
                print("  理由:")
                for i, reason in enumerate(signal['reasons'][:3], 1):
                    print("    %d. %s" % (i, reason))
        
        # 市场情绪
        if 'sentiment' in data:
            sentiment = data['sentiment']
            print("\n市场情绪:")
            print("  数据状态: %s" % ('可用' if sentiment else '不可用'))
        
        # 资金流向
        if 'capital_flow' in data:
            flow = data['capital_flow']
            print("\n资金流向:")
            print("  数据状态: %s" % ('可用' if flow else '不可用'))
        
        print("\n" + "=" * 50)
        print("分析完成!")
        print("=" * 50)
        
except Exception as e:
    elapsed = time.time() - start_time
    print("FAIL: 请求失败")
    print("耗时: %.2f 秒" % elapsed)
    print("错误:", str(e))