"""Offline preview helper for Weekly Picks DataTable.

This script imports the weekly_picks module, loads the latest picks CSV,
prepares the display DataFrame, constructs the style_data_conditional list,
and prints a small human-readable preview. Run locally inside the repo with
python Dash/preview_weekly_table.py
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tabs import weekly_picks


def main():
    df, path_or_err = weekly_picks._load_weekly_df()
    if df is None:
        print('No weekly picks found:', path_or_err)
        return
    disp = weekly_picks._prepare_weekly_display_df(df)
    try:
        disp = weekly_picks._attempt_enriched_backfill(disp, picks_path=path_or_err)
    except Exception as e:
        print('Backfill failed:', e)
    # Build columns and style rules similar to the module
    records = disp.fillna('').to_dict(orient='records')
    cols = []
    for c in disp.columns:
        col = {'name': c, 'id': c}
        if c in ('price_live', 'week_start'):
            col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
        elif c in ('daily_change', 'overall_change', 'profit_loss'):
            if c == 'profit_loss':
                col.update({'type': 'numeric', 'format': {'specifier': ',.2f'}})
            else:
                col.update({'type': 'numeric', 'format': {'specifier': '.4f'}})
        cols.append(col)

    style_data_conditional = []
    if 'price_live' in disp.columns:
        style_data_conditional.append({'if': {'column_id': 'price_live'}, 'textAlign': 'right'})
    for c in ('profit_loss', 'daily_change', 'overall_change'):
        if c in disp.columns:
            style_data_conditional.append({'if': {'column_id': c}, 'textAlign': 'right'})
            style_data_conditional.append({'if': {'filter_query': f'{{{c}}} > 0', 'column_id': c}, 'color': '#10B981'})
            style_data_conditional.append({'if': {'filter_query': f'{{{c}}} < 0', 'column_id': c}, 'color': '#EF4444'})
    if 'overall_change' in disp.columns and 'price_live' in disp.columns:
        style_data_conditional.append({'if': {'filter_query': '{overall_change} > 0', 'column_id': 'price_live'}, 'color': '#10B981', 'fontWeight': '700'})
        style_data_conditional.append({'if': {'filter_query': '{overall_change} < 0', 'column_id': 'price_live'}, 'color': '#EF4444', 'fontWeight': '700'})

    print('Picks path:', path_or_err)
    print('Columns:', [c for c in disp.columns])
    print('Number of rows:', len(disp))
    print('\nSample rows:')
    for r in records[:10]:
        print(json.dumps(r, default=str))
    print('\nStyle rules:')
    print(json.dumps(style_data_conditional, indent=2))


if __name__ == '__main__':
    main()
