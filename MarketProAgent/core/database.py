"""
Database layer — SQLite with migrations for all trading data.
"""
import json
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any


class Database:
    def __init__(self, db_path: str = "./data/market.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        conn = self._conn()
        c = conn.cursor()
        c.executescript('''
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY, value TEXT
            );

            CREATE TABLE IF NOT EXISTS bars (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                open REAL, high REAL, low REAL, close REAL, volume INTEGER,
                UNIQUE(ticker, timestamp)
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL,
                side TEXT, order_type TEXT, quantity INTEGER,
                price REAL, trigger_price REAL, status TEXT,
                filled_quantity INTEGER DEFAULT 0, filled_price REAL,
                product TEXT, strategy TEXT, tag TEXT,
                created_at TEXT, filled_at TEXT
            );

            CREATE TABLE IF NOT EXISTS positions (
                id TEXT PRIMARY KEY,
                ticker TEXT NOT NULL, side TEXT,
                entry_price REAL, quantity INTEGER,
                current_price REAL, stop_loss REAL, trailing_sl REAL,
                entry_time TEXT, strategy TEXT, product TEXT
            );

            CREATE TABLE IF NOT EXISTS trades (
                id TEXT PRIMARY KEY,
                ticker TEXT, side TEXT,
                entry_price REAL, exit_price REAL, quantity INTEGER,
                entry_time TEXT, exit_time TEXT,
                strategy TEXT, pnl REAL, pnl_pct REAL, exit_reason TEXT
            );

            CREATE TABLE IF NOT EXISTS strategy_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT, strategy_name TEXT, signal TEXT,
                confidence REAL, entry_price REAL, stop_loss REAL,
                target REAL, reason TEXT, indicators TEXT,
                timestamp TEXT
            );

            CREATE TABLE IF NOT EXISTS analysis_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT, run_type TEXT, status TEXT,
                run_timestamp TEXT, result_json TEXT
            );

            CREATE TABLE IF NOT EXISTS portfolio_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tickers TEXT, run_timestamp TEXT,
                correlation_matrix TEXT, optimization_results TEXT,
                portfolio_metrics TEXT
            );

            CREATE TABLE IF NOT EXISTS market_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT, nifty_price REAL, bank_nifty_price REAL,
                vix REAL, advance_count INTEGER, decline_count INTEGER,
                fii_net_flow REAL, dii_net_flow REAL, pcr REAL,
                raw_json TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_bars_ticker_ts ON bars(ticker, timestamp);
            CREATE INDEX IF NOT EXISTS idx_trades_ticker ON trades(ticker);
            CREATE INDEX IF NOT EXISTS idx_trades_exit ON trades(exit_time);
            CREATE INDEX IF NOT EXISTS idx_signals_ticker ON strategy_signals(ticker);
        ''')
        conn.commit()
        conn.close()

    # --- Bars ---
    def save_bars(self, ticker: str, bars: List[Dict]):
        conn = self._conn()
        c = conn.cursor()
        for b in bars:
            c.execute('''INSERT OR REPLACE INTO bars
                (ticker, timestamp, open, high, low, close, volume)
                VALUES (?,?,?,?,?,?,?)''',
                (ticker, b['timestamp'], b['open'], b['high'], b['low'], b['close'], b['volume']))
        conn.commit()
        conn.close()

    def get_bars(self, ticker: str, limit: int = 500) -> List[Dict]:
        conn = self._conn()
        c = conn.cursor()
        c.execute('''SELECT * FROM bars WHERE ticker = ?
                      ORDER BY timestamp DESC LIMIT ?''', (ticker, limit))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    # --- Orders ---
    def save_order(self, order: Dict):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO orders
            (id, ticker, side, order_type, quantity, price, trigger_price,
             status, filled_quantity, filled_price, product, strategy, tag,
             created_at, filled_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            (order['id'], order['ticker'], order['side'], order['order_type'],
             order['quantity'], order.get('price'), order.get('trigger_price'),
             order['status'], order.get('filled_quantity', 0), order.get('filled_price'),
             order.get('product', 'MIS'), order.get('strategy', ''), order.get('tag', ''),
             order.get('created_at'), order.get('filled_at')))
        conn.commit()
        conn.close()

    def get_orders(self, ticker: Optional[str] = None, status: Optional[str] = None) -> List[Dict]:
        conn = self._conn()
        c = conn.cursor()
        query = "SELECT * FROM orders WHERE 1=1"
        params = []
        if ticker:
            query += " AND ticker = ?"
            params.append(ticker)
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC"
        c.execute(query, params)
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    # --- Positions ---
    def save_position(self, pos: Dict):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO positions
            (id, ticker, side, entry_price, quantity, current_price,
             stop_loss, trailing_sl, entry_time, strategy, product)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
            (pos['id'], pos['ticker'], pos['side'], pos['entry_price'],
             pos['quantity'], pos['current_price'], pos.get('stop_loss'),
             pos.get('trailing_sl'), pos['entry_time'], pos.get('strategy', ''),
             pos.get('product', 'MIS')))
        conn.commit()
        conn.close()

    def delete_position(self, pos_id: str):
        conn = self._conn()
        c = conn.cursor()
        c.execute("DELETE FROM positions WHERE id = ?", (pos_id,))
        conn.commit()
        conn.close()

    def get_open_positions(self) -> List[Dict]:
        conn = self._conn()
        c = conn.cursor()
        c.execute("SELECT * FROM positions")
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    # --- Trades ---
    def save_trade(self, trade: Dict):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO trades
            (id, ticker, side, entry_price, exit_price, quantity,
             entry_time, exit_time, strategy, pnl, pnl_pct, exit_reason)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
            (trade['id'], trade['ticker'], trade['side'],
             trade['entry_price'], trade['exit_price'], trade['quantity'],
             trade['entry_time'], trade['exit_time'], trade.get('strategy', ''),
             trade['pnl'], trade['pnl_pct'], trade.get('exit_reason', '')))
        conn.commit()
        conn.close()

    def get_trades(self, ticker: Optional[str] = None, limit: int = 50) -> List[Dict]:
        conn = self._conn()
        c = conn.cursor()
        if ticker:
            c.execute('''SELECT * FROM trades WHERE ticker = ?
                          ORDER BY exit_time DESC LIMIT ?''', (ticker, limit))
        else:
            c.execute('''SELECT * FROM trades ORDER BY exit_time DESC LIMIT ?''', (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    def get_trade_stats(self) -> Dict:
        conn = self._conn()
        c = conn.cursor()
        c.execute('''SELECT COUNT(*) as total,
            SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
            SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
            SUM(pnl) as total_pnl,
            AVG(pnl) as avg_pnl,
            MAX(pnl) as max_win,
            MIN(pnl) as max_loss
            FROM trades''')
        row = dict(c.fetchone())
        c.execute("SELECT SUM(pnl) FROM trades WHERE pnl > 0")  # gross profit
        row['gross_profit'] = (c.fetchone() or [0])[0] or 0
        c.execute("SELECT SUM(pnl) FROM trades WHERE pnl < 0")  # gross loss
        row['gross_loss'] = (c.fetchone() or [0])[0] or 0
        conn.close()
        return {k: v if v is not None else 0 for k, v in row.items()}

    # --- Signals ---
    def save_signal(self, signal: Dict):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT INTO strategy_signals
            (ticker, strategy_name, signal, confidence, entry_price,
             stop_loss, target, reason, indicators, timestamp)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (signal['ticker'], signal['strategy_name'], signal['signal'],
             signal['confidence'], signal.get('entry_price'), signal.get('stop_loss'),
             signal.get('target'), signal.get('reason', ''),
             json.dumps(signal.get('indicators', {})), signal.get('timestamp')))
        conn.commit()
        conn.close()

    def get_recent_signals(self, ticker: Optional[str] = None, limit: int = 20) -> List[Dict]:
        conn = self._conn()
        c = conn.cursor()
        if ticker:
            c.execute('''SELECT * FROM strategy_signals WHERE ticker = ?
                          ORDER BY timestamp DESC LIMIT ?''', (ticker, limit))
        else:
            c.execute('''SELECT * FROM strategy_signals ORDER BY timestamp DESC LIMIT ?''', (limit,))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()
        return rows

    # --- Analysis runs ---
    def save_analysis_run(self, ticker: str, run_type: str, result: Dict, status: str = "completed"):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT INTO analysis_runs (ticker, run_type, status, run_timestamp, result_json)
                      VALUES (?,?,?,?,?)''',
                  (ticker, run_type, status, datetime.now().isoformat(), json.dumps(result)))
        run_id = c.lastrowid
        conn.commit()
        conn.close()
        return run_id

    # --- Market context ---
    def save_market_context(self, ctx: Dict):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT INTO market_context
            (timestamp, nifty_price, bank_nifty_price, vix,
             advance_count, decline_count, fii_net_flow, dii_net_flow, pcr, raw_json)
            VALUES (?,?,?,?,?,?,?,?,?,?)''',
            (ctx.get('timestamp'), ctx.get('nifty_price'), ctx.get('bank_nifty_price'),
             ctx.get('vix'), ctx.get('advance_count'), ctx.get('decline_count'),
             ctx.get('fii_net_flow'), ctx.get('dii_net_flow'), ctx.get('pcr'),
             json.dumps(ctx)))
        conn.commit()
        conn.close()

    def get_latest_market_context(self) -> Optional[Dict]:
        conn = self._conn()
        c = conn.cursor()
        c.execute("SELECT * FROM market_context ORDER BY timestamp DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        return dict(row) if row else None

    # --- Portfolio ---
    def save_portfolio_analysis(self, tickers, corr, opt, metrics):
        conn = self._conn()
        c = conn.cursor()
        c.execute('''INSERT INTO portfolio_analyses
            (tickers, run_timestamp, correlation_matrix, optimization_results, portfolio_metrics)
            VALUES (?,?,?,?,?)''',
            (','.join(tickers), datetime.now().isoformat(),
             json.dumps(corr), json.dumps(opt), json.dumps(metrics)))
        conn.commit()
        conn.close()

    def close(self):
        pass  # SQLite connections are short-lived, nothing to close

    # --- Cleanup ---
    def cleanup_old_data(self, days: int = 365):
        cutoff = datetime.now().isoformat()
        conn = self._conn()
        c = conn.cursor()
        c.execute("DELETE FROM bars WHERE timestamp < date('now', ?)", (f'-{days} days',))
        c.execute("DELETE FROM analysis_runs WHERE run_timestamp < date('now', ?)", (f'-{days} days',))
        conn.commit()
        conn.close()
