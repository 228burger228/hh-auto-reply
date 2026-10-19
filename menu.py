"""
HH.RU Auto-Reply Bot — Интерактивный CLI-дашборд и менеджер
Стиль: Бизнес-Премиум (Vanilla Python, без внешних UI-зависимостей)
Разработчик: Dmitry (@228burger228)
"""

import os
import sys
import time
import shutil
from pathlib import Path

# Обеспечиваем корректную UTF-8 кодировку для консоли Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass

import config
import database
from ai_generator import generate_cover_letter, extract_ats_focus

# ANSI-стили для бизнес-минимализма
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def print_header():
    """Элегантный заголовок консоли."""
    today_applied = database.get_today_applied_count()
    stats = database.get_total_stats()
    total_applies = stats.get("total_applied", 0)
    
    print(f"{CYAN}┌────────────────────────────────────────────────────────────────────────┐{RESET}")
    print(f"{CYAN}│{RESET}  {BOLD}HH.RU AUTO-REPLY BOT{RESET} — {DIM}Design Technologist & UI/UX Edition{RESET}            {CYAN}│{RESET}")
    print(f"{CYAN}│{RESET}  {DIM}GitHub: @228burger228  •  v2.0 Business-Premium CLI                    {RESET}{CYAN}│{RESET}")
    print(f"{CYAN}├────────────────────────────────────────────────────────────────────────┤{RESET}")
    
    status_color = GREEN if today_applied < config.MAX_APPLIES_PER_DAY else YELLOW
    print(f"{CYAN}│{RESET}  Статус: {status_color}● Активен{RESET} | Сегодня: {BOLD}{today_applied}/{config.MAX_APPLIES_PER_DAY}{RESET} | Всего в базе: {BOLD}{total_applies}{RESET}     {CYAN}│{RESET}")
    print(f"{CYAN}└────────────────────────────────────────────────────────────────────────┘{RESET}\n")

def view_statistics():
    """Экран подробной аналитики откликов."""
    clear_screen()
    print_header()
    print(f"{BOLD}📊 АНАЛИТИКА И ИСТОРИЯ ОТКЛИКОВ{RESET}\n")
    
    stats = database.get_total_stats()
    today_count = database.get_today_applied_count()
    daily_history = database.get_daily_history(days=7)
    recent_applies = database.get_recent_applications(limit=7)
    
    print(f"  • Всего отправлено откликов:   {BOLD}{GREEN}{stats['total_applied']}{RESET}")
    print(f"  • Уникальных работодателей:   {BOLD}{CYAN}{stats['unique_companies']}{RESET}")
    print(f"  • Откликов за сегодня:        {BOLD}{today_count} / {config.MAX_APPLIES_PER_DAY}{RESET}")
    print(f"  • Дата первого отклика:       {DIM}{stats['first_date']}{RESET}")
    print(f"  • Последняя активность:       {DIM}{stats['last_date']}{RESET}\n")
    
    print(f"{BOLD}📅 Динамика за последние дни:{RESET}")
    if daily_history:
        for day, cnt in daily_history:
            bar = "█" * min(cnt // 5 + 1, 30)
            print(f"  {day} : {CYAN}{bar}{RESET} ({cnt})")
    else:
        print(f"  {DIM}Нет данных за прошедшие дни.{RESET}")
    print()

    print(f"{BOLD}🕒 Последние 7 откликов:{RESET}")
    if recent_applies:
        for app in recent_applies:
            _, title, company, url, status, app_date, _ = app
            clean_title = (title[:38] + "..") if len(title) > 40 else title
            clean_comp = (company[:23] + "..") if len(company) > 25 else company
            print(f"  • [{app_date}] {BOLD}{clean_title}{RESET} @ {CYAN}{clean_comp}{RESET}")
            print(f"    {DIM}{url}{RESET}")
    else:
        print(f"  {DIM}История откликов пуста.{RESET}")
        
    print()
    input(f"{DIM}Нажмите Enter для возврата в главное меню...{RESET}")

def update_env_file(key: str, value: str):
    """Обновление или добавление переменной в файл .env с сохранением комментариев."""
    env_path = config.ENV_PATH
    lines = []
    found = False
    
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(f"{key}=") or stripped.startswith(f"{key} ="):
            new_lines.append(f"{key}={value}\n")
            found = True
        else:
            new_lines.append(line)
            
    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines.append("\n")
        new_lines.append(f"{key}={value}\n")
        
    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

def settings_menu():
    """Экран настройки параметров поиска и ограничений."""
    while True:
        clear_screen()
        print_header()
        print(f"{BOLD}⚙️  НАСТРОЙКИ И ФИЛЬТРЫ (.env){RESET}\n")
        
        search_preview = config.HH_SEARCH_URL
        if len(search_preview) > 60:
            search_preview = search_preview[:57] + "..."
            
        print(f"  [1] Поисковый URL:        {CYAN}{search_preview or 'Не задан'}{RESET}")
        print(f"  [2] Дневной лимит:        {BOLD}{config.MAX_APPLIES_PER_DAY}{RESET} откликов")
        print(f"  [3] Режим браузера:       {BOLD}{'Фоновый (Headless)' if config.HEADLESS else 'Видимый (с окном)'}{RESET}")
        print(f"  [4] Ожидаемая зарплата:   {BOLD}{config.ANSWER_SALARY}{RESET} руб.")
        print(f"  [5] Задержки между кликами: {config.MIN_DELAY_SECONDS} - {config.MAX_DELAY_SECONDS} сек.")
        print(f"  [6] Телефон в анкетах:    {BOLD}{config.ANSWER_PHONE or 'Не указан'}{RESET}")
        print(f"  [7] Email в анкетах:      {BOLD}{config.ANSWER_EMAIL or 'Не указан'}{RESET}")
        print(f"\n  [0] Сохранить и вернуться в главное меню\n")
        
        choice = input(f"{BOLD}Выберите пункт для изменения [0-7]: {RESET}").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            print(f"\nТекущий URL: {config.HH_SEARCH_URL}")
            new_url = input("Вставьте новый URL поиска с hh.ru (или Enter для отмены): ").strip()
            if new_url:
                update_env_file("HH_SEARCH_URL", new_url)
                config.HH_SEARCH_URL = new_url
                print(f"{GREEN}✓ URL поиска успешно обновлен!{RESET}")
                time.sleep(1.2)
        elif choice == "2":
            new_limit = input(f"Введите новый дневной лимит (сейчас {config.MAX_APPLIES_PER_DAY}): ").strip()
            if new_limit.isdigit() and int(new_limit) > 0:
                update_env_file("MAX_APPLIES_PER_DAY", new_limit)
                config.MAX_APPLIES_PER_DAY = int(new_limit)
                print(f"{GREEN}✓ Лимит обновлен!{RESET}")
                time.sleep(1.2)
        elif choice == "3":
            new_val = not config.HEADLESS
            update_env_file("HEADLESS", "true" if new_val else "false")
            config.HEADLESS = new_val
            print(f"{GREEN}✓ Режим переключен на: {'Headless' if new_val else 'Видимый'}{RESET}")
            time.sleep(1.2)
        elif choice == "4":
            new_sal = input(f"Введите желаемую зарплату (сейчас {config.ANSWER_SALARY}): ").strip()
            if new_sal:
                update_env_file("ANSWER_SALARY", new_sal)
                config.ANSWER_SALARY = new_sal
                print(f"{GREEN}✓ Зарплата обновлена!{RESET}")
                time.sleep(1.2)
        elif choice == "5":
            min_d = input(f"Минимальная задержка (сек, сейчас {config.MIN_DELAY_SECONDS}): ").strip()
            max_d = input(f"Максимальная задержка (сек, сейчас {config.MAX_DELAY_SECONDS}): ").strip()
            if min_d.isdigit() and max_d.isdigit() and int(max_d) >= int(min_d):
                update_env_file("MIN_DELAY_SECONDS", min_d)
                update_env_file("MAX_DELAY_SECONDS", max_d)
                config.MIN_DELAY_SECONDS = int(min_d)
                config.MAX_DELAY_SECONDS = int(max_d)
                print(f"{GREEN}✓ Задержки обновлены!{RESET}")
                time.sleep(1.2)
        elif choice == "6":
            new_phone = input(f"Введите телефон для анкет: ").strip()
            if new_phone:
                update_env_file("ANSWER_PHONE", new_phone)
                config.ANSWER_PHONE = new_phone
                print(f"{GREEN}✓ Телефон обновлен!{RESET}")
                time.sleep(1.2)
        elif choice == "7":
            new_email = input(f"Введите Email для анкет: ").strip()
            if new_email:
                update_env_file("ANSWER_EMAIL", new_email)
                config.ANSWER_EMAIL = new_email
                print(f"{GREEN}✓ Email обновлен!{RESET}")
                time.sleep(1.2)

def test_letter_generation():
    """Тестирование генератора сопроводительных писем под вакансию."""
    clear_screen()
    print_header()
    print(f"{BOLD}📝 ТЕСТ ГЕНЕРАЦИИ СОПРОВОДИТЕЛЬНОГО ПИСЬМА (Smart ATS){RESET}\n")
    print("Введите параметры тестовой вакансии для проверки подбора аргументов и кейсов.")
    
    title = input(f"\n{BOLD}Название вакансии{RESET} (например, 'UI/UX дизайнер в B2B SaaS' или 'Верстальщик / Графический дизайнер'): ").strip()
    if not title:
        title = "Product UI/UX Designer / Design Technologist"
        
    company = input(f"{BOLD}Название компании{RESET} (например, 'Яндекс', 'TechCorp' или пусто): ").strip()
    desc = input(f"{BOLD}Ключевые требования{RESET} (например, 'Figma, Auto Layout, Vue, дизайн-система, полиграфия'): ").strip()
    
    print(f"\n{YELLOW}⚙️  Анализируем стек и генерируем письмо...{RESET}\n")
    
    focus_keys = extract_ats_focus(title, desc)
    letter = generate_cover_letter(title, company, desc)
    
    print(f"{CYAN}┌── Выделенный фокус ATS ────────────────────────────────────────────────┐{RESET}")
    print(f"  Категории: {BOLD}{', '.join(focus_keys)}{RESET}")
    print(f"{CYAN}├── Сгенерированное письмо ──────────────────────────────────────────────┤{RESET}")
    print(letter)
    print(f"{CYAN}└────────────────────────────────────────────────────────────────────────┘{RESET}\n")
    
    input(f"{DIM}Нажмите Enter для возврата в главное меню...{RESET}")

def check_browser_session():
    """Открытие браузера для проверки авторизации или прохождения капчи."""
    clear_screen()
    print_header()
    print(f"{BOLD}🔑 ПРОВЕРКА АВТОРИЗАЦИИ И СЕССИИ HH.RU{RESET}\n")
    print("Сейчас откроется окно Chromium с вашим сохраненным профилем.")
    print("Вы сможете убедиться, что вы вошли в аккаунт на hh.ru, или решить капчу.")
    print(f"{YELLOW}Автоматический поиск вакансий в этом режиме НЕ запускается.{RESET}\n")
    
    from playwright.sync_api import sync_playwright
    
    try:
        with sync_playwright() as p:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                f"--disk-cache-size={config.DISK_CACHE_LIMIT_MB * 1024 * 1024}"
            ]
            
            context = p.chromium.launch_persistent_context(
                user_data_dir=config.USER_DATA_DIR,
                headless=False,
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                locale="ru-RU",
                timezone_id="Europe/Moscow",
                args=args
            )
            
            page = context.pages[0] if context.pages else context.new_page()
            print(f"{GREEN}Браузер запущен. Переходим на hh.ru...{RESET}")
            page.goto("https://hh.ru", wait_until="domcontentloaded")
            
            print(f"\n{BOLD}Окно браузера открыто.{RESET}")
            input(f"{CYAN}Нажмите Enter в этой консоли, когда закончите просмотр, чтобы закрыть браузер...{RESET}")
            context.close()
            print(f"{GREEN}✓ Браузер закрыт.{RESET}")
            time.sleep(1)
    except Exception as e:
        print(f"{RED}Ошибка запуска браузера: {e}{RESET}")
        input(f"{DIM}Нажмите Enter...{RESET}")

def clean_cache():
    """Очистка дискового кеша профиля с подсчетом освобожденного места."""
    clear_screen()
    print_header()
    print(f"{BOLD}🧹 ОЧИСТКА ДИСКОВОГО КЕША БРАУЗЕРА{RESET}\n")
    
    profile_dir = Path(config.USER_DATA_DIR)
    if not profile_dir.exists():
        print(f"{YELLOW}Папка профиля еще не создана. Очистка не требуется.{RESET}")
        time.sleep(1.5)
        return
        
    cache_targets = [
        profile_dir / "Default" / "Cache",
        profile_dir / "Default" / "Code Cache",
        profile_dir / "Default" / "GPUCache",
        profile_dir / "Default" / "Service Worker" / "CacheStorage",
        profile_dir / "Default" / "Service Worker" / "ScriptCache",
        profile_dir / "GrShaderCache",
        profile_dir / "ShaderCache"
    ]
    
    total_freed_bytes = 0
    cleaned_dirs = 0
    
    for target in cache_targets:
        if target.exists():
            for root, dirs, files in os.walk(target):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_freed_bytes += os.path.getsize(fp)
                    except Exception:
                        pass
            try:
                shutil.rmtree(target, ignore_errors=True)
                cleaned_dirs += 1
            except Exception:
                pass
                
    freed_mb = total_freed_bytes / (1024 * 1024)
    print(f"{GREEN}✓ Кеш успешно очищен!{RESET}")
    print(f"  • Освобождено на диске: {BOLD}{freed_mb:.2f} МБ{RESET}")
    print(f"  • Сессия, cookies и авторизация {BOLD}полностью сохранены{RESET}.\n")
    
    input(f"{DIM}Нажмите Enter для возврата в главное меню...{RESET}")

def main():
    database.init_db()
    
    while True:
        clear_screen()
        print_header()
        
        print(f"{BOLD}ГЛАВНОЕ МЕНЮ ДЕЙСТВИЙ:{RESET}")
        print(f"  {CYAN}[1]{RESET} 🚀 {BOLD}Запустить автоотклик{RESET} {DIM}(поиск и отправка писем){RESET}")
        print(f"  {CYAN}[2]{RESET} 📊 {BOLD}Аналитика и статистика{RESET} {DIM}(графики и история в БД){RESET}")
        print(f"  {CYAN}[3]{RESET} ⚙️  {BOLD}Настройки и фильтры{RESET} {DIM}(изменение .env из консоли){RESET}")
        print(f"  {CYAN}[4]{RESET} 📝 {BOLD}Тест генератора писем{RESET} {DIM}(Smart ATS песочница){RESET}")
        print(f"  {CYAN}[5]{RESET} 🔑 {BOLD}Проверка сессии hh.ru{RESET} {DIM}(открыть окно браузера){RESET}")
        print(f"  {CYAN}[6]{RESET} 🧹 {BOLD}Очистить кеш браузера{RESET} {DIM}(освободить диск){RESET}")
        print(f"  {CYAN}[0]{RESET} 🚪 {BOLD}Выход{RESET}\n")
        
        choice = input(f"{BOLD}Выберите действие [0-6]: {RESET}").strip()
        
        if choice == "1":
            clear_screen()
            print_header()
            print(f"{GREEN}🚀 Запускаем рабочий цикл бота...{RESET}\n")
            try:
                import bot
                bot.run_bot()
            except KeyboardInterrupt:
                print(f"\n{YELLOW}Работа остановлена пользователем.{RESET}")
            except Exception as e:
                print(f"\n{RED}Ошибка выполнения: {e}{RESET}")
            print()
            input(f"{DIM}Нажмите Enter для возврата в меню...{RESET}")
        elif choice == "2":
            view_statistics()
        elif choice == "3":
            settings_menu()
        elif choice == "4":
            test_letter_generation()
        elif choice == "5":
            check_browser_session()
        elif choice == "6":
            clean_cache()
        elif choice == "0":
            print(f"\n{CYAN}До новых встреч! Успешного поиска работы.{RESET}\n")
            break

if __name__ == "__main__":
    main()
