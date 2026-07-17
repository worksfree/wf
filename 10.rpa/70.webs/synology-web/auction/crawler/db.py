"""SQLite 저장소 — 개발/로컬 단계. 이후 Supabase PostgreSQL로 마이그레이션."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime

from config import DATA_DIR

DB_PATH = DATA_DIR / "auction.db"


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS auction_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            source          TEXT NOT NULL DEFAULT 'court',
            case_number     TEXT UNIQUE NOT NULL,
            court_name      TEXT,
            item_type       TEXT,
            address         TEXT,
            address_road    TEXT,
            sido            TEXT,
            sigungu         TEXT,
            dong            TEXT,
            lat             REAL,
            lng             REAL,
            area_exclusive  REAL,
            appraisal_price INTEGER,
            minimum_price   INTEGER,
            bid_date        TEXT,
            fail_count      INTEGER DEFAULT 0,
            status          TEXT DEFAULT 'active',
            detail_url      TEXT,
            raw_html        TEXT,
            created_at      TEXT DEFAULT (datetime('now','localtime')),
            updated_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS real_estate_trades (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_type      TEXT,
            sido            TEXT,
            sigungu         TEXT,
            dong            TEXT,
            jibun           TEXT,
            building_name   TEXT,
            area_exclusive  REAL,
            trade_price     INTEGER,
            trade_year      INTEGER,
            trade_month     INTEGER,
            trade_day       INTEGER,
            floor           INTEGER,
            build_year      INTEGER,
            lawd_cd         TEXT,
            lat             REAL,
            lng             REAL,
            created_at      TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS geocode_cache (
            address         TEXT PRIMARY KEY,
            lat             REAL,
            lng             REAL,
            cached_at       TEXT DEFAULT (datetime('now','localtime'))
        );

        CREATE INDEX IF NOT EXISTS idx_auction_sido    ON auction_items(sido, status);
        CREATE INDEX IF NOT EXISTS idx_auction_biddate ON auction_items(bid_date);
        CREATE INDEX IF NOT EXISTS idx_trade_dong      ON real_estate_trades(dong, trade_type);
        CREATE INDEX IF NOT EXISTS idx_trade_date      ON real_estate_trades(trade_year, trade_month);
        """)
    print(f"[db] initialized: {DB_PATH}")


def upsert_auction(item: dict) -> bool:
    """경매 물건 저장/갱신. 사건번호 기준 중복 제거."""
    sql = """
    INSERT INTO auction_items
        (source, case_number, court_name, item_type, address, address_road,
         sido, sigungu, dong, lat, lng, area_exclusive, appraisal_price,
         minimum_price, bid_date, fail_count, status, detail_url, raw_html, updated_at)
    VALUES
        (:source,:case_number,:court_name,:item_type,:address,:address_road,
         :sido,:sigungu,:dong,:lat,:lng,:area_exclusive,:appraisal_price,
         :minimum_price,:bid_date,:fail_count,:status,:detail_url,:raw_html,
         datetime('now','localtime'))
    ON CONFLICT(case_number) DO UPDATE SET
        minimum_price  = excluded.minimum_price,
        fail_count     = excluded.fail_count,
        bid_date       = excluded.bid_date,
        lat            = COALESCE(excluded.lat, lat),
        lng            = COALESCE(excluded.lng, lng),
        updated_at     = excluded.updated_at
    """
    row = {
        "source": item.get("source", "court"),
        "case_number": item["case_number"],
        "court_name": item.get("court_name"),
        "item_type": item.get("item_type"),
        "address": item.get("address"),
        "address_road": item.get("address_road"),
        "sido": item.get("sido"),
        "sigungu": item.get("sigungu"),
        "dong": item.get("dong"),
        "lat": item.get("lat"),
        "lng": item.get("lng"),
        "area_exclusive": item.get("area_exclusive"),
        "appraisal_price": item.get("appraisal_price"),
        "minimum_price": item.get("minimum_price"),
        "bid_date": item.get("bid_date"),
        "fail_count": item.get("fail_count", 0),
        "status": item.get("status", "active"),
        "detail_url": item.get("detail_url"),
        "raw_html": item.get("raw_html"),
    }
    try:
        with get_conn() as conn:
            conn.execute(sql, row)
        return True
    except Exception as e:
        print(f"[db] upsert_auction error: {e}")
        return False


def bulk_insert_trades(trades: list[dict]):
    """실거래가 일괄 저장."""
    sql = """
    INSERT OR IGNORE INTO real_estate_trades
        (trade_type, sido, sigungu, dong, jibun, building_name, area_exclusive,
         trade_price, trade_year, trade_month, trade_day, floor, build_year, lawd_cd)
    VALUES
        (:trade_type,:sido,:sigungu,:dong,:jibun,:building_name,:area_exclusive,
         :trade_price,:trade_year,:trade_month,:trade_day,:floor,:build_year,:lawd_cd)
    """
    if not trades:
        return
    with get_conn() as conn:
        conn.executemany(sql, trades)
    print(f"[db] inserted {len(trades)} trade records")


def get_geocache(address: str):
    with get_conn() as conn:
        row = conn.execute("SELECT lat, lng FROM geocode_cache WHERE address=?", (address,)).fetchone()
    return (row["lat"], row["lng"]) if row else None


def set_geocache(address: str, lat: float, lng: float):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO geocode_cache(address, lat, lng) VALUES(?,?,?)",
            (address, lat, lng)
        )


def get_stats() -> dict:
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM auction_items WHERE status='active'").fetchone()[0]
        trades = conn.execute("SELECT COUNT(*) FROM real_estate_trades").fetchone()[0]
        no_coords = conn.execute("SELECT COUNT(*) FROM auction_items WHERE lat IS NULL").fetchone()[0]
    return {"active_auctions": total, "trades": trades, "missing_coords": no_coords}
