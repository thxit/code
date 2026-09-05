import subprocess
import time
import urllib.request
import json
import sys
import os

def start_and_test():
    # Start server
    print("=" * 60)
    print("启动A股量化交易系统...")
    print("=" * 60)
    
    server_process = subprocess.Popen([
        sys.executable,
        'webapp/app_simple.py'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, 
       cwd='d:\\code\\jiaoyixitong', creationflags=subprocess.CREATE_NEW_CONSOLE)
    
    print(f"服务器进程已启动，PID: {server_process.pid}")
    print("等待服务器初始化...")
    time.sleep(8)
    
    # Check if server is running
    if server_process.poll() is not None:
        print("\n❌ 服务器启动失败！")
        output = server_process.communicate(timeout=30)[0]
        print("错误输出:")
        print(output)
        return False
    
    print("\n✅ 服务器启动成功！")
    print("正在测试API...")
    
    # Test health API
    print("\n--- 测试健康检查 API ---")
    try:
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/health', timeout=15)
        data = json.loads(response.read().decode('utf-8'))
        print(f"状态: {data.get('status', '未知')}")
        print(f"时间: {data.get('time', '未知')}")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")
    
    # Test quick analysis API
    print("\n--- 测试快速分析 API ---")
    try:
        print("正在获取市场数据... (可能需要10-30秒)")
        response = urllib.request.urlopen('http://127.0.0.1:5000/api/quick', timeout=120)
        data = json.loads(response.read().decode('utf-8'))
        
        if 'error' in data:
            print(f"❌ 分析失败: {data['error']}")
            if 'traceback' in data:
                print("\n错误详情:")
                print(data['traceback'][-2000:] if len(data['traceback']) > 2000 else data['traceback'])
        else:
            print("✅ 分析成功！")
            print(f"\n📊 分析结果摘要:")
            print(f"  - 分析时间: {data['meta'].get('analysis_time', 'N/A')}")
            print(f"  - 分析模式: {data['meta'].get('mode', 'N/A')}")
            
            if 'market_trend' in data:
                trend = data['market_trend']
                print(f"\n📈 大盘趋势:")
                print(f"  - 摘要: {trend.get('summary', 'N/A')}")
                print(f"  - 趋势方向: {trend.get('trend_direction', 'N/A')}")
                print(f"  - 强度: {trend.get('trend_strength', 'N/A')}")
            
            if 'trading_signal' in data:
                signal = data['trading_signal']
                print(f"\n🎯 交易信号:")
                print(f"  - 操作建议: {signal.get('action', 'N/A')}")
                print(f"  - 信号强度: {signal.get('strength', 'N/A')}")
                print(f"  - 信号评分: {signal.get('score', 'N/A')}")
            
            if 'sentiment' in data:
                sentiment = data['sentiment']
                print(f"\n💬 市场情绪:")
                print(f"  - 数据状态: {'可用' if sentiment else '不可用'}")
            
            if 'capital_flow' in data:
                flow = data['capital_flow']
                print(f"\n💰 资金流向:")
                print(f"  - 数据状态: {'可用' if flow else '不可用'}")
        
    except Exception as e:
        print(f"❌ 快速分析失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("服务器正在运行，请访问: http://127.0.0.1:5000")
    print("=" * 60)
    
    # Keep the script running to hold the server
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        server_process.terminate()
        server_process.wait()
        print("服务器已关闭")
    
    return True

if __name__ == "__main__":
    start_and_test()