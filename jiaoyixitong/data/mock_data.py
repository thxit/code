import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Optional

def generate_mock_north_flow(period: int = 60) -> pd.DataFrame:
    """生成模拟北向资金数据"""
    dates = [datetime.now() - timedelta(days=i) for i in range(period)][::-1]
    dates = [d for d in dates if d.weekday() < 5]  # 只保留工作日
    
    np.random.seed(42)
    flows = np.random.normal(20, 30, len(dates))  # 均值20亿，标准差30亿
    
    df = pd.DataFrame({
        'date': dates,
        'net_flow': flows,
        'amount': np.abs(flows) * np.random.uniform(0.8, 1.2, len(dates)) * 10
    })
    
    return df

def generate_mock_industry_flow() -> pd.DataFrame:
    """生成模拟行业资金流数据"""
    industries = [
        '电子', '医药生物', '计算机', '电力设备', '食品饮料',
        '机械设备', '化工', '有色金属', '国防军工', '汽车',
        '银行', '非银金融', '建筑装饰', '交通运输', '家用电器'
    ]
    
    np.random.seed(42)
    df = pd.DataFrame({
        '行业名称': industries,
        '涨跌幅': np.random.uniform(-5, 5, len(industries)),
        '净流入': np.random.uniform(-50, 100, len(industries)),
        '成交额': np.random.uniform(50, 500, len(industries))
    })
    
    return df.sort_values('净流入', ascending=False).reset_index(drop=True)

def generate_mock_sentiment() -> pd.DataFrame:
    """生成模拟市场情绪数据"""
    stocks = [
        ('000001', '平安银行'), ('000002', '万科A'), ('000858', '五粮液'),
        ('600519', '贵州茅台'), ('601318', '中国平安'), ('002594', '比亚迪'),
        ('300750', '宁德时代'), ('600036', '招商银行'), ('000333', '美的集团'),
        ('601899', '紫金矿业'), ('600030', '中信证券'), ('300059', '东方财富'),
        ('000651', '格力电器'), ('601398', '工商银行'), ('600104', '上汽集团')
    ]
    
    np.random.seed(42)
    df = pd.DataFrame({
        '代码': [s[0] for s in stocks],
        '名称': [s[1] for s in stocks],
        '最新价': np.random.uniform(5, 200, len(stocks)),
        '涨跌幅': np.random.uniform(-10, 10, len(stocks)),
        '成交量': np.random.uniform(10000, 500000, len(stocks)),
        '涨停': np.random.choice([True, False], len(stocks), p=[0.2, 0.8])
    })
    
    return df

def generate_mock_concept_flow() -> pd.DataFrame:
    """生成模拟概念板块资金流数据"""
    concepts = [
        '人工智能', '数字经济', '新能源', '光伏概念', '储能',
        '半导体', '消费复苏', '国企改革', '一带一路', '军工'
    ]
    
    np.random.seed(42)
    df = pd.DataFrame({
        '概念名称': concepts,
        '涨跌幅': np.random.uniform(-3, 8, len(concepts)),
        '净流入': np.random.uniform(-30, 80, len(concepts)),
        '领涨股': ['股票A', '股票B', '股票C', '股票D', '股票E',
                  '股票F', '股票G', '股票H', '股票I', '股票J']
    })
    
    return df.sort_values('净流入', ascending=False).reset_index(drop=True)