import sys
import tushare as ts
from PyQt5.QtWidgets import QApplication, QMainWindow, QTabWidget, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

# 原tushare导入替换为yfinance
import yfinance as yf
import time

# 移除tushare Token配置
# 雅虎财经无需Token，直接使用yfinance

# 板块数据加载逻辑替换（示例）
def load_sector_data(self):
    # 示例：获取A股热门行业指数（雅虎财经）
    try:
        # 自定义行业指数映射（雅虎财经A股指数代码格式：行业缩写.SI）
        sector_mapping = {
            '酿酒行业': '801125.SI',
            '医药制造': '801150.SI',
            '半导体': '801081.SI'
        }
        sector_names = list(sector_mapping.keys())
        self.sector_table.setRowCount(len(sector_names))

        for row, sector in enumerate(sector_names):
            code = sector_mapping[sector]
            ticker = yf.Ticker(code)
            hist = ticker.history(period='1d')  # 获取当日数据
            if not hist.empty:
                close_price = hist['Close'].iloc[-1]
                # 计算涨跌幅（需要前一日收盘价）
                prev_close = ticker.history(period='2d')['Close'].iloc[0]
                pct_chg = ((close_price - prev_close) / prev_close) * 100

                self.sector_table.setItem(row, 0, QTableWidgetItem(sector))
                self.sector_table.setItem(row, 1, QTableWidgetItem(code))
                self.sector_table.setItem(row, 2, QTableWidgetItem(f'{close_price:.2f}'))
                self.sector_table.setItem(row, 3, QTableWidgetItem(f'{pct_chg:.2f}'))
                self.sector_table.setItem(row, 4, QTableWidgetItem('-'))  # 雅虎财经无直接成交量

        self.sector_table.resizeColumnsToContents()
    except Exception as e:
        print(f'加载板块数据失败：{str(e)}')

class StockReviewApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('A股短线复盘助手')
        self.setGeometry(100, 100, 1200, 800)

        # 创建主容器
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # 创建选项卡
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # 初始化各功能模块
        self.init_sector_tab()  # 板块指数
        self.init_leading_stocks_tab()  # 领涨个股

    def init_sector_tab(self):
        # 板块指数标签页
        sector_tab = QWidget()
        self.tabs.addTab(sector_tab, '板块指数')

        # 板块数据表格
        self.sector_table = QTableWidget()
        self.sector_table.setColumnCount(5)
        self.sector_table.setHorizontalHeaderLabels(['板块名称', '指数代码', '当前点位', '涨跌幅(%)', '成交量(手)'])

        # 加载板块数据
        self.load_sector_data()

        layout = QVBoxLayout(sector_tab)
        layout.addWidget(self.sector_table)

    def load_sector_data(self):
        # 加载雅虎财经板块数据
        try:
            sector_mapping = {
                '酿酒行业': '801125.SI',
                '医药制造': '801150.SI',
                '半导体': '801081.SI'
            }
            sector_names = list(sector_mapping.keys())
            self.sector_table.setRowCount(len(sector_names))

            for row, sector in enumerate(sector_names):
                code = sector_mapping[sector]
                ticker = yf.Ticker(code)
                time.sleep(1)  # 每请求一个指数后延迟1秒，避免限流
                hist = ticker.history(period='1d')
                if not hist.empty:
                    close_price = hist['Close'].iloc[-1]
                    prev_close = ticker.history(period='2d')['Close'].iloc[0]
                    pct_chg = ((close_price - prev_close) / prev_close) * 100 if prev_close != 0 else 0

                    self.sector_table.setItem(row, 0, QTableWidgetItem(sector))
                    self.sector_table.setItem(row, 1, QTableWidgetItem(code))
                    self.sector_table.setItem(row, 2, QTableWidgetItem(f'{close_price:.2f}'))
                    self.sector_table.setItem(row, 3, QTableWidgetItem(f'{pct_chg:.2f}'))
                    self.sector_table.setItem(row, 4, QTableWidgetItem('-'))

            self.sector_table.resizeColumnsToContents()
        except Exception as e:
            print(f'加载板块数据失败：{str(e)}')

    def init_leading_stocks_tab(self):
        # 领涨个股标签页
        leading_tab = QWidget()
        self.tabs.addTab(leading_tab, '领涨个股')

        # 领涨股数据表格
        self.leading_table = QTableWidget()
        self.leading_table.setColumnCount(6)
        self.leading_table.setHorizontalHeaderLabels(['股票代码', '股票名称', '当前价', '涨跌幅(%)', '成交额(万元)', '所属板块'])

        layout = QVBoxLayout(leading_tab)
        layout.addWidget(self.leading_table)

    # 原tushare数据获取逻辑已完全替换为雅虎财经（yfinance）实现
    # 移除了对tushare的pro变量依赖
    
    # 板块数据加载方法更新
        def load_sector_data(self):
            # 示例：获取A股热门行业指数（雅虎财经）
            try:
                # 自定义行业指数映射（雅虎财经A股指数代码格式：行业缩写.SI）
                sector_mapping = {
                    '酿酒行业': '801125.SI',
                    '医药制造': '801150.SI',
                    '半导体': '801081.SI'
                }
                sector_names = list(sector_mapping.keys())
                self.sector_table.setRowCount(len(sector_names))
    
                for row, sector in enumerate(sector_names):
                    code = sector_mapping[sector]
                    ticker = yf.Ticker(code)
                    hist = ticker.history(period='1d')  # 获取当日数据
                    if not hist.empty:
                        close_price = hist['Close'].iloc[-1]
                        # 计算涨跌幅（需要前一日收盘价）
                        prev_close = ticker.history(period='2d')['Close'].iloc[0]
                        pct_chg = ((close_price - prev_close) / prev_close) * 100
    
                        self.sector_table.setItem(row, 0, QTableWidgetItem(sector))
                        self.sector_table.setItem(row, 1, QTableWidgetItem(code))
                        self.sector_table.setItem(row, 2, QTableWidgetItem(f'{close_price:.2f}'))
                        self.sector_table.setItem(row, 3, QTableWidgetItem(f'{pct_chg:.2f}'))
                        self.sector_table.setItem(row, 4, QTableWidgetItem('-'))  # 雅虎财经无直接成交量
    
                self.sector_table.resizeColumnsToContents()
            except Exception as e:
                print(f'加载板块数据失败：{str(e)}')

if __name__ == '__main__':


    app = QApplication(sys.argv)
    window = StockReviewApp()
    window.show()
    sys.exit(app.exec_())