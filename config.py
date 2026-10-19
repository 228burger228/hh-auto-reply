import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    load_dotenv()

# Основные параметры поиска hh.ru
HH_SEARCH_URL = os.getenv("HH_SEARCH_URL", "").strip()

# API Gemini для сопроводительных писем
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_PROXY = os.getenv("GEMINI_PROXY", "").strip()

# Профиль кандидата
MY_ROLE = os.getenv("MY_ROLE", "Веб-дизайнер / Frontend-разработчик")
PORTFOLIO_URL = os.getenv("PORTFOLIO_URL", "https://228burger228.github.io/burgerportfolio2.0/#design")
GAME_PORTFOLIO_URL = os.getenv("GAME_PORTFOLIO_URL", "https://228burger228.github.io/Game-portfolio/")
TELEGRAM = os.getenv("TELEGRAM", "@aimovl")

# Настройки для автозаполнения анкет и вопросов работодателя
ANSWER_FULL_NAME = os.getenv("ANSWER_FULL_NAME", "Дмитрий")
ANSWER_PHONE = os.getenv("ANSWER_PHONE", "")
ANSWER_EMAIL = os.getenv("ANSWER_EMAIL", "")
ANSWER_CITIZENSHIP = os.getenv("ANSWER_CITIZENSHIP", "РФ")
ANSWER_PORTFOLIO = os.getenv("ANSWER_PORTFOLIO", PORTFOLIO_URL)
ANSWER_GAME_PORTFOLIO = os.getenv("ANSWER_GAME_PORTFOLIO", GAME_PORTFOLIO_URL)
ANSWER_TELEGRAM = os.getenv("ANSWER_TELEGRAM", TELEGRAM)
ANSWER_EXPERIENCE_YEARS = os.getenv("ANSWER_EXPERIENCE_YEARS", "3")
ANSWER_SALARY = os.getenv("ANSWER_SALARY", "80000")
ANSWER_CITY = os.getenv("ANSWER_CITY", "Москва")
ANSWER_ABOUT_ME = os.getenv(
    "ANSWER_ABOUT_ME",
    "Веб-дизайнер и фронтенд-разработчик. Проектирую интерфейсы под ключ в Figma и делаю чистую адаптивную верстку. Кейсы: https://228burger228.github.io/burgerportfolio2.0/#design"
)

# Детальное описание бэкграунда и навыков
MY_EXPERIENCE = """
Специализация: Веб-дизайн и Frontend-разработка (Design Technologist). Закрываю задачи под ключ — от исследования, CJM и дизайн-системы в Figma до чистой адаптивной верстки в прод и бизнес-презентаций.

Ключевые навыки:
- UI/UX & Web Design: Figma (Auto Layout, дизайн-системы, компоненты, интерактивные прототипы, UI Kit, адаптив от 360px до 4K), Adobe Photoshop, Illustrator, InDesign.
- Frontend: HTML5, CSS3, JavaScript, Vue.js (Vue 3, Vite), Bootstrap 5, Git, нативный чистый код, семантика, оптимизация Google Lighthouse 95+.
- Разработка и архитектура: проектирование SaaS, B2B-интерфейсов, EdTech, SPA.

Реализованные проекты:
- HgStroy (https://hgstroy.ru): проектирование B2B-портала строительной компании, масштабируемая дизайн-система, верстка (HTML5/CSS3/JS/Bootstrap), ускорение загрузки в 2.4 раза (Lighthouse 95+).
- KINDORF Portal Pro: SaaS Канбан-платформа управления задачами с Drag&Drop, ролевой моделью RBAC (FastAPI, SQLite).
- Warpath Wiki: SPA-справочник игрового сообщества на Vue 3 + Vite + Supabase (10 000+ активных пользователей).
- Онлайн-академия AMAKids (Академика) и Study Up: дизайн-системы и адаптивная верстка онлайн-школ.
- vertical.team: конверсионный 8-секционный лендинг на чистом коде.

Портфолио: https://228burger228.github.io/burgerportfolio2.0/#design
Интерактивное портфолио: https://228burger228.github.io/Game-portfolio/
Telegram: @aimovl
"""

# API Gemini модель
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

# Режим работы браузера и оптимизация
HEADLESS = os.getenv("HEADLESS", "false").strip().lower() in ("true", "1", "yes")
DISK_CACHE_LIMIT_MB = int(os.getenv("DISK_CACHE_LIMIT_MB", "10"))
ENABLE_USER_ACTIVITY_PAUSE = os.getenv("ENABLE_USER_ACTIVITY_PAUSE", "false").strip().lower() in ("true", "1", "yes")

# Лимиты и задержки
MAX_APPLIES_PER_DAY = int(os.getenv("MAX_APPLIES_PER_DAY", "60"))
MIN_DELAY_SECONDS = int(os.getenv("MIN_DELAY_SECONDS", "4"))
MAX_DELAY_SECONDS = int(os.getenv("MAX_DELAY_SECONDS", "10"))

# Черные списки
_blacklist_words_raw = os.getenv("BLACKLIST_WORDS", "senior,lead,тимлид,руководитель,1c,1с,преподаватель,стажер,стажёр")
BLACKLIST_WORDS = [w.strip().lower() for w in _blacklist_words_raw.split(",") if w.strip()]

_blacklist_companies_raw = os.getenv("BLACKLIST_COMPANIES", "")
BLACKLIST_COMPANIES = [c.strip().lower() for c in _blacklist_companies_raw.split(",") if c.strip()]

# Директории
USER_DATA_DIR = str(BASE_DIR / "browser_profile")
DB_PATH = str(BASE_DIR / "applications.db")
