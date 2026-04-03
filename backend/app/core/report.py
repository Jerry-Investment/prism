"""
PRISM Report Generator — produces HTML performance reports from analytics data.
"""
from __future__ import annotations

from typing import Any


def _fmt_pct(v: float | None, digits: int = 2) -> str:
    if v is None:
        return "N/A"
    return f"{v * 100:.{digits}f}%"


def _fmt_float(v: float | None, digits: int = 4) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{digits}f}"


def _color_cell(value: float, invert: bool = False) -> str:
    """Return CSS color class for a monthly-return cell."""
    if value > 0.02:
        return "#1a7a1a" if not invert else "#7a1a1a"
    elif value > 0:
        return "#4caf50" if not invert else "#f44336"
    elif value < -0.02:
        return "#7a1a1a" if not invert else "#1a7a1a"
    elif value < 0:
        return "#f44336" if not invert else "#4caf50"
    return "#555"


def _monthly_heatmap(monthly_returns: dict[str, float]) -> str:
    if not monthly_returns:
        return "<p>월별 수익률 데이터 없음</p>"

    months = ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
    month_labels = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    years = sorted({k[:4] for k in monthly_returns})

    header = "<tr><th>Year</th>" + "".join(f"<th>{m}</th>" for m in month_labels) + "<th>Annual</th></tr>"
    rows = [header]

    for year in years:
        yearly_product = 1.0
        cells = [f"<td><strong>{year}</strong></td>"]
        for mo in months:
            key = f"{year}-{mo}"
            val = monthly_returns.get(key)
            if val is not None:
                color = _color_cell(val)
                cells.append(
                    f'<td style="background:{color};color:#fff;padding:4px 6px;'
                    f'border-radius:3px;text-align:center">{_fmt_pct(val, 1)}</td>'
                )
                yearly_product *= 1 + val
            else:
                cells.append('<td style="color:#888">—</td>')

        annual = yearly_product - 1.0
        color = _color_cell(annual)
        cells.append(
            f'<td style="background:{color};color:#fff;padding:4px 6px;'
            f'border-radius:3px;text-align:center;font-weight:bold">{_fmt_pct(annual, 1)}</td>'
        )
        rows.append("<tr>" + "".join(cells) + "</tr>")

    return (
        '<table style="border-collapse:collapse;width:100%;font-size:13px">'
        + "".join(rows)
        + "</table>"
    )


def _equity_sparkline(equity_curve: list[dict]) -> str:
    """Generate a simple SVG sparkline from equity curve."""
    if len(equity_curve) < 2:
        return ""
    equities = [e["equity"] for e in equity_curve]
    n = len(equities)
    w, h = 600, 120
    min_e, max_e = min(equities), max(equities)
    span = max_e - min_e if max_e != min_e else 1

    points = []
    for i, e in enumerate(equities):
        x = i / (n - 1) * w
        y = h - (e - min_e) / span * h
        points.append(f"{x:.1f},{y:.1f}")

    polyline = " ".join(points)
    # Color: green if final > initial, red otherwise
    color = "#4caf50" if equities[-1] >= equities[0] else "#f44336"

    return (
        f'<svg width="{w}" height="{h}" style="display:block;margin:12px 0">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"/>'
        f"</svg>"
    )


def generate_html_report(
    task_id: str,
    strategy_name: str,
    symbol: str,
    initial_capital: float,
    final_equity: float,
    total_trades: int,
    analytics: dict[str, Any],
    equity_curve: list[dict],
) -> str:
    """Generate a complete HTML performance report."""
    perf = analytics["performance"]
    risk = analytics["risk"]
    monthly = analytics["monthly_returns"]
    yearly = analytics["yearly_returns"]

    total_return_pct = _fmt_pct(perf["total_return"])
    total_return_color = "#4caf50" if perf["total_return"] >= 0 else "#f44336"

    sparkline = _equity_sparkline(equity_curve)
    heatmap = _monthly_heatmap(monthly)

    yearly_rows = ""
    for yr, ret in sorted(yearly.items()):
        color = _color_cell(ret)
        yearly_rows += (
            f"<tr><td>{yr}</td>"
            f'<td style="color:{color};font-weight:bold">{_fmt_pct(ret)}</td></tr>'
        )

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>PRISM 백테스트 리포트 — {strategy_name}</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          background: #0f0f0f; color: #e0e0e0; margin: 0; padding: 24px; }}
  h1 {{ color: #fff; font-size: 22px; margin-bottom: 4px; }}
  h2 {{ color: #aaa; font-size: 15px; border-bottom: 1px solid #333;
        padding-bottom: 6px; margin-top: 28px; }}
  .meta {{ color: #888; font-size: 13px; margin-bottom: 20px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }}
  .card {{ background: #1c1c1c; border-radius: 8px; padding: 14px 16px; }}
  .card-label {{ font-size: 11px; color: #888; text-transform: uppercase; letter-spacing: .5px; }}
  .card-value {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  th {{ background: #222; padding: 8px 10px; text-align: left; color: #aaa;
        font-weight: 500; border-bottom: 1px solid #333; }}
  td {{ padding: 7px 10px; border-bottom: 1px solid #1e1e1e; }}
  .positive {{ color: #4caf50; }}
  .negative {{ color: #f44336; }}
</style>
</head>
<body>
<h1>PRISM 백테스트 리포트</h1>
<div class="meta">
  전략: <strong>{strategy_name}</strong> &nbsp;|&nbsp;
  종목: <strong>{symbol}</strong> &nbsp;|&nbsp;
  Task: <code>{task_id[:8]}…</code>
</div>

<h2>요약</h2>
<div class="grid">
  <div class="card">
    <div class="card-label">총 수익률</div>
    <div class="card-value" style="color:{total_return_color}">{total_return_pct}</div>
  </div>
  <div class="card">
    <div class="card-label">연환산 수익률</div>
    <div class="card-value">{_fmt_pct(perf['annualised_return'])}</div>
  </div>
  <div class="card">
    <div class="card-label">샤프 비율</div>
    <div class="card-value">{_fmt_float(perf['sharpe_ratio'], 2)}</div>
  </div>
  <div class="card">
    <div class="card-label">소르티노 비율</div>
    <div class="card-value">{_fmt_float(perf['sortino_ratio'], 2)}</div>
  </div>
  <div class="card">
    <div class="card-label">최대 낙폭 (MDD)</div>
    <div class="card-value" style="color:#f44336">{_fmt_pct(perf['max_drawdown'])}</div>
  </div>
  <div class="card">
    <div class="card-label">칼마 비율</div>
    <div class="card-value">{_fmt_float(perf['calmar_ratio'], 2)}</div>
  </div>
  <div class="card">
    <div class="card-label">승률</div>
    <div class="card-value">{_fmt_pct(perf['win_rate'])}</div>
  </div>
  <div class="card">
    <div class="card-label">Profit Factor</div>
    <div class="card-value">{_fmt_float(perf['profit_factor'], 2)}</div>
  </div>
  <div class="card">
    <div class="card-label">초기 자본</div>
    <div class="card-value" style="font-size:16px">₩{initial_capital:,.0f}</div>
  </div>
  <div class="card">
    <div class="card-label">최종 자산</div>
    <div class="card-value" style="font-size:16px">₩{final_equity:,.0f}</div>
  </div>
  <div class="card">
    <div class="card-label">총 거래 수</div>
    <div class="card-value">{total_trades}</div>
  </div>
</div>

<h2>자산 곡선</h2>
{sparkline}

<h2>성과 지표</h2>
<table>
  <tr><th>지표</th><th>값</th></tr>
  <tr><td>연환산 변동성</td><td>{_fmt_pct(perf['annualised_volatility'])}</td></tr>
  <tr><td>최대 낙폭 지속기간</td><td>{perf['max_drawdown_duration']} 기간</td></tr>
</table>

<h2>리스크 지표</h2>
<table>
  <tr><th>지표</th><th>값</th></tr>
  <tr><td>VaR 95%</td><td class="negative">{_fmt_pct(risk['var_95'])}</td></tr>
  <tr><td>VaR 99%</td><td class="negative">{_fmt_pct(risk['var_99'])}</td></tr>
  <tr><td>CVaR 95% (Expected Shortfall)</td><td class="negative">{_fmt_pct(risk['cvar_95'])}</td></tr>
  <tr><td>CVaR 99%</td><td class="negative">{_fmt_pct(risk['cvar_99'])}</td></tr>
  <tr><td>일별 P&L 평균</td><td>{_fmt_pct(risk['daily_pnl_mean'])}</td></tr>
  <tr><td>일별 P&L 표준편차</td><td>{_fmt_pct(risk['daily_pnl_std'])}</td></tr>
  <tr><td>P&L 왜도 (Skewness)</td><td>{_fmt_float(risk['daily_pnl_skew'], 3)}</td></tr>
  <tr><td>P&L 첨도 (Kurtosis)</td><td>{_fmt_float(risk['daily_pnl_kurt'], 3)}</td></tr>
  <tr><td>최대 연속 손실 횟수</td><td>{risk['max_consecutive_losses']}</td></tr>
  <tr><td>최대 연속 손실 합계</td><td class="negative">{_fmt_pct(risk['max_consecutive_loss_amount'])}</td></tr>
</table>

<h2>월별 수익률 히트맵</h2>
{heatmap}

<h2>연도별 수익률</h2>
<table>
  <tr><th>연도</th><th>수익률</th></tr>
  {yearly_rows if yearly_rows else '<tr><td colspan="2" style="color:#888">데이터 없음</td></tr>'}
</table>

<p style="color:#555;font-size:11px;margin-top:32px">
  Generated by PRISM Analytics Engine &nbsp;·&nbsp;
  Powered by Paperclip AI Trading Platform
</p>
</body>
</html>"""
