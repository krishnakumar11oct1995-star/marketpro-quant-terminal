#!/usr/bin/env python3
"""
Database & Persistence Module.
SQLite storage for analysis runs, model performance, and portfolio analyses.
"""
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'market.db')

def get_connection(db_path=None):
    path = db_path or DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS analysis_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            run_timestamp TEXT NOT NULL,
            parameters TEXT,
            status TEXT DEFAULT 'completed'
        );

        CREATE TABLE IF NOT EXISTS analysis_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL REFERENCES analysis_runs(id),
            module_name TEXT NOT NULL,
            result_json TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS model_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            model_name TEXT NOT NULL,
            forecast_date TEXT NOT NULL,
            forecast_price REAL,
            actual_price REAL,
            error REAL,
            forecast_reliability REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS competitor_scans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            sector TEXT,
            n_peers INTEGER,
            peers_json TEXT,
            comparison_json TEXT,
            run_timestamp TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS portfolio_analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tickers TEXT NOT NULL,
            run_timestamp TEXT NOT NULL,
            correlation_matrix TEXT,
            optimization_results TEXT,
            portfolio_metrics TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_runs_ticker ON analysis_runs(ticker);
        CREATE INDEX IF NOT EXISTS idx_runs_timestamp ON analysis_runs(run_timestamp);
        CREATE INDEX IF NOT EXISTS idx_perf_ticker ON model_performance(ticker);
    ''')
    conn.commit()
    conn.close()

def save_run(ticker, parameters, status='completed', db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute(
        'INSERT INTO analysis_runs (ticker, run_timestamp, parameters, status) VALUES (?, ?, ?, ?)',
        (ticker, datetime.now().isoformat(), json.dumps(parameters), status)
    )
    run_id = c.lastrowid
    conn.commit()
    conn.close()
    return run_id

def save_result(run_id, module_name, result_dict, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute(
        'INSERT INTO analysis_results (run_id, module_name, result_json) VALUES (?, ?, ?)',
        (run_id, module_name, json.dumps(result_dict))
    )
    conn.commit()
    conn.close()

def save_model_performance(ticker, model_name, forecast_date,
                           forecast_price, actual_price, error,
                           forecast_reliability, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO model_performance
            (ticker, model_name, forecast_date, forecast_price, actual_price, error, forecast_reliability)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (ticker, model_name, forecast_date, forecast_price, actual_price, error, forecast_reliability))
    conn.commit()
    conn.close()

def save_competitor_scan(ticker, sector, n_peers, peers_json, comparison_json, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO competitor_scans
            (ticker, sector, n_peers, peers_json, comparison_json, run_timestamp)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (ticker, sector, n_peers, json.dumps(peers_json), json.dumps(comparison_json),
          datetime.now().isoformat()))
    conn.commit()
    conn.close()

def save_portfolio_analysis(tickers, correlation_matrix, optimization_results,
                            portfolio_metrics, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    c.execute('''
        INSERT INTO portfolio_analyses
            (tickers, run_timestamp, correlation_matrix, optimization_results, portfolio_metrics)
        VALUES (?, ?, ?, ?, ?)
    ''', (','.join(tickers), datetime.now().isoformat(),
          json.dumps(correlation_matrix), json.dumps(optimization_results),
          json.dumps(portfolio_metrics)))
    conn.commit()
    conn.close()

def get_recent_runs(ticker=None, limit=10, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    if ticker:
        c.execute('SELECT * FROM analysis_runs WHERE ticker = ? ORDER BY run_timestamp DESC LIMIT ?',
                  (ticker, limit))
    else:
        c.execute('SELECT * FROM analysis_runs ORDER BY run_timestamp DESC LIMIT ?', (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

def get_model_performance_history(ticker, model_name=None, limit=50, db_path=None):
    conn = get_connection(db_path)
    c = conn.cursor()
    if model_name:
        c.execute('''SELECT * FROM model_performance
                     WHERE ticker = ? AND model_name = ?
                     ORDER BY forecast_date DESC LIMIT ?''', (ticker, model_name, limit))
    else:
        c.execute('''SELECT * FROM model_performance
                     WHERE ticker = ?
                     ORDER BY forecast_date DESC LIMIT ?''', (ticker, limit))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows

if __name__ == '__main__':
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        db_path = sys.argv[2] if len(sys.argv) > 2 else None
        init_db(db_path)
        print(f"Database initialized at {db_path or DB_PATH}")
    else:
        init_db()
        print(f"Database initialized at {DB_PATH}")
