"""An analyst workbook with source rows, formulas and an adjustable alert rule."""
from pathlib import Path

import xlsxwriter


def write_excel(result: dict, path: Path, weekly: dict | None = None):
    k = result['kpis']
    source = result['lane_monthly'].sort_values(['month', 'lane']).reset_index(drop=True)
    lanes = result['lanes'].head(20)
    states = result['states']
    monthly = result['monthly']

    with xlsxwriter.Workbook(str(path)) as workbook:
        workbook.set_properties({'title': 'Delivery performance | Analyst workbook'})
        navy = workbook.add_format({'bold': True, 'bg_color': '#193B53', 'font_color': '#FFFFFF', 'border': 0})
        title = workbook.add_format({'bold': True, 'font_size': 17, 'font_color': '#193B53'})
        money = workbook.add_format({'num_format': '"R$ "#,##0.00'})
        integer = workbook.add_format({'num_format': '#,##0'})
        percent = workbook.add_format({'num_format': '0.0%'})
        one_dp = workbook.add_format({'num_format': '#,##0.0'})
        pale = workbook.add_format({'bg_color': '#E8F4F2', 'num_format': '0.0'})
        note = workbook.add_format({'font_color': '#5D7181', 'italic': True})
        source_end = len(source) + 1
        raw_range = lambda col: f"'Lane data'!${col}$2:${col}${source_end}"

        overview = workbook.add_worksheet('Overview')
        overview.hide_gridlines(2)
        overview.set_column('A:A', 33)
        overview.set_column('B:B', 24)
        overview.write('A1', 'DELIVERY PERFORMANCE', title)
        overview.write('A2', 'Historical Olist extract | business decisions, not a live feed', note)
        overview.write_row('A4', ['KPI', 'Value'], navy)
        values = [
            ('Total orders in extract', k['total_orders']),
            ('Assessed deliveries', k['assessed_orders']),
            ('Late orders', k['late_orders']),
            ('Late-delivery rate', k['late_rate']),
            ('All merchandise GMV', k['gmv_brl']),
            ('GMV on late orders', k['late_gmv_brl']),
            ('Unassessed rows in extract', k['unassessed_in_extract']),
        ]
        for row, (label, value) in enumerate(values, 4):
            overview.write(row, 0, label)
            if label == 'Late-delivery rate':
                overview.write_formula(row, 1, '=IFERROR(B7/B6,0)', percent, value)
            elif 'GMV' in label:
                overview.write_number(row, 1, value, money)
            else:
                overview.write_number(row, 1, value, integer)
        overview.write('A14', 'Late = delivery date after promised calendar date.', note)
        overview.write('A15', 'Late merchandise GMV is not confirmed revenue loss.', note)

        raw = workbook.add_worksheet('Lane data')
        raw.freeze_panes(1, 0)
        raw.set_column('A:B', 17)
        raw.set_column('C:E', 16)
        raw.write_row(0, 0, ['Month', 'Lane', 'Assessed', 'Late', 'Late GMV (BRL)'], navy)
        for i, record in enumerate(source.itertuples(index=False), 1):
            raw.write(i, 0, record.month)
            raw.write(i, 1, record.lane)
            raw.write_number(i, 2, int(record.orders))
            raw.write_number(i, 3, int(record.late_orders))
            raw.write_number(i, 4, float(record.late_gmv_brl), money)
        raw.add_table(0, 0, len(source), 4, {'name': 'LaneMonthData', 'style': 'Table Style Medium 2',
                                           'columns': [{'header': x} for x in ['Month','Lane','Assessed','Late','Late GMV (BRL)']]})

        score = workbook.add_worksheet('Lane scorecard')
        score.hide_gridlines(2)
        score.freeze_panes(7, 1)
        score.set_column('A:A', 38)
        score.set_column('B:I', 19)
        score.write('A1', 'LANE REVIEW SCORECARD', title)
        score.write('A2', 'Alert multiplier (editable)')
        score.write_number('B2', 2.0, pale)
        score.write('A3', 'Same-state historical baseline')
        score.write_number('B3', result['baseline'], percent)
        score.write('A4', 'A lane is flagged if its late rate exceeds the benchmark x multiplier and it has 50+ orders.', note)
        score.write_row('A7', ['Lane', 'Assessed', 'Late', 'Late GMV', 'Late rate',
                              'Benchmark late', 'Excess', 'Flag'], navy)
        for i, rec in enumerate(lanes.itertuples(index=False), 8):
            score.write(f'A{i}', rec.lane)
            score.write_formula(f'B{i}', f'=SUMIFS({raw_range("C")},{raw_range("B")},A{i})', integer, int(rec.orders))
            score.write_formula(f'C{i}', f'=SUMIFS({raw_range("D")},{raw_range("B")},A{i})', integer, int(rec.late_orders))
            score.write_formula(f'D{i}', f'=SUMIFS({raw_range("E")},{raw_range("B")},A{i})', money, float(rec.late_gmv_brl))
            score.write_formula(f'E{i}', f'=IFERROR(C{i}/B{i},0)', percent, float(rec.late_rate))
            score.write_formula(f'F{i}', f'=B{i}*$B$3', one_dp, float(rec.benchmark_late))
            score.write_formula(f'G{i}', f'=C{i}-F{i}', one_dp, float(rec.excess_late))
            flag = 'REVIEW' if int(rec.orders) >= 50 and float(rec.late_rate) >= 2 * result['baseline'] else 'Monitor'
            score.write_formula(f'H{i}', f'=IF(AND(B{i}>=50,E{i}>=$B$2*$B$3),"REVIEW","Monitor")', None, flag)
        score.autofilter(6, 0, 6 + len(lanes), 7)
        score.conditional_format(7, 7, 6 + len(lanes), 7,
                                 {'type': 'text', 'criteria': 'containing', 'value': 'REVIEW',
                                  'format': workbook.add_format({'bg_color': '#FDE9DB', 'font_color': '#A32B19', 'bold': True})})

        matrix = workbook.add_worksheet('Month x lane')
        matrix.freeze_panes(1, 1)
        matrix.set_column('A:A', 14)
        matrix.set_column('B:F', 18)
        top5 = lanes.head(5).lane.tolist()
        matrix.write_row(0, 0, ['Month', *top5], navy)
        for row, month in enumerate(sorted(source.month.unique()), 2):
            matrix.write(f'A{row}', month)
            for column, name in enumerate(top5, 1):
                letter = xlsxwriter.utility.xl_col_to_name(column)
                numerator = f'SUMIFS({raw_range("D")},{raw_range("A")},$A{row},{raw_range("B")},{letter}$1)'
                denominator = f'SUMIFS({raw_range("C")},{raw_range("A")},$A{row},{raw_range("B")},{letter}$1)'
                mask = source[(source.month == month) & (source.lane == name)]
                cached = float(mask.late_orders.sum() / mask.orders.sum()) if len(mask) else ''
                matrix.write_formula(
                    row - 1, column,
                    f'=IF({denominator}=0,"",{numerator}/{denominator})',
                    percent, cached,
                )
        matrix.conditional_format(1, 1, len(source.month.unique()), 5,
                                  {'type': '3_color_scale', 'min_color': '#E6F5F1',
                                   'mid_color': '#F8EBC2', 'max_color': '#F2C2BC'})

        state = workbook.add_worksheet('States')
        state.freeze_panes(1, 0)
        state.set_column('A:A', 15)
        state.set_column('B:E', 17)
        state.write_row(0, 0, ['State', 'Assessed', 'Late', 'Late rate', 'Share of all late'], navy)
        for i, rec in enumerate(states.itertuples(index=False), 1):
            state.write(i, 0, rec.customer_state)
            state.write_number(i, 1, int(rec.orders))
            state.write_number(i, 2, int(rec.late_orders))
            state.write_formula(i, 3, f'=IFERROR(C{i+1}/B{i+1},0)', percent, rec.late_rate)
            state.write_formula(i, 4, f'=IFERROR(C{i+1}/Overview!$B$7,0)', percent, rec.share_of_all_late)

        trend = workbook.add_worksheet('Monthly trend')
        trend.set_column('A:A', 14)
        trend.set_column('B:D', 19)
        trend.write_row(0, 0, ['Month', 'Assessed', 'Late', 'Late rate'], navy)
        for i, rec in enumerate(monthly.itertuples(index=False), 1):
            trend.write(i, 0, rec.month)
            trend.write_number(i, 1, int(rec.orders))
            trend.write_number(i, 2, int(rec.late_orders))
            trend.write_formula(i, 3, f'=IFERROR(C{i+1}/B{i+1},0)', percent, rec.late_rate)
        chart = workbook.add_chart({'type': 'line'})
        chart.add_series({'name': 'Late-delivery rate',
                          'categories': ['Monthly trend', 1, 0, len(monthly), 0],
                          'values': ['Monthly trend', 1, 3, len(monthly), 3]})
        chart.set_title({'name': 'Late rate by purchase month'})
        chart.set_y_axis({'num_format': '0%'})
        chart.set_legend({'none': True})
        trend.insert_chart('F2', chart)

        if weekly is not None:
            week_sheet = workbook.add_worksheet('This week')
            week_sheet.hide_gridlines(2)
            week_sheet.set_column('A:A', 24)
            week_sheet.set_column('B:E', 18)
            week_sheet.write('A1', 'COMPLETED DELIVERIES THIS WEEK', title)
            week_sheet.write('A2', 'Delivery dates, not purchase dates', note)
            week_sheet.write('A4', 'Week beginning')
            week_sheet.write('B4', weekly['week_start'])
            week_sheet.write('A5', 'Completed deliveries (one seller)')
            week_sheet.write_number('B5', weekly['orders'], integer)
            week_sheet.write('A6', 'Late deliveries')
            week_sheet.write_number('B6', weekly['late_orders'], integer)
            week_sheet.write('A7', 'Late rate')
            week_sheet.write_formula('B7', '=IFERROR(B6/B5,"")', percent,
                                     weekly['late_rate'] if weekly['late_rate'] is not None else '')
            week_sheet.write('A8', 'Earlier-history same-state rate')
            if weekly['baseline'] is not None:
                week_sheet.write_number('B8', weekly['baseline'], percent)
            week_sheet.write_row('A10', ['Lane', 'Completed', 'Late', 'Late rate', 'Prior-rate multiple'], navy)
            for i, row in enumerate(weekly['by_lane'].head(20).itertuples(index=False), 10):
                week_sheet.write(i, 0, row.lane)
                week_sheet.write_number(i, 1, int(row.orders), integer)
                week_sheet.write_number(i, 2, int(row.late_orders), integer)
                week_sheet.write_formula(i, 3, f'=IF(B{i+1}=0,"",C{i+1}/B{i+1})', percent, row.late_rate)
                if weekly['baseline']:
                    week_sheet.write_number(i, 4, row.multiple, one_dp)
            week_sheet.autofilter(9, 0, 9 + min(20, len(weekly['by_lane'])), 4)
