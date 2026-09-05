import backtrader as bt
import matplotlib.pyplot as plt

# 创建双均线策略
class DualMovingAverageStrategy(bt.Strategy):
    params = (
        ('fast', 10),  # 快速均线周期
        ('slow', 30),  # 慢速均线周期
    )

    def __init__(self):
        # 定义均线指标
        self.fast_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.fast)
        self.slow_ma = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.slow)
        
        # 交叉信号指标
        self.crossover = bt.indicators.CrossOver(self.fast_ma, self.slow_ma)

    def next(self):
        if not self.position:  # 没有持仓
            if self.crossover > 0:  # 快速均线上穿慢速均线
                self.buy()  # 买入
        elif self.crossover < 0:  # 快速均线下穿慢速均线
            self.close()  # 卖出

# 回测设置
def run_backtest(data_path='data.csv'):
    # 创建回测引擎
    cerebro = bt.Cerebro()
    
    # 添加策略
    cerebro.addstrategy(DualMovingAverageStrategy)
    
    # 加载数据
    data = bt.feeds.GenericCSVData(
        dataname=data_path,
        dtformat=('%Y-%m-%d'),
        datetime=0,
        high=2,
        low=3,
        open=1,
        close=4,
        volume=5,
        openinterest=-1
    )
    cerebro.adddata(data)
    
    # 设置初始资金
    cerebro.broker.setcash(100000.0)
    
    # 添加分析器
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # 运行回测
    print('初始资金: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('最终资金: %.2f' % cerebro.broker.getvalue())
    
    # 打印分析结果
    strat = results[0]
    print('夏普比率:', strat.analyzers.sharpe.get_analysis()['sharperatio'])
    print('最大回撤:', strat.analyzers.drawdown.get_analysis()['max']['drawdown'])
    print('年化收益率:', strat.analyzers.returns.get_analysis()['rnorm100'])
    
    # 绘制回测结果
    cerebro.plot(style='candlestick')
    plt.show()

if __name__ == '__main__':
    run_backtest()