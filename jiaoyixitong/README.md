# A股量化交易系统

## 启动方式

### 方式一：运行批处理文件（推荐）
双击运行 `start.bat` 文件，服务器会自动启动。

### 方式二：命令行启动
打开命令提示符（CMD），执行以下命令：

```cmd
cd d:\code\jiaoyixitong
venv\Scripts\activate.bat
python webapp/app_simple.py
```

## 访问地址
启动后，在浏览器中访问：http://127.0.0.1:5000

## 功能模块

1. **大盘趋势分析** - 分析上证指数趋势
2. **板块轮动** - 分析各板块表现
3. **情绪热点** - 市场情绪分析
4. **资金流向** - 资金流动分析
5. **选股功能** - 多策略选股
6. **交易信号** - 开仓/清仓建议

## API接口

- `GET /api/health` - 健康检查
- `GET /api/quick` - 快速分析
- `POST /api/analyze` - 完整分析
- `GET /api/market-trend` - 大盘趋势
- `GET /api/sector-rotation` - 板块轮动
- `GET /api/capital-flow` - 资金流向
- `GET /api/sentiment` - 情绪分析
- `GET /api/screen-stocks` - 选股功能