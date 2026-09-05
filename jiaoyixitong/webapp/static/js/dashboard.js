var charts = {};
var currentTab = 'sector';

Chart.defaults.color = '#8890a8';
Chart.defaults.borderColor = '#2a2e42';
Chart.defaults.font.family = "'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif";

function chartColors() {
  return {
    green: '#00c087', red: '#f24855', yellow: '#f5a623',
    blue: '#4a7dff', cyan: '#00d4d4', purple: '#9b59b6',
    white: '#e0e4f0', muted: '#5a6078',
  };
}

function destroyChart(key) {
  if (charts[key]) { charts[key].destroy(); charts[key] = null; }
}

function createChart(key, ctx, config) {
  destroyChart(key);
  charts[key] = new Chart(ctx, config);
  return charts[key];
}

function setStatus(state, text) {
  var el = document.getElementById('header-status');
  var dot = el.querySelector('.status-dot');
  el.className = 'header-status status-' + state;
  dot.className = 'status-dot dot-' + state;
  document.getElementById('status-text').textContent = text;
}

function showLoading(msg) {
  document.getElementById('loading-text').textContent = msg || '正在分析中...';
  document.getElementById('loading-overlay').style.display = 'flex';
}

function hideLoading() {
  document.getElementById('loading-overlay').style.display = 'none';
}

function formatNum(n, d) { d = d || 2; return n != null ? Number(n).toFixed(d) : '--'; }
function formatPct(n) { return n != null ? (Number(n) >= 0 ? '+' : '') + Number(n).toFixed(2) + '%' : '--'; }

function runAnalysis(mode) {
  showLoading(mode === 'full' ? '全面分析中，请稍候...' : '快速分析中...');
  setStatus('loading', '分析中');

  fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: mode }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data.error) {
        throw new Error(data.error || '分析失败');
      }
      renderAll(data);
      setStatus('done', '分析完成');
      hideLoading();
    })
    .catch(function (err) {
      console.error(err);
      setStatus('idle', '分析失败');
      hideLoading();
      alert('分析失败: ' + (err.message || '未知错误'));
    });
}

function renderAll(d) {
  document.getElementById('header-time').textContent =
    d.meta ? d.meta.analysis_time : '--';
  renderSignal(d.trading_signal);
  renderMarketTrend(d.market_trend);
  renderIndicators(d.market_trend);
  renderSectorRotation(d.sector_rotation);
  renderSentiment(d.sentiment);
  renderCapitalFlow(d.capital_flow);
  renderStocks(d.recommended_stocks);
  renderBacktest(d.backtest);
  renderRisk(d.risk_assessment);
  renderReasons(d.trading_signal);
  document.getElementById('reasons-row').style.display = 'flex';
}

function renderSignal(sig) {
  if (!sig) return;
  var action = sig.action || '--';
  var actionEl = document.getElementById('signal-action');
  var card = document.getElementById('signal-card');

  actionEl.textContent = action;
  card.className = 'card stat-card signal-card';

  if (action === '开仓') {
    actionEl.className = 'stat-value value-up';
    card.classList.add('signal-bullish');
  } else if (action === '清仓') {
    actionEl.className = 'stat-value value-down';
    card.classList.add('signal-bearish');
  } else {
    actionEl.className = 'stat-value value-neutral';
  }

  document.getElementById('signal-strength').textContent =
    (sig.strength ? '(强度: ' + sig.strength + ')' : '') +
    ' | 止损' + formatPct(sig.stop_loss) + ' | 止盈' + formatPct(sig.take_profit);

  var score = sig.score != null ? sig.score : 0;
  document.getElementById('signal-score').textContent = formatNum(score * 100, 0);
  document.getElementById('score-indicator').style.left = (score * 100) + '%';
}

function renderReasons(sig) {
  if (!sig) return;
  var pro = document.getElementById('reasons-pro');
  var con = document.getElementById('reasons-con');
  pro.innerHTML = '';
  con.innerHTML = '';
  (sig.reasons || []).forEach(function (r) {
    pro.innerHTML += '<li class="reason-pro">+ ' + r + '</li>';
  });
  (sig.warnings || []).forEach(function (w) {
    con.innerHTML += '<li class="reason-con">! ' + w + '</li>';
  });
  if (!pro.innerHTML) pro.innerHTML = '<li class="reason-pro">--</li>';
  if (!con.innerHTML) con.innerHTML = '<li class="reason-con">--</li>';
}

function renderRisk(risk) {
  if (!risk) return;
  var level = risk.risk_level || '--';
  var el = document.getElementById('risk-level');
  el.textContent = level;
  el.className = 'stat-value';
  if (level.indexOf('低') >= 0) el.classList.add('risk-level-low');
  else if (level.indexOf('中') >= 0) el.classList.add('risk-level-mid');
  else el.classList.add('risk-level-high');

  document.getElementById('risk-detail').textContent =
    '波动: ' + (risk.volatility_level || '--') +
    ' | ATR: ' + formatNum(risk.ATR_pct) + '%';

  var pos = risk.adjusted_position != null ? risk.adjusted_position : 0;
  document.getElementById('position-advice').textContent = formatNum(pos * 100, 0) + '%';
  document.getElementById('position-detail').textContent =
    '单票上限: ' + formatNum((risk.single_stock_max || 0) * 100, 0) + '%';
}

function renderMarketTrend(mt) {
  if (!mt) return;
  var trend = mt.trend || {};
  var mom = mt.momentum || {};
  var vol = mt.volume || {};
  var sr = mt.support_resistance || {};

  document.getElementById('trend-signal').textContent = mt.overall_signal || '--';
  var badge = document.getElementById('trend-signal');
  if ((mt.overall_signal || '').indexOf('多') >= 0) badge.className = 'badge badge-green';
  else if ((mt.overall_signal || '').indexOf('空') >= 0) badge.className = 'badge badge-red';
  else badge.className = 'badge badge-yellow';

  var dates = [], prices = [], ma5 = [], ma10 = [], ma20 = [], ma60 = [];
  if (mt._raw_df) {
    var df = mt._raw_df;
    for (var i = 0; i < df.length; i++) {
      dates.push(df[i].date || '');
      prices.push(df[i].close);
      ma5.push(df[i].MA5);
      ma10.push(df[i].MA10);
      ma20.push(df[i].MA20);
      ma60.push(df[i].MA60);
    }
  }

  renderTechnicalCharts(mt);
}

function renderTechnicalCharts(mt) {
  if (!mt || !mt._raw_df) return;
  var df = mt._raw_df;
  var dates = [], closes = [], macdDifs = [], macdDeas = [], macdHists = [],
      rsis = [], kdjKs = [], kdjDs = [], kdjJs = [], ma5s = [], ma10s = [], ma20s = [], ma60s = [],
      bollUp = [], bollMid = [], bollDn = [];

  for (var i = 0; i < df.length; i++) {
    var row = df[i];
    var d = row.date || '';
    dates.push(typeof d === 'string' ? d.slice(5) : d);
    closes.push(row.close);
    ma5s.push(row.MA5);
    ma10s.push(row.MA10);
    ma20s.push(row.MA20);
    ma60s.push(row.MA60);
    macdDifs.push(row.MACD_DIF);
    macdDeas.push(row.MACD_DEA);
    macdHists.push(row.MACD_HIST);
    rsis.push(row.RSI);
    kdjKs.push(row.KDJ_K);
    kdjDs.push(row.KDJ_D);
    kdjJs.push(row.KDJ_J);
    bollUp.push(row.BOLL_UP);
    bollMid.push(row.BOLL_MID);
    bollDn.push(row.BOLL_DN);
  }

  var c = chartColors();

  createChart('price', document.getElementById('chart-price'), {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        { label: '收盘价', data: closes, borderColor: c.white, borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
        { label: 'MA5', data: ma5s, borderColor: c.yellow, borderWidth: 1, pointRadius: 0 },
        { label: 'MA10', data: ma10s, borderColor: c.blue, borderWidth: 1, pointRadius: 0 },
        { label: 'MA20', data: ma20s, borderColor: c.purple, borderWidth: 1, pointRadius: 0 },
        { label: 'MA60', data: ma60s, borderColor: c.cyan, borderWidth: 1, pointRadius: 0 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { boxWidth: 12, padding: 8, font: { size: 10 } } } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });

  var macdColors = macdHists.map(function (v) { return v >= 0 ? c.green : c.red; });

  createChart('macd', document.getElementById('chart-macd'), {
    type: 'bar',
    data: {
      labels: dates,
      datasets: [
        { type: 'bar', label: 'MACD柱', data: macdHists, backgroundColor: macdColors, borderWidth: 0 },
        { type: 'line', label: 'DIF', data: macdDifs, borderColor: c.white, borderWidth: 1, pointRadius: 0 },
        { type: 'line', label: 'DEA', data: macdDeas, borderColor: c.yellow, borderWidth: 1, pointRadius: 0 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { boxWidth: 12, padding: 8, font: { size: 10 } } } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });

  createChart('rsi', document.getElementById('chart-rsi'), {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        { label: 'RSI', data: rsis, borderColor: c.blue, borderWidth: 1.5, pointRadius: 0, yAxisID: 'y' },
        { label: 'KDJ_K', data: kdjKs, borderColor: c.white, borderWidth: 1, pointRadius: 0, yAxisID: 'y' },
        { label: 'KDJ_D', data: kdjDs, borderColor: c.yellow, borderWidth: 1, pointRadius: 0, yAxisID: 'y' },
        { label: 'KDJ_J', data: kdjJs, borderColor: c.purple, borderWidth: 1, pointRadius: 0, yAxisID: 'y' },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { labels: { boxWidth: 12, padding: 8, font: { size: 10 } } },
        annotation: false,
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } },
        y: { min: 0, max: 100, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });

  // 布林带图表
  createChart('boll', document.getElementById('chart-boll'), {
    type: 'line',
    data: {
      labels: dates,
      datasets: [
        { label: '上轨', data: bollUp, borderColor: c.red, borderWidth: 1, pointRadius: 0, borderDash: [5, 3] },
        { label: '中轨', data: bollMid, borderColor: c.yellow, borderWidth: 1, pointRadius: 0 },
        { label: '下轨', data: bollDn, borderColor: c.green, borderWidth: 1, pointRadius: 0, borderDash: [5, 3] },
        { label: '收盘价', data: closes, borderColor: c.white, borderWidth: 1.5, pointRadius: 0, tension: 0.1 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { labels: { boxWidth: 12, padding: 8, font: { size: 10 } } } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });

  // 成交量图表
  var volColors = [];
  for (var i = 0; i < closes.length; i++) {
    if (i === 0) {
      volColors.push(c.green);
    } else {
      volColors.push(closes[i] >= closes[i-1] ? c.green : c.red);
    }
  }
  // 计算相对成交量（归一化显示）
  var volumes = mt._raw_df.map(function(row) { return row.volume || 0; });
  var maxVol = Math.max(...volumes);
  var normVols = volumes.map(function(v) { return v / maxVol * 100; });

  createChart('volume', document.getElementById('chart-volume'), {
    type: 'bar',
    data: {
      labels: dates,
      datasets: [
        { label: '成交量', data: normVols, backgroundColor: volColors, borderWidth: 0 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { maxTicksLimit: 10, font: { size: 10 } } },
        y: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 }, display: false },
      },
      interaction: { intersect: false, mode: 'index' },
    },
  });
}

function renderIndicators(mt) {
  if (!mt) return;
  var trend = mt.trend || {};
  var mom = mt.momentum || {};
  var vol = mt.volume || {};
  var boll = trend.BOLL || {};
  var macd = trend.MACD || {};
  var kdj = mom.KDJ || {};
  var sr = mt.support_resistance || {};

  var left = document.getElementById('indicator-left');
  var right = document.getElementById('indicator-right');

  var leftItems = [
    ['点位', formatNum(mt.current_price)],
    ['涨跌', formatPct(mt.daily_stats ? mt.daily_stats.change_pct : null)],
    ['MA5', formatNum(trend.MA5)],
    ['MA10', formatNum(trend.MA10)],
    ['MA20', formatNum(trend.MA20)],
    ['MA60', formatNum(trend.MA60)],
    ['MACD', (macd.status || '--') + ' DIF:' + formatNum(macd.DIF, 4)],
    ['BOLL上', formatNum(boll.UP)],
    ['BOLL中', formatNum(boll.MID)],
    ['BOLL下', formatNum(boll.DN)],
    ['支撑位', formatNum(sr.support)],
    ['阻力位', formatNum(sr.resistance)],
  ];

  var rightItems = [
    ['RSI(14)', formatNum(mom.RSI, 1) + ' ' + (mom.RSI_zone || '')],
    ['KDJ', 'K:' + formatNum(kdj.K, 1) + ' D:' + formatNum(kdj.D, 1) + ' J:' + formatNum(kdj.J, 1)],
    ['WR', formatNum(mom.WR, 1)],
    ['CCI', formatNum(mom.CCI, 1)],
    ['MFI', formatNum(mom.MFI, 1)],
    ['ADX', formatNum(trend.ADX, 1) + ' ' + (trend.ADX_strength || '')],
    ['量比', formatNum(vol.volume_ratio, 2)],
    ['5日涨幅', formatPct(mom.change_5d)],
    ['10日涨幅', formatPct(mom.change_10d)],
    ['20日涨幅', formatPct(mom.change_20d)],
    ['OBV信号', vol.OBV_signal || '--'],
    ['波动率', mt.volatility ? mt.volatility.volatility_level : '--'],
  ];

  left.innerHTML = leftItems.map(function (item) {
    return '<div class="indicator-row"><span class="indicator-label">' + item[0] + '</span><span class="indicator-value">' + item[1] + '</span></div>';
  }).join('');
  right.innerHTML = rightItems.map(function (item) {
    return '<div class="indicator-row"><span class="indicator-label">' + item[0] + '</span><span class="indicator-value">' + item[1] + '</span></div>';
  }).join('');

  document.getElementById('tech-summary').textContent = mt.summary || '--';
}

function renderSectorRotation(sr) {
  if (!sr) return;
  var top = sr.top_sectors || [];
  var bottom = (sr.bottom_sectors || []).slice().reverse();
  var allData = top.concat(bottom);
  if (allData.length === 0) {
    document.getElementById('chart-sector').parentElement.innerHTML =
      '<div class="text-center text-muted" style="padding:80px 0">板块数据暂不可用<br><small>网络API限制</small></div>';
    return;
  }

  var labels = allData.map(function (s) { return s.name; });
  var scores = allData.map(function (s) { return s.composite_score != null ? s.composite_score * 100 : 0; });
  var bgColors = allData.map(function (s, i) {
    return i < (top.length) ? 'rgba(0,192,135,0.6)' : 'rgba(242,72,85,0.6)';
  });

  createChart('sector', document.getElementById('chart-sector'), {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{ label: '综合评分', data: scores, backgroundColor: bgColors, borderRadius: 4 }],
    },
    options: {
      indexAxis: 'y',
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { font: { size: 10 } } },
        y: { grid: { display: false }, ticks: { font: { size: 11 } } },
      },
    },
  });
}

function renderSentiment(sent) {
  if (!sent) return;
  var ss = sent.sentiment_score || {};
  var ls = sent.limit_stats || {};
  var hc = sent.hot_concepts || [];

  var html = '<div class="text-center mb-8">';
  html += '<div class="stat-value" style="color:' + getSentimentColor(ss.score || 50) + '">' + (ss.score || '--') + '</div>';
  html += '<div class="text-sm text-muted">情绪评分 / 100</div>';
  html += '<div class="badge badge-yellow mt-8">' + (ss.zone || '--') + '</div>';
  html += '</div>';

  html += '<div class="indicator-row"><span class="indicator-label">涨停家数</span><span class="indicator-value value-up">' + (ls.limit_up_count || 0) + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">跌停家数</span><span class="indicator-value value-down">' + (ls.limit_down_count || 0) + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">涨停比率</span><span class="indicator-value">' + formatPct((ls.limit_up_ratio || 0) * 100) + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">市场状态</span><span class="indicator-value">' + (ls.status || '--') + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">操作建议</span><span class="indicator-value">' + (ss.suggestion || '--') + '</span></div>';

  if (hc.length > 0) {
    html += '<div class="mt-8"><div class="text-sm text-muted mb-8">热点概念</div>';
    hc.slice(0, 8).forEach(function (c) {
      html += '<span class="badge badge-blue" style="margin:2px">' + c.name + '(' + c.limit_count + ')</span> ';
    });
    html += '</div>';
  }

  document.getElementById('sentiment-detail').innerHTML = html;
}

function getSentimentColor(score) {
  if (score >= 65) return '#00c087';
  if (score >= 40) return '#f5a623';
  return '#f24855';
}

function renderCapitalFlow(cf) {
  if (!cf) return;
  var nf = cf.north_flow || {};
  var indTop = cf.industry_flow_top || [];
  var indBot = cf.industry_flow_bottom || [];

  var html = '<div class="mb-8"><div class="text-sm font-weight:600 mb-8">北向资金</div>';
  html += '<div class="indicator-row"><span class="indicator-label">趋势</span><span class="indicator-value">' + (nf.trend || '--') + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">信号</span><span class="indicator-value">' + (nf.signal || '--') + '</span></div>';
  html += '<div class="indicator-row"><span class="indicator-label">20日累计</span><span class="indicator-value">' + formatNum(nf.recent_20_flow) + '亿</span></div>';
  html += '</div>';

  if (indTop.length > 0) {
    html += '<div class="mt-8"><div class="text-sm font-weight:600 mb-8">行业资金流入 TOP5</div>';
    indTop.slice(0, 5).forEach(function (item) {
      html += '<div class="indicator-row"><span class="indicator-label">' + item.name + '</span><span class="indicator-value value-up">' + formatNum(item.flow_yi) + '亿</span></div>';
    });
    html += '</div>';
  }

  if (indBot.length > 0) {
    html += '<div class="mt-8"><div class="text-sm font-weight:600 mb-8">行业资金流出 TOP5</div>';
    indBot.slice(0, 5).forEach(function (item) {
      html += '<div class="indicator-row"><span class="indicator-label">' + item.name + '</span><span class="indicator-value value-down">' + formatNum(item.flow_yi) + '亿</span></div>';
    });
    html += '</div>';
  }

  if (indTop.length === 0 && indBot.length === 0) {
    html += '<div class="text-center text-muted mt-12">资金流向数据暂不可用</div>';
  }

  document.getElementById('flow-detail').innerHTML = html;
}

function renderStocks(stocks) {
  var tbody = document.getElementById('stock-tbody');
  document.getElementById('stock-count').textContent = '共' + (stocks ? stocks.length : 0) + '只';

  if (!stocks || stocks.length === 0) {
    tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted" style="padding:40px">股票数据暂不可用<br><small>网络API限制</small></td></tr>';
    return;
  }

  tbody.innerHTML = stocks.map(function (s, i) {
    var chg = s.change_pct || 0;
    var chgClass = chg > 0 ? 'value-up' : (chg < 0 ? 'value-down' : '');
    return '<tr>' +
      '<td class="rank">' + (i + 1) + '</td>' +
      '<td>' + (s.code || '--') + '</td>' +
      '<td class="name">' + (s.name || '--') + '</td>' +
      '<td class="num">' + formatNum(s.price) + '</td>' +
      '<td class="num ' + chgClass + '">' + formatPct(chg) + '</td>' +
      '<td class="num">' + formatNum(s.volume_ratio) + '</td>' +
      '<td class="num">' + formatNum(s.score, 3) + '</td>' +
      '</tr>';
  }).join('');
}

function renderBacktest(bt) {
  if (!bt) return;
  document.getElementById('bt-total').textContent = formatPct(bt.total_return);
  document.getElementById('bt-annual').textContent = formatPct(bt.annual_return);
  document.getElementById('bt-sharpe').textContent = formatNum(bt.sharpe_ratio);
  document.getElementById('bt-dd').textContent = formatPct(bt.max_drawdown);
  document.getElementById('bt-wr').textContent = formatNum(bt.win_rate, 1) + '%';
  document.getElementById('bt-trades').textContent = bt.total_trades || '--';
  document.getElementById('bt-return').textContent = '总收益 ' + formatPct(bt.total_return);
}

function switchTab(name) {
  var tabs = document.querySelectorAll('.tab-item');
  tabs.forEach(function (t) { t.classList.remove('active'); });
  event.target.classList.add('active');

  document.getElementById('tab-sector').style.display = name === 'sector' ? 'block' : 'none';
  document.getElementById('tab-sentiment').style.display = name === 'sentiment' ? 'block' : 'none';
  document.getElementById('tab-flow').style.display = name === 'flow' ? 'block' : 'none';
  currentTab = name;
}

function refreshStocks() {
  var strategy = document.getElementById('strategy-select').value;
  showLoading('获取股票列表中...');
  
  fetch('/api/screen-stocks?strategy=' + strategy + '&top_n=20')
    .then(function (r) { return r.json(); })
    .then(function (stocks) {
      renderStocks(stocks);
      hideLoading();
    })
    .catch(function (err) {
      console.error(err);
      hideLoading();
    });
}

function runAnalysisWithStrategy(mode) {
  showLoading(mode === 'full' ? '全面分析中，请稍候...' : '快速分析中...');
  setStatus('loading', '分析中');

  fetch('/api/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode: mode }),
  })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      renderAll(data);
      refreshStocks();
      setStatus('done', '分析完成');
      hideLoading();
    })
    .catch(function (err) {
      console.error(err);
      setStatus('idle', '分析失败');
      hideLoading();
      alert('分析失败: ' + err.message);
    });
}

window.addEventListener('load', function () {
  document.getElementById('header-time').textContent = new Date().toLocaleString('zh-CN');
  
  // 启动时自动执行快速分析和刷新股票列表
  runAnalysisWithStrategy('quick');
  
  // 每秒更新时间
  setInterval(function() {
    document.getElementById('header-time').textContent = new Date().toLocaleString('zh-CN');
  }, 1000);
});
