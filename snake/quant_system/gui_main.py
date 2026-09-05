"""
A股量化分析系统 - 可视化图形界面 v2.0
修复: HTML渲染/QPixmap缩放/初始空白/窗口自适应
"""

import os
import sys
import logging
from datetime import datetime
from typing import Dict, Optional
from functools import partial

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTextBrowser, QListWidget, QListWidgetItem,
    QStackedWidget, QSplitter, QStatusBar, QProgressBar,
    QMessageBox, QScrollArea, QSizePolicy, QFrame,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QImage

SYSTEM_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SYSTEM_DIR)

import matplotlib
matplotlib.use('Agg')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(SYSTEM_DIR, 'cache')
REPORT_DIR = os.path.join(SYSTEM_DIR, 'reports')
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)
os.chdir(SYSTEM_DIR)


STYLESHEET = """
QMainWindow { background-color: #f0f2f5; }
QListWidget {
    background-color: #1a1a2e; color: #e0e0e0;
    border: none; font-size: 14px; padding: 8px; outline: none;
}
QListWidget::item {
    padding: 12px 16px; border-radius: 6px;
    margin: 2px 4px; color: #cccccc;
}
QListWidget::item:selected {
    background-color: #e94560; color: white; font-weight: bold;
}
QListWidget::item:hover:!selected {
    background-color: #16213e; color: #ffffff;
}
QPushButton {
    background-color: #e94560; color: white; border: none;
    border-radius: 6px; padding: 10px 24px;
    font-size: 14px; font-weight: bold;
}
QPushButton:hover { background-color: #c73650; }
QPushButton:pressed { background-color: #a32d43; }
QPushButton:disabled { background-color: #888888; }
QPushButton#btnRunSingle {
    background-color: #0f3460; font-size: 12px; padding: 6px 16px;
}
QPushButton#btnRunSingle:hover { background-color: #1a4a7a; }
QTextBrowser {
    background-color: #ffffff;
    border: 1px solid #ddd;
    border-radius: 6px;
    padding: 12px;
    font-size: 13px;
    font-family: 'Consolas', 'Microsoft YaHei', monospace;
}
QStatusBar {
    background-color: #1a1a2e; color: #e0e0e0; font-size: 12px;
}
QProgressBar {
    border: none; border-radius: 4px;
    background-color: #e0e0e0; height: 6px; text-align: center;
}
QProgressBar::chunk { background-color: #e94560; border-radius: 4px; }
QFrame#imageFrame {
    background-color: #fafafa;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
}
"""


# ==================== 异步工作线程 ====================

class AnalysisWorker(QThread):
    finished = pyqtSignal(dict)
    progress = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, module: str, use_cache: bool = True):
        super().__init__()
        self.module = module
        self.use_cache = use_cache

    def run(self):
        try:
            self.progress.emit(f'正在运行 {self.module} 分析...')
            result = {}
            if self.module == '全部':
                import main
                result = main.run_quant_system(use_cache=self.use_cache)
            elif self.module == '指数分析':
                from index_analyzer import analyze_all_indices
                result = analyze_all_indices(use_cache=self.use_cache)
            elif self.module == '板块轮动':
                from sector_rotation import run_sector_rotation
                result = run_sector_rotation(use_cache=self.use_cache)
            elif self.module == '热点识别':
                from hot_spot import get_hot_spot_briefing
                result = get_hot_spot_briefing(use_cache=self.use_cache)
            elif self.module == '短线情绪':
                from sentiment import compute_sentiment_score
                result = compute_sentiment_score(use_cache=self.use_cache)
            elif self.module == 'ETF轮动':
                from etf_rotation import get_weekly_rotation_signal, run_etf_backtest, plot_etf_backtest
                signal = get_weekly_rotation_signal(use_cache=self.use_cache)
                backtest = run_etf_backtest(use_cache=self.use_cache)
                if 'error' not in backtest:
                    plot_etf_backtest(backtest)
                result = {'signal': signal, 'backtest': backtest}
            elif self.module == '风险评估':
                from risk_assessment import assess_comprehensive_risk, plot_risk_radar
                result = assess_comprehensive_risk(use_cache=self.use_cache)
                plot_risk_radar(result)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(f'{self.module} 运行失败: {str(e)}')
            logger.exception(f'{self.module} 运行失败')


# ==================== 图片加载器（带Pillow回退） ====================

def load_pixmap(path: str) -> Optional[QPixmap]:
    if not path or not os.path.exists(path):
        return None
    pix = QPixmap(path)
    if not pix.isNull():
        return pix
    try:
        from PIL import Image
        img = Image.open(path)
        img = img.convert('RGB')
        data = img.tobytes('raw', 'RGB')
        qimg = QImage(data, img.width, img.height, QImage.Format_RGB888)
        if not qimg.isNull():
            return QPixmap.fromImage(qimg)
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f'Pillow备用加载失败 [{path}]: {e}')
    return None


# ==================== 页面基类 ====================

class PageBase(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_image_path = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self.text_browser = QTextBrowser()
        self.text_browser.setMinimumHeight(180)

        self.image_frame = QFrame()
        self.image_frame.setObjectName('imageFrame')
        self.image_frame.setStyleSheet(
            'QFrame#imageFrame { background-color: #fafafa; '
            'border: 1px solid #e0e0e0; border-radius: 6px; }'
        )
        frame_layout = QVBoxLayout(self.image_frame)
        frame_layout.setContentsMargins(8, 8, 8, 8)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding
        )
        self.image_label.setMinimumSize(200, 150)
        self.image_label.setWordWrap(True)
        self.image_label.setStyleSheet('background: transparent;')
        frame_layout.addWidget(self.image_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.image_frame)
        self.scroll.setMinimumHeight(250)
        self.scroll.setFrameShape(QFrame.NoFrame)

        layout.addWidget(self.text_browser, 2)
        layout.addWidget(self.scroll, 3)

    def set_html(self, html: str):
        self.text_browser.setHtml(html)

    def set_image(self, image_path: Optional[str]):
        self._current_image_path = image_path
        if not image_path:
            self._show_placeholder('暂无图表')
            return
        pix = load_pixmap(image_path)
        if pix is None:
            self._show_placeholder(f'未找到图表\n{os.path.basename(image_path)}')
            return
        self._display_pixmap(pix)

    def _display_pixmap(self, pix: QPixmap):
        area_size = self.scroll.viewport().size()
        avail_w = max(area_size.width() - 20, 100)
        avail_h = max(area_size.height() - 20, 100)
        scaled = pix.scaled(
            avail_w, avail_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setFixedSize(scaled.size())

    def _show_placeholder(self, text: str):
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText(
            f'<div style="color:#999;padding:50px;text-align:center;'
            f'font-size:14px;">{text}</div>'
        )
        self.image_label.setFixedSize(400, 200)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._current_image_path:
            pix = load_pixmap(self._current_image_path)
            if pix:
                self._display_pixmap(pix)


class OverviewPage(PageBase):
    def __init__(self, parent=None):
        super().__init__(parent)
        title = QLabel('📊 A股量化分析系统 - 综合看板')
        title.setStyleSheet(
            'font-size: 22px; font-weight: bold; color: #1a1a2e; padding: 8px 0;'
        )
        desc = QLabel(
            '点击左侧导航栏切换模块 | 点击"运行全部"更新所有数据'
        )
        desc.setStyleSheet('color: #666; font-size: 13px; padding: 0 0 12px 0;')
        self.layout().insertWidget(0, desc)
        self.layout().insertWidget(0, title)


class ChartPage(PageBase):
    def __init__(self, module_name: str, parent=None):
        super().__init__(parent)
        header = QHBoxLayout()
        self.title = QLabel(f'📈 {module_name}')
        self.title.setStyleSheet(
            'font-size: 20px; font-weight: bold; color: #1a1a2e; padding: 4px 0;'
        )
        header.addWidget(self.title)
        header.addStretch()
        self.btn_run = QPushButton(f'▶ 运行{module_name}')
        self.btn_run.setObjectName('btnRunSingle')
        header.addWidget(self.btn_run)
        hw = QWidget()
        hw.setLayout(header)
        self.layout().insertWidget(0, hw)


# ==================== 主窗口 ====================

class QuantGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('A股量化分析系统 v2.0')
        self.setGeometry(100, 50, 1400, 850)
        self.setMinimumSize(1000, 650)

        self.cache_enabled = True
        self.results_cache = {}
        self.module_names = [
            '综合看板', '指数分析', '板块轮动',
            '热点识别', '短线情绪', 'ETF轮动', '风险评估',
        ]

        self._init_ui()
        self._init_status()
        self._show_welcome()

    def _init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---- 左侧导航 ----
        nav_panel = QWidget()
        nav_panel.setFixedWidth(200)
        nav_panel.setStyleSheet('background-color: #1a1a2e;')
        nav_layout = QVBoxLayout(nav_panel)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        logo = QLabel('📊 量化系统')
        logo.setStyleSheet(
            'color: white; font-size: 18px; font-weight: bold; '
            'padding: 20px 16px; background-color: #0f3460;'
        )
        logo.setAlignment(Qt.AlignCenter)
        nav_layout.addWidget(logo)

        self.nav_list = QListWidget()
        self.nav_list.setFont(QFont('Microsoft YaHei', 12))
        for t in self.module_names:
            self.nav_list.addItem(QListWidgetItem(t))
        nav_layout.addWidget(self.nav_list, 1)

        btn_all = QPushButton('▶ 运行全部')
        btn_all.setStyleSheet(
            'QPushButton { background-color: #e94560; color: white; '
            'border: none; border-radius: 0; padding: 14px; '
            'font-size: 15px; font-weight: bold; }'
            'QPushButton:hover { background-color: #c73650; }'
        )
        nav_layout.addWidget(btn_all)

        self.cache_btn = QPushButton('✓ 缓存已启用')
        self.cache_btn.setCheckable(True)
        self.cache_btn.setChecked(True)
        self.cache_btn.setStyleSheet(
            'QPushButton { background-color: #16213e; color: #a0e0a0; '
            'border: none; padding: 10px; font-size: 12px; }'
            'QPushButton:checked { background-color: #16213e; color: #e94560; }'
        )
        nav_layout.addWidget(self.cache_btn)

        # ---- 右侧堆叠页面 ----
        self.stack = QStackedWidget()
        self.pages = {}
        self.pages['综合看板'] = OverviewPage()
        for name in self.module_names[1:]:
            self.pages[name] = ChartPage(name)
        for name in self.module_names:
            self.stack.addWidget(self.pages[name])

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(nav_panel)
        splitter.addWidget(self.stack)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setHandleWidth(0)
        main_layout.addWidget(splitter)

        # 信号
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        btn_all.clicked.connect(self._run_all_modules)
        self.cache_btn.clicked.connect(self._toggle_cache)
        for name in self.module_names[1:]:
            self.pages[name].btn_run.clicked.connect(
                partial(self._run_single_module, name)
            )

    def _init_status(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        self.status_label = QLabel('就绪 | 点击"运行全部"开始分析')
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setMaximumHeight(16)
        self.progress_bar.setVisible(False)
        sb.addWidget(self.status_label, 1)
        sb.addPermanentWidget(self.progress_bar)

    def _show_welcome(self):
        html = (
            '<div style="text-align:center;padding:40px 20px;">'
            '<h2 style="color:#1a1a2e;">欢迎使用 A股量化分析系统</h2>'
            '<p style="color:#666;font-size:15px;line-height:2.0;">'
            '请点击左侧底部 <b>"▶ 运行全部"</b> 按钮开始完整分析<br>'
            '或点击各模块右上角的 <b>"▶ 运行模块名"</b> 单独分析<br><br>'
            '系统将依次执行：指数分析 → 板块轮动 → 热点识别<br>'
            '短线情绪 → ETF轮动 → 综合风险评估<br><br>'
            f'<span style="color:#999;">运行时间: '
            f'{datetime.now().strftime("%Y-%m-%d %H:%M")}</span>'
            '</p></div>'
        )
        self.pages['综合看板'].set_html(html)
        self.pages['综合看板'].set_image(None)

    def _toggle_cache(self):
        self.cache_enabled = self.cache_btn.isChecked()
        self.cache_btn.setText(
            '✓ 缓存已启用' if self.cache_enabled else '✗ 缓存已禁用'
        )

    def _on_nav_changed(self, index: int):
        if 0 <= index < self.stack.count():
            self.stack.setCurrentIndex(index)
            name = self.module_names[index]
            data = self.results_cache.get(name)
            if data:
                self._render_page(name, data)

    def _render_page(self, page_name: str, data):
        page = self.pages.get(page_name)
        if not page:
            return
        renderer = getattr(self, f'_render_{page_name}', None)
        if renderer:
            renderer(page, data)
        QApplication.processEvents()

    # ---- 页面渲染函数 ----

    def _render_综合看板(self, page: PageBase, data: dict):
        lines = ['<h3>📊 系统运行摘要</h3>']
        now = datetime.now().strftime('%Y-%m-%d %H:%M')
        lines.append(f'<p>运行时间: {now}</p><hr>')

        idx = data.get('index_result') or {}
        if idx and isinstance(idx, dict):
            scores = [
                r.get('total_score', 50) for r in idx.values()
                if isinstance(r, dict)
            ]
            if scores:
                avg = sum(scores) / len(scores)
                lines.append(f'<p>📈 三大指数均分: <b>{avg:.1f}</b></p>')

        risk = data.get('risk_result') or {}
        if isinstance(risk, dict) and risk.get('risk_score') is not None:
            rs = risk['risk_score']
            rl = risk.get('risk_level', '')
            color = '#e74c3c' if rs >= 50 else '#2ecc71'
            lines.append(
                f'<p>⚠️ 综合风险: <b style="color:{color};">{rs}</b>'
                f' - {rl}</p>'
            )

        sent = data.get('sentiment_result') or {}
        if isinstance(sent, dict) and sent.get('total_score') is not None:
            lines.append(
                f'<p>💹 短线情绪: <b>{sent["total_score"]}</b>'
                f' - {sent.get("level", "")}</p>'
            )

        sec = data.get('sector_result') or {}
        if isinstance(sec, dict) and sec.get('top_sectors'):
            lines.append(f'<p>🔄 强势板块: {len(sec["top_sectors"])}个</p>')

        etf = data.get('etf_signal') or {}
        if etf:
            if etf.get('defensive'):
                lines.append('<p>📦 ETF: 防御模式</p>')
            else:
                names = [h.get('name', '') for h in etf.get('holdings', [])]
                if names:
                    lines.append(f'<p>📦 ETF持仓: {" + ".join(names)}</p>')

        lines.append('<hr><p style="color:#999;">点击左侧模块查看详细分析</p>')
        page.set_html('\n'.join(lines))
        ip = os.path.join(REPORT_DIR, 'risk_assessment.png')
        page.set_image(ip if os.path.exists(ip) else None)

    def _render_指数分析(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        lines = ['<h3>📈 三大指数综合分析</h3>']
        lines.append(f'<p>更新: {datetime.now().strftime("%Y-%m-%d %H:%M")}</p><hr>')
        for name, r in data.items():
            score = r.get('total_score', 50)
            jdg = r.get('judgment', '中性')
            color = '#2ecc71' if score >= 60 else (
                '#f39c12' if score >= 40 else '#e74c3c')
            lines.append(
                f'<h4>{name} <span style="color:{color};">[{jdg}]</span></h4>'
            )
            lines.append(f'<p>综合评分: <b>{score}</b></p>')
            pe = r.get('details', {}).get('pe', {})
            if pe:
                lines.append(
                    f'<p>PE: {pe.get("current_pe", "N/A")} '
                    f'(历史分位: {pe.get("percentile", "N/A")}%) | '
                    f'评估: {pe.get("evaluation", "N/A")}</p>'
                )
            d = r.get('details', {})
            lines.append(
                f'<p>MA20: {d.get("ma20_trend", "N/A")} | '
                f'MA60: {d.get("ma60_trend", "N/A")}</p><hr>'
            )
        page.set_html('\n'.join(lines))
        img = None
        for name in data:
            p = os.path.join(REPORT_DIR, f'{name}_kline.png')
            if os.path.exists(p):
                img = p
                break
        page.set_image(img)

    def _render_板块轮动(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        lines = ['<h3>🔄 板块轮动分析</h3>']
        lines.append(
            f'<p>更新: {data.get("date", datetime.now().strftime("%Y-%m-%d"))}</p>'
        )
        if data.get('defensive'):
            lines.append(
                '<p style="color:#e74c3c;">⚠ 防御模式: 全市场板块动量偏弱</p>'
            )
        else:
            n = len(data.get('top_sectors', []))
            lines.append(f'<p>强势板块: {n}个</p>')
        lines.append('<hr><h4>强势板块排名 TOP10</h4>')
        headers = ['排名', '板块', '20日动量', '60日动量', 'MA20方向']
        rows = []
        for s in data.get('top_sectors', [])[:10]:
            rows.append([
                str(s.get('rank', '')), s.get('sector', ''),
                f'{s.get("momentum_20d", 0):+.1f}%',
                f'{s.get("momentum_60d", 0):+.1f}%',
                s.get('ma20_dir', ''),
            ])
        lines.append(self._build_table(headers, rows))
        page.set_html('\n'.join(lines))
        ip = data.get('charts', {}).get('heatmap')
        if not (ip and os.path.exists(ip)):
            ip = os.path.join(REPORT_DIR, 'sector_momentum_heatmap.png')
        page.set_image(ip if os.path.exists(ip) else None)

    def _render_热点识别(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        lines = ['<h3>🔥 热点识别分析</h3>']
        lines.append(
            f'<p>更新: {data.get("date", datetime.now().strftime("%Y-%m-%d"))}</p><hr>'
        )
        lu = data.get('limit_up_analysis', {})
        lines.append('<h4>涨停板分析</h4>')
        lines.append(f'<p>涨停总数: {lu.get("total_limit", 0)}只</p>')
        lines.append(f'<p>热点集中度: {lu.get("clustering_level", "N/A")}</p>')
        lines.append(
            f'<p>核心热点: {lu.get("top_sector", "无")} '
            f'({lu.get("top_sector_count", 0)}只涨停)</p>'
        )
        hs = lu.get('hot_sectors', [])
        if hs:
            lines.append('<h4>热点板块分布</h4>')
            lines.append(self._build_table(
                ['板块', '涨停数', '占比'],
                [[s.get('sector', ''), str(s.get('limit_up_count', 0)),
                  f'{s.get("ratio", 0)}%'] for s in hs[:8]]
            ))
        va = data.get('volume_anomalies', {})
        sv = va.get('sector_anomalies', [])
        if sv:
            lines.append('<h4>资金异动行业（放量）</h4>')
            lines.append(self._build_table(
                ['行业', '量比'],
                [[s.get('sector', ''), f'{s.get("volume_ratio", 0):.2f}']
                 for s in sv[:6]]
            ))
        lines.append(f'<hr><h4>热点简报</h4><p>{data.get("summary", "暂无数据")}</p>')
        page.set_html('\n'.join(lines))
        page.set_image(None)

    def _render_短线情绪(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        score = data.get('total_score', 50)
        level = data.get('level', '未知')
        cmap = {
            '极度恐慌': '#e74c3c', '偏弱': '#e67e22',
            '中性': '#f1c40f', '偏暖': '#2ecc71', '极度亢奋': '#e74c3c',
        }
        color = cmap.get(level, '#333')
        lines = ['<h3>💹 短线情绪分析</h3>']
        lines.append(
            f'<p>更新: {data.get("date", datetime.now().strftime("%Y-%m-%d"))}</p><hr>'
        )
        lines.append(
            f'<h2 style="color:{color};text-align:center;">'
            f'综合情绪评分: {score}/100</h2>'
        )
        lines.append(
            f'<h3 style="color:{color};text-align:center;">{level}</h3><hr>'
        )
        lines.append('<h4>分项指标</h4>')
        cn = {
            'up_down_ratio': '涨跌比', 'limit_up_ratio': '涨停/跌停比',
            'prev_limit_up_perf': '昨日涨停表现', 'break_rate': '炸板率',
            'max_continuous': '最高连板', 'market_breadth': '市场宽度',
        }
        rows = []
        for k, v in data.get('components', {}).items():
            rows.append([cn.get(k, k), str(v.get('score', 0)), v.get('detail', '')])
        lines.append(self._build_table(['指标', '评分', '数值'], rows))
        page.set_html('\n'.join(lines))
        page.set_image(None)

    def _render_ETF轮动(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        lines = ['<h3>📦 ETF轮动分析</h3>']
        lines.append(
            f'<p>更新: {datetime.now().strftime("%Y-%m-%d")}</p><hr>'
        )
        sig = data.get('signal', {})
        lines.append('<h4>轮动信号</h4>')
        if sig.get('defensive'):
            lines.append(
                '<p style="color:#e74c3c;">⚠ 防御模式: '
                '所有ETF动量转负，建议持有现金/货币基金</p>'
            )
        else:
            for h in sig.get('holdings', []):
                lines.append(
                    f'<p>▶ 持有: <b>{h.get("name", "")}</b> '
                    f'(动量: {h.get("momentum", 0):+.1f}%)</p>'
                )
        lines.append('<hr><h4>全部ETF动量排名</h4>')
        am = sig.get('all_momentum', {})
        sm = sorted(am.items(), key=lambda x: x[1], reverse=True)
        lines.append(self._build_table(
            ['ETF', '20日动量'],
            [[n, f'{m:+.1f}%'] for n, m in sm]
        ))
        bt = data.get('backtest', {})
        if bt and 'error' not in bt:
            lines.append('<hr><h4>回测绩效</h4>')
            lines.append(
                f'<p>回测期间: {bt.get("start_date", "N/A")} ~ '
                f'{bt.get("end_date", "N/A")} ({bt.get("years", 0):.1f}年)</p>'
            )
            lines.append(
                f'<p>累计收益: <b>{bt.get("total_return", 0):+.1f}%</b> '
                f'(基准: {bt.get("benchmark_return", 0):+.1f}%)</p>'
            )
            lines.append(
                f'<p>年化收益: {bt.get("annual_return", 0):+.1f}% | '
                f'最大回撤: {bt.get("max_drawdown", 0):.1f}% | '
                f'夏普比率: {bt.get("sharpe_ratio", 0):.2f}</p>'
            )
        page.set_html('\n'.join(lines))
        ip = os.path.join(REPORT_DIR, 'etf_backtest.png')
        page.set_image(ip if os.path.exists(ip) else None)

    def _render_风险评估(self, page: PageBase, data: dict):
        if not data:
            page.set_html('<p>暂无数据，请先运行分析</p>')
            return
        rs = data.get('risk_score', 50)
        rl = data.get('risk_level', '未知')
        cmap = {
            '低风险': '#2ecc71', '中风险': '#f1c40f',
            '高风险': '#e67e22', '极高风险': '#e74c3c',
        }
        color = cmap.get(rl, '#333')
        lines = ['<h3>⚠️ 综合风险评估</h3>']
        lines.append(
            f'<p>更新: {data.get("date", datetime.now().strftime("%Y-%m-%d"))}</p><hr>'
        )
        lines.append(
            f'<h2 style="color:{color};text-align:center;">'
            f'综合风险评分: {rs}/100</h2>'
        )
        lines.append(
            f'<h3 style="color:{color};text-align:center;">{rl}</h3><hr>'
        )
        dm = {
            'index_system': '指数系统', 'momentum_decay': '动量衰减',
            'sentiment_extreme': '情绪极端', 'hotspot_shift': '热点切换',
        }
        rows = []
        for k, v in data.get('dimensions', {}).items():
            rows.append([dm.get(k, k), f'{v.get("score", 0)}', v.get('detail', '')])
        lines.append('<h4>各维度评分</h4>')
        lines.append(self._build_table(['维度', '风险评分', '详情'], rows))
        lines.append('<hr><h4>操作建议</h4>')
        for s in data.get('suggestions', []):
            lines.append(f'<p>→ {s}</p>')
        page.set_html('\n'.join(lines))
        ip = os.path.join(REPORT_DIR, 'risk_assessment.png')
        page.set_image(ip if os.path.exists(ip) else None)

    # ---- 工具方法 ----

    def _build_table(self, headers: list, rows: list) -> str:
        hdr = ''.join(
            f'<th style="padding:8px 12px;background:#1a1a2e;color:white;'
            f'font-size:13px;">{h}</th>' for h in headers
        )
        bd = ''
        for row in rows:
            cells = ''
            for c in row:
                s = str(c)
                if s.startswith('+') and '%' in s:
                    cl = '#e74c3c'
                elif s.startswith('-') and '%' in s:
                    cl = '#2ecc71'
                else:
                    cl = '#333'
                cells += f'<td style="padding:6px 12px;color:{cl};">{s}</td>'
            bd += f'<tr style="border-bottom:1px solid #eee;">{cells}</tr>'
        return (
            '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
            f'<thead><tr>{hdr}</tr></thead><tbody>{bd}</tbody></table>'
        )

    # ---- 运行控制 ----

    def _run_all_modules(self):
        self._run_worker('全部')

    def _run_single_module(self, name: str):
        self._run_worker(name)

    def _run_worker(self, module: str):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText(f'正在运行 {module} 分析...')
        for p in self.pages.values():
            if hasattr(p, 'btn_run'):
                p.btn_run.setEnabled(False)
        self.cache_btn.setEnabled(False)
        self.nav_list.setEnabled(False)

        self.worker = AnalysisWorker(module, use_cache=self.cache_enabled)
        self.worker.finished.connect(lambda r: self._on_done(module, r))
        self.worker.error.connect(self._on_error)
        self.worker.progress.connect(self.status_label.setText)
        self.worker.start()

    def _on_done(self, module: str, result: dict):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.cache_btn.setEnabled(True)
        self.nav_list.setEnabled(True)
        for p in self.pages.values():
            if hasattr(p, 'btn_run'):
                p.btn_run.setEnabled(True)

        if module == '全部':
            self.results_cache['综合看板'] = result
            self.results_cache['指数分析'] = result.get('index_result', {})
            self.results_cache['板块轮动'] = result.get('sector_result', {})
            self.results_cache['热点识别'] = result.get('hot_spot_result', {})
            self.results_cache['短线情绪'] = result.get('sentiment_result', {})
            self.results_cache['ETF轮动'] = {
                'signal': result.get('etf_signal', {}),
                'backtest': result.get('etf_backtest', {}),
            }
            self.results_cache['风险评估'] = result.get('risk_result', {})
        else:
            self.results_cache[module] = result

        idx = self.nav_list.currentRow()
        if 0 <= idx < len(self.module_names):
            name = self.module_names[idx]
            self._render_page(name, self.results_cache.get(name, result))

        self.status_label.setText(f'{module} 分析完成 ✓')
        QMessageBox.information(self, '完成', f'{module} 分析已完成！')

    def _on_error(self, msg: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText('运行出错')
        self.cache_btn.setEnabled(True)
        self.nav_list.setEnabled(True)
        for p in self.pages.values():
            if hasattr(p, 'btn_run'):
                p.btn_run.setEnabled(True)
        QMessageBox.warning(self, '运行错误', msg)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    app.setFont(QFont('Microsoft YaHei', 10))
    w = QuantGUI()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
