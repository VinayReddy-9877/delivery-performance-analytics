"""One-page decision memo for an operations manager."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, Image, KeepTogether)


def write_memo(result: dict, file: Path):
    font = 'Helvetica'
    regular = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')
    if regular.exists():
        pdfmetrics.registerFont(TTFont('DejaVu', str(regular)))
        font = 'DejaVu'
    style = ParagraphStyle('body', fontName=font, fontSize=9, leading=13, spaceAfter=6)
    heading = ParagraphStyle('heading', parent=style, fontSize=16, leading=20,
                             textColor=colors.HexColor('#183b56'), spaceAfter=12)
    section = ParagraphStyle('section', parent=style, fontSize=11, leading=14,
                             textColor=colors.HexColor('#183b56'), spaceBefore=9, spaceAfter=5)
    k = result['kpis']
    lane = result['priority']
    rj = result['states'].set_index('customer_state').loc['RJ']
    top5 = sum(result['lanes'].head(5).excess_late.clip(lower=0))
    cross_compare = result['comparison_rates']['other_cross_state_excluding_sp_rj']
    cross_excess = lane['late_orders'] - lane['orders'] * cross_compare
    content = [Paragraph('Delivery Performance | Operations Brief', heading),
               Paragraph('<b>Decision:</b> prioritize weekly monitoring of the SP to RJ shipping lane.', style),
               Spacer(1, 8)]
    rows = [
        ['Metric', 'Observed result'],
        ['Delivered late', f"{k['late_orders']:,} of {k['assessed_orders']:,} ({k['late_rate']:.1%})"],
        ['Late-order merchandise', f"R$ {k['late_gmv_brl']:,.0f}; not confirmed loss"],
        ['SP to RJ', f"{int(lane['late_orders']):,} / {int(lane['orders']):,} ({lane['late_rate']:.1%})"],
        ['Benchmark difference', f"{lane['excess_late']:,.0f} more late than {result['baseline']:.1%} benchmark"],
        ['RJ customer state', f"{int(rj.late_orders):,} late ({rj.share_of_all_late:.1%} of all late)"],
    ]
    grid = Table(rows, colWidths=[190, 310], hAlign='LEFT')
    grid.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#183b56')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f3f7fa')]),
        ('FONTNAME', (0, 0), (-1, -1), font),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, -1), (-1, -1), .4, colors.HexColor('#cedce6')),
    ]))
    content.append(grid)
    content += [
        Paragraph('What the data suggests', section),
        Paragraph(f"SP to RJ has the largest volume-adjusted late-delivery gap. Against other cross-state lanes ({cross_compare:.1%} late), its benchmark gap remains about {cross_excess:,.0f} orders. The top five lanes total roughly {top5:,.0f} excess deliveries at the same-state benchmark. Spikes were concentrated in Nov 2017 and Feb-Mar 2018.", style),
        Paragraph('What operations should do', section),
        Paragraph('<b>Logistics:</b> trigger a weekly review when a lane with at least 50 orders crosses 2x the prior-history same-state rate; inspect carrier and seller records for those weeks.', style),
        Paragraph('<b>Analytics:</b> track alert frequency and late-order counts after any process change; compare with similar lanes before claiming effectiveness.', style),
        Paragraph('Caveats', section),
        Paragraph(f"This is a prepared, delivered-heavy Olist extract, not the complete order universe; {k['unassessed_in_extract']} rows here have no observed delivery. Multi-seller orders are excluded from lane analysis. A same-state benchmark is not a causal forecast, and late-order merchandise is not revenue lost.", style),
    ]
    pdf = SimpleDocTemplate(str(file), pagesize=(595.3, 841.9), leftMargin=47,
                            rightMargin=47, topMargin=47, bottomMargin=45)
    pdf.build(content)
