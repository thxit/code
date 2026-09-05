#!/usr/bin/env python
import sys
import os

# Add project path
sys.path.insert(0, 'd:/code/jiaoyixitong')

print("=" * 60)
print("A股量化交易系统 - 调试模式")
print("=" * 60)
print()

try:
    from webapp.app_simple import app
    print("✅ 应用加载成功")
    
    # Run the app
    print("启动服务器...")
    print("访问地址: http://127.0.0.1:5000")
    print()
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
    
except Exception as e:
    print(f"❌ 启动失败: {e}")
    import traceback
    traceback.print_exc()
    input("\n按回车键退出...")