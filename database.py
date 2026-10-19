import sqlite3
from datetime import datetime, date
from typing import Optional
from config import DB_PATH

def get_connection():
    """Создание устойчивого подключения к SQLite с таймаутом."""
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    return conn

def init_db():
    """Инициализация базы данных и таблицы откликов."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            vacancy_id TEXT PRIMARY KEY,
            title TEXT,
            company TEXT,
            url TEXT,
            cover_letter TEXT,
            status TEXT,
            applied_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def is_vacancy_processed(vacancy_id: str) -> bool:
    """Проверка, откликались ли уже на эту вакансию."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM applications WHERE vacancy_id = ?", (vacancy_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_application(
    vacancy_id: str,
    title: str,
    company: str,
    url: str,
    cover_letter: str = "",
    status: str = "applied"
):
    """Сохранение факта отклика в БД."""
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO applications (vacancy_id, title, company, url, cover_letter, status, applied_date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (vacancy_id, title, company, url, cover_letter, status, today_str))
    conn.commit()
    conn.close()

def get_today_applied_count() -> int:
    """Подсчет количества успешных откликов за сегодня."""
    today_str = date.today().isoformat()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM applications 
        WHERE applied_date = ? AND status = 'applied'
    """, (today_str,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_total_stats() -> dict:
    """Общая статистика откликов из базы данных."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*), COUNT(DISTINCT company) FROM applications WHERE status = 'applied'")
    total_applied, unique_companies = cursor.fetchone()
    
    cursor.execute("SELECT MIN(applied_date), MAX(applied_date) FROM applications WHERE status = 'applied'")
    min_date, max_date = cursor.fetchone()
    
    conn.close()
    return {
        "total_applied": total_applied or 0,
        "unique_companies": unique_companies or 0,
        "first_date": min_date or "-",
        "last_date": max_date or "-"
    }

def get_recent_applications(limit: int = 7) -> list:
    """Получение последних откликов."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT vacancy_id, title, company, url, status, applied_date, created_at
        FROM applications
        ORDER BY created_at DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_daily_history(days: int = 7) -> list:
    """Статистика откликов по дням за последние N дней."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT applied_date, COUNT(*) 
        FROM applications 
        WHERE status = 'applied'
        GROUP BY applied_date 
        ORDER BY applied_date DESC 
        LIMIT ?
    """, (days,))
    rows = cursor.fetchall()
    conn.close()
    return rows

