"""Plain HTML briefing that managers can open without Python or a dashboard server."""
from __future__ import annotations

from html import escape
from pathlib import Path


def build_html(result: dict, output: Path, week: str | None, alerts, weekly: dict | None = None):
    k = result['kpis']
    focus = result['priority']
    rj = result['states'].set_index('customer_state').loc['RJ']
    peak = result['lane_monthly'].query("lane == 'SP → RJ' and month == '2018-03'")
    march = float(peak.late_rate.iloc[0]) if not peak.empty else 0
    top_five = sum(result['lanes'].head(5).excess_late.clip(lower=0))
    cross_rate = result['comparison_rates']['other_cross_state_excluding_sp_rj']
    cross_excess = focus['late_orders'] - focus['orders'] * cross_rate
    focus_name = escape(focus['lane'])
    title = 'Historical week of ' + escape(week) if week else 'Historical delivery performance'

    table_rows = ''.join(
        '<tr><td>{}</td><td>{:,}</td><td>{:,}</td><td>{:.1%}</td><td>{:,.0f}</td></tr>'.format(
            escape(str(row.lane)), int(row.orders), int(row.late_orders),
            row.late_rate, row.excess_late,
        ) for row in result['lanes'].head(8).itertuples(index=False)
    )
    doc = '''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Delivery Performance | Olist</title><style>
body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;max-width:1050px;margin:36px auto;padding:0 24px;color:#1b3042;line-height:1.5;background:#f9fafc}
h1{font-size:33px;margin-bottom:4px}h2{margin-top:35px;font-size:22px}small,.muted{color:#637789}
.lead{font-size:19px;max-width:850px}.cards{display:flex;flex-wrap:wrap;gap:14px;margin:24px 0}
.card{background:#fff;padding:17px 20px;border:1px solid #dde5eb;border-radius:12px;min-width:190px;flex:1}
.card strong{display:block;font-size:27px}.card span{font-size:13px;color:#617489}
section{background:#fff;border:1px solid #e1e8ee;border-radius:12px;padding:19px 22px;margin:20px 0}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:10px;border-bottom:1px solid #e8edf1}th{background:#f2f5f7}
img{max-width:100%;height:auto;margin:10px 0 16px}ul{padding-left:20px}.note{font-size:13px;color:#687789}
</style></head><body>'''
    doc += f'<small>{title}</small><h1>Delivery Performance Analytics</h1>'
    doc += '<p class="lead">Which shipping lanes need attention first? Rank delays by affected orders, not only by the highest late rate.</p>'
    doc += '<div class="cards">'
    if weekly is None:
        cards = [
            ('Historical assessed deliveries', f'{k["assessed_orders"]:,}'),
            ('Historical late rate', f'{k["late_rate"]:.1%}'),
            ('Late-order merchandise', f'R$ {k["late_gmv_brl"]:,.0f}'),
        ]
    else:
        cards = [
            ('Completed this week', f'{weekly["orders"]:,}'),
            ('Late deliveries this week', f'{weekly["late_orders"]:,}'),
            ('Late rate this week', f'{weekly["late_rate"]:.1%}'
             if weekly['late_rate'] is not None else '—'),
            ('Flagged lanes', str(len(alerts))),
        ]
    for label, value in cards:
        doc += f'<div class="card"><span>{label}</span><strong>{value}</strong></div>'
    doc += '</div>'
    if weekly is not None:
        current_rate = (f"{weekly['late_rate']:.1%}" if weekly['late_rate'] is not None
                        else 'not available')
        earlier_rate = (f"{weekly['baseline']:.1%}" if weekly['baseline'] is not None
                        else 'insufficient history')
        week_rows = ''.join(
            f'<tr><td>{escape(str(row.lane))}</td><td>{int(row.orders):,}</td>'
            f'<td>{int(row.late_orders):,}</td><td>{row.late_rate:.1%}</td></tr>'
            for row in weekly['by_lane'].head(8).itertuples(index=False)
        )
        flagged = ', '.join(escape(str(x)) for x in alerts.lane.tolist()) if len(alerts) else 'None'
        doc += f'''<section><h2>This week: completed deliveries</h2>
<p><b>{escape(weekly['week_start'])}</b> through the following six days; outcomes were
known only after deliveries were completed. Of <b>{weekly['orders']:,}</b> completed
single-seller deliveries, <b>{weekly['late_orders']:,}</b> were late
(<b>{current_rate}</b>). The benchmark from <i>earlier completed</i> same-state
deliveries was <b>{earlier_rate}</b>.</p>
<p><b>Flagged lanes ({len(alerts)}):</b> {flagged}.
An alert is a retrospective detection at the end of the delivery week,
not an advance prediction on purchase day.</p>
<img src="figures/sp_rj_delivery_weeks.png"
alt="SP to RJ rate by completed delivery week">
<table><thead><tr><th>Lane</th><th>Completed</th><th>Late</th><th>Rate</th>
</tr></thead><tbody>{week_rows}</tbody></table></section>'''
    if weekly is not None:
        doc += f'<section><h2>Historical context (full extract)</h2><p>Across '
        doc += (f'<b>{k["assessed_orders"]:,}</b> assessed deliveries, '
                f'<b>{k["late_orders"]:,}</b> were late '
                f'(<b>{k["late_rate"]:.1%}</b>), representing '
                f'<b>R$ {k["late_gmv_brl"]:,.0f}</b> in merchandise value '
                f'associated with late deliveries. This full-history view uses '
                f'the complete historical extract and is not restricted to '
                f'what was known at this replay week.</p></section>')
    doc += f'''<section><h2>Recommendation: monitor {focus_name} first</h2>
<p><b>{int(focus['late_orders']):,} of {int(focus['orders']):,}</b> assessed orders were late
({focus['late_rate']:.1%}), versus {result['baseline']:.1%} for same-state deliveries.
This is roughly <b>{focus['excess_late']:,.0f} excess late orders</b> at that benchmark. Against other cross-state lanes ({cross_rate:.1%}), the gap is about <b>{cross_excess:,.0f}</b> orders.
The lane accounts for <b>{focus['share_of_all_late']:.1%}</b> of all late orders and
<b>R$ {focus['late_gmv_brl']:,.0f}</b> in late-order merchandise value.</p>
<p>Late performance reached <b>{march:.0%} in March 2018</b>, then fell. Monitor the lane weekly;
review carrier and promise-setting records when it crosses the alert threshold.</p>
<img alt="Late rate by month for SP to RJ" src="figures/sp_rj_by_month.png"></section>'''
    doc += f'''<section><h2>Where the exposure is concentrated</h2>
<p>RJ customers account for <b>{int(rj.late_orders):,}</b> late orders ({rj.share_of_all_late:.1%}
of all late deliveries). The top five lanes have roughly <b>{top_five:,.0f}</b> excess
late orders compared with the same-state benchmark.</p>
<img alt="Top lanes ranked by benchmark excess" src="figures/lane_excess.png">
<table><thead><tr><th>Lane</th><th>Assessed</th><th>Late</th><th>Late rate</th><th>Excess vs benchmark</th></tr></thead><tbody>{table_rows}</tbody></table></section>'''
    doc += '''<section><h2>Recommended next actions</h2><ul>
<li><b>Logistics:</b> investigate SP to RJ in the spike months; compare transit and seller handoff once tracking data is available.</li>
<li><b>Operations analyst:</b> review completed-delivery weekly alerts for lanes with at least 50 assessed orders and 2× the prior-history same-state rate.</li>
<li><b>Customer operations:</b> measure review scores and undelivered orders after obtaining the full original order and reviews tables.</li></ul>
<img alt="Overall late rate by month" src="figures/all_months.png"></section>'''
    doc += f'''<p class="note">Source: prepared Olist extract (2016–2018). {k['unassessed_in_extract']:,} orders in this extract lack an assessable delivered date.
The prepared extract is not the full Olist order universe. Multi-seller orders are excluded from lane analysis.
Excess orders are a benchmark comparison, not a causal estimate or committed savings.
Late-order GMV is merchandise associated with delay, not revenue lost. Historical replay is not live incoming data.</p>'''
    doc += '</body></html>'
    output.write_text(doc, encoding='utf-8')
