#!/usr/bin/env python3
"""Verify Phase 14 database writes"""

import psycopg2
import os

# Connect to PostgreSQL
conn = psycopg2.connect(
    host=os.getenv('POSTGRES_HOST', 'localhost'),
    port=int(os.getenv('POSTGRES_PORT', 5432)),
    database=os.getenv('POSTGRES_DB', 'financial_dashboard'),
    user=os.getenv('POSTGRES_USER', 'dashboard_user'),
    password=os.getenv('POSTGRES_PASSWORD', 'newpassword')
)

cur = conn.cursor()

# Query weekly picks
cur.execute('''
    SELECT ticker, rank, combined_score, 
           LEFT(rationale, 80) AS rationale_preview,
           jsonb_array_length(chart_array) AS chart_points
    FROM weekly_picks_production 
    ORDER BY rank
''')

print('=' * 100)
print('WEEKLY PICKS PRODUCTION TABLE - VERIFICATION')
print('=' * 100)
print('{:<6} {:<8} {:<8} {:<12} {:<50}'.format('Rank', 'Ticker', 'Score', 'Chart Pts', 'Rationale Preview'))
print('-' * 100)

for row in cur.fetchall():
    ticker, rank, score, rationale, chart_pts = row
    print('{:<6} {:<8} {:<8.2f} {:<12} {:<50}'.format(rank, ticker, score, chart_pts, rationale))

print('=' * 100)

# Query telemetry
cur.execute('''
    SELECT run_id, status, stocks_processed, picks_generated, 
           EXTRACT(EPOCH FROM (execution_end - execution_start)) AS duration_seconds
    FROM generator_telemetry 
    ORDER BY execution_start DESC 
    LIMIT 5
''')

print()
print('GENERATOR TELEMETRY - LAST 5 RUNS')
print('=' * 100)
print('{:<12} {:<10} {:<10} {:<10} {:<15}'.format('Run ID', 'Status', 'Stocks', 'Picks', 'Duration (s)'))
print('-' * 100)

for row in cur.fetchall():
    run_id, status, stocks, picks, duration = row
    dur_val = duration if duration is not None else 0.0
    print('{:<12} {:<10} {:<10} {:<10} {:<15.2f}'.format(run_id, status, stocks or 0, picks or 0, dur_val))

print('=' * 100)

cur.close()
conn.close()
print()
print('✅ Database verification complete!')
