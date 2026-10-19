import os
import sys
import time
import random
import logging
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from playwright.sync_api import sync_playwright, Page, TimeoutError

import config
import database
from ai_generator import generate_cover_letter

from logging.handlers import RotatingFileHandler

# Логирование с ограничением размера файлов (макс 3 МБ, 2 бэкапа)
log_file_path = os.path.join(config.BASE_DIR, "bot.log")
file_handler = RotatingFileHandler(log_file_path, maxBytes=3*1024*1024, backupCount=2, encoding="utf-8")
stream_handler = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[file_handler, stream_handler]
)
logger = logging.getLogger("hh_bot")

# Подавление избыточных логов сетевых библиотек
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# Флаги активности
LAST_USER_ACTIVITY_TIME = 0.0
IS_BOT_ACTING = False

def on_user_activity():
    """Коллбэк при физическом действии пользователя в окне браузера."""
    global LAST_USER_ACTIVITY_TIME
    if not getattr(config, "ENABLE_USER_ACTIVITY_PAUSE", False) or IS_BOT_ACTING:
        return
    LAST_USER_ACTIVITY_TIME = time.time()

def check_user_activity_and_pause():
    """
    Если включена опция ENABLE_USER_ACTIVITY_PAUSE и пользователь взаимодействовал с окном,
    бот делает короткую паузу (5 сек), чтобы не конфликтовать.
    """
    if not getattr(config, "ENABLE_USER_ACTIVITY_PAUSE", False):
        return

    global LAST_USER_ACTIVITY_TIME
    elapsed = time.time() - LAST_USER_ACTIVITY_TIME
    if elapsed < 5.0 and not IS_BOT_ACTING:
        remaining = int(5.0 - elapsed)
        logger.info(f"🖐️ Пользователь активен в окне. Пауза {remaining} сек...")
        while time.time() - LAST_USER_ACTIVITY_TIME < 5.0:
            time.sleep(1)
        logger.info("▶️ Продолжаем работу.")

def setup_page_listeners(page: Page):
    """Привязка отслеживания кликов и клавиатуры на странице только если включено в config."""
    if not getattr(config, "ENABLE_USER_ACTIVITY_PAUSE", False):
        return

    try:
        page.expose_binding("onUserActivity", lambda source: on_user_activity())
    except Exception:
        pass

    try:
        page.add_init_script("""
            window.addEventListener('mousedown', (e) => {
                if (e.isTrusted) {
                    try { window.onUserActivity(); } catch(err) {}
                }
            }, true);
            window.addEventListener('keydown', (e) => {
                if (e.isTrusted) {
                    try { window.onUserActivity(); } catch(err) {}
                }
            }, true);
        """)
    except Exception:
        pass

def sleep_random(min_sec: float = None, max_sec: float = None):
    """Случайная задержка для имитации поведения человека."""
    check_user_activity_and_pause()
    mn = min_sec if min_sec is not None else config.MIN_DELAY_SECONDS
    mx = max_sec if max_sec is not None else config.MAX_DELAY_SECONDS
    delay = random.uniform(mn, mx)
    time.sleep(delay)
    check_user_activity_and_pause()

def is_blacklisted(title: str, company: str) -> bool:
    """
    Проверка вакансии и компании по черным спискам.
    Специальное исключение: «арт-директор» / «art director» НЕ блокируются.
    """
    title_lower = title.lower()
    company_lower = company.lower()

    for word in config.BLACKLIST_WORDS:
        if word in title_lower:
            # Если это арт-директор, не блокируем
            if word in ["директор", "director"] and any(ad in title_lower for ad in ["арт-директор", "арт директор", "art-director", "art director"]):
                continue

            logger.info(f"Пропуск вакансии «{title}»: стоп-слово в названии «{word}».")
            return True

    for comp in config.BLACKLIST_COMPANIES:
        if comp and comp in company_lower:
            logger.info(f"Пропуск вакансии от компании «{company}»: компания в черном списке.")
            return True

    return False

def check_and_wait_for_captcha(page: Page) -> bool:
    """
    Проверяет наличие ЛЮБОЙ капчи на странице (SmartCaptcha, текстовая капча 'перепишите слова',
    картинка со словами, reCAPTCHA, Cloudflare, плашка hh.ru).
    Если обнаружена капча:
    останавливает бота, сигнализирует звуком и ждет, пока пользователь решит её в браузере.
    """
    def is_captcha_present() -> bool:
        try:
            # 1. URL проверки / капчи
            cur_url = page.url.lower()
            if any(k in cur_url for k in ["captcha", "checkcaptcha", "showcaptcha"]):
                return True

            # 2. Поля ввода капчи с картинки / текста со словами
            captcha_inputs = [
                'input[name*="captcha"]',
                'input[id*="captcha"]',
                'input[data-qa*="captcha"]',
                'img[src*="captcha"]',
                'img[class*="captcha"]'
            ]
            for c_sel in captcha_inputs:
                el = page.query_selector(c_sel)
                if el and el.is_visible():
                    return True

            # 3. Элементы интерактивной капчи
            interactive_selectors = [
                'iframe[src*="captcha"]',
                'iframe[src*="smartcaptcha"]',
                'iframe[src*="recaptcha"]',
                'div[class*="captcha"]',
                'div[id*="captcha"]',
                '.smart-captcha',
                '[data-qa="captcha"]',
                'div[data-name="smart-captcha"]'
            ]
            for sel in interactive_selectors:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    return True

            # 4. Текстовые индикаторы капчи (включая "перепишите слова", "символы с картинки" и т.д.)
            body_text = page.inner_text("body").lower() if page.query_selector("body") else ""
            captcha_phrases = [
                "перепишите слова",
                "введите слово",
                "символы с картинки",
                "введите код",
                "код с картинки",
                "подтвердите, что вы не робот",
                "проверка безопасности",
                "smartcaptcha",
                "пожалуйста, пройдите проверку",
                "вы робот",
                "подтверждение действия"
            ]
            if any(p in body_text for p in captcha_phrases):
                return True

            return False
        except Exception:
            return False

    if is_captcha_present():
        # Мягкий системный звук уведомления Windows вместо громкого зуммера
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        logger.warning("\n" + "=" * 65)
        logger.warning("⚠️  ОБНАРУЖЕНА КАПЧА (ВВОД СЛОВ / ПРОВЕРКА РОБОТА) НА HH.RU!")
        logger.warning("Бот временно остановлен, чтобы вы могли ввести слова или решить капчу.")
        logger.warning("👉 Пожалуйста, перейдите в открытое окно браузера и решите капчу.")
        logger.warning("Как только капча исчезнет, бот автоматически продолжит работу!")
        logger.warning("=" * 65 + "\n")

        # Ожидание решения капчи пользователем
        while is_captcha_present():
            time.sleep(2)

        logger.info("✅ Капча успешно пройдена! Бот возобновляет автоотклики...")
        sleep_random(2, 4)
        return True

    return False

def check_authorization(page: Page) -> bool:
    """Проверка, авторизован ли пользователь на hh.ru."""
    logger.info("Проверяем статус авторизации на hh.ru...")
    safe_goto(page, "https://hh.ru/")
    sleep_random(2, 3)

    if page.query_selector('[data-qa="mainmenu_applicantprofile"]') or \
       page.query_selector('[data-qa="mainmenu_myResumes"]') or \
       page.query_selector('[data-qa="mainmenu_profile"]'):
        logger.info("Авторизация подтверждена. Профиль найден!")
        return True

    login_btn = page.query_selector('[data-qa="login"]') or page.query_selector('a:has-text("Войти")')
    if login_btn:
        logger.warning("Вы не авторизованы на hh.ru.")
        return False

    return True

def wait_for_user_login(page: Page):
    """Ожидание ручной авторизации пользователем в окне браузера."""
    logger.info("=======================================================")
    logger.info("ТРЕБУЕТСЯ АВТОРИЗАЦИЯ:")
    logger.info("Пожалуйста, войдите в свой аккаунт hh.ru в открытом окне браузера.")
    logger.info("После успешного входа бот автоматически продолжит работу.")
    logger.info("=======================================================")

    safe_goto(page, "https://hh.ru/account/login")

    while True:
        sleep_random(3, 4)
        check_and_wait_for_captcha(page)
        try:
            if page.query_selector('[data-qa="mainmenu_applicantprofile"]') or \
               page.query_selector('[data-qa="mainmenu_myResumes"]') or \
               page.query_selector('[data-qa="mainmenu_profile"]'):
                logger.info("Успешный вход в аккаунт обнаружен! Сохраняем сессию...")
                sleep_random(2, 3)
                break
        except Exception:
            pass

def safe_goto(page: Page, url: str) -> bool:
    """Безопасный переход по URL с проверкой капчи и паузы пользователя."""
    check_user_activity_and_pause()
    try:
        page.goto(url, wait_until="commit", timeout=25000)
        try:
            page.wait_for_load_state("domcontentloaded", timeout=7000)
        except Exception:
            pass
        check_and_wait_for_captcha(page)
        check_user_activity_and_pause()
        return True
    except Exception as e:
        logger.warning(f"Ошибка при загрузке страницы {url}: {e}")
        return False

def parse_vacancy_urls_from_search(page: Page) -> list[str]:
    """Парсинг ссылок на вакансии со страницы поисковой выдачи."""
    check_and_wait_for_captcha(page)
    check_user_activity_and_pause()
    vacancy_links = []
    card_elements = page.query_selector_all(
        '[data-qa="vacancy-serp__vacancy-title"], '
        '[data-qa="serp-item__title"], '
        'a[href*="/vacancy/"]'
    )

    for el in card_elements:
        href = el.get_attribute("href")
        if not href:
            continue
        if "/vacancy/" in href:
            clean_url = href.split("?")[0]
            if clean_url not in vacancy_links:
                vacancy_links.append(clean_url)

    logger.info(f"Найдено уникальных вакансий на странице: {len(vacancy_links)}")
    return vacancy_links

def answer_screening_questions(page: Page, vacancy_title: str) -> bool:
    """
    Интеллектуальное автозаполнение анкеты и обязательных вопросов работодателя.
    Заполняет ссылки на портфолио, Telegram, опыт, зарплату, радиокнопки и чекбоксы.
    """
    try:
        check_and_wait_for_captcha(page)
        check_user_activity_and_pause()

        # 1. Если требуется выбрать резюме (когда в профиле их несколько)
        resume_items = page.query_selector_all('[data-qa="vacancy-response-resume-item"], input[name="resumeId"]')
        if resume_items:
            checked = page.query_selector('input[name="resumeId"]:checked')
            if not checked:
                is_design_vac = any(k in vacancy_title.lower() for k in ["дизайн", "ui", "ux", "figma", "арт"])
                selected = False
                for r_item in resume_items:
                    text = r_item.inner_text().lower()
                    if is_design_vac and ("дизайн" in text or "ui" in text or "web" in text or "арт" in text):
                        r_item.click()
                        selected = True
                        break
                    elif not is_design_vac and ("front" in text or "разработ" in text or "верст" in text):
                        r_item.click()
                        selected = True
                        break
                if not selected and resume_items:
                    resume_items[0].click()
                sleep_random(0.5, 1)

        # 2. Текстовые инпуты (input[type="text"], input[type="number"], без типа)
        inputs = page.query_selector_all('input[type="text"], input[type="number"], input:not([type])')
        for inp in inputs:
            check_user_activity_and_pause()
            if not inp.is_visible():
                continue
            curr_val = inp.input_value()
            if curr_val and curr_val.strip():
                continue

            label_text = ""
            try:
                parent = inp.evaluate_handle('el => el.closest(".bloko-form-item, [data-qa*=\'question\'], div")')
                if parent:
                    label_text = parent.as_element().inner_text().lower()
            except Exception:
                pass

            placeholder = (inp.get_attribute("placeholder") or "").lower()
            name_attr = (inp.get_attribute("name") or "").lower()
            context = f"{label_text} {placeholder} {name_attr}"

            if any(k in context for k in ["портфолио", "portfolio", "ссылк", "behance", "dribbble", "github", "проект", "сайт", "макет"]):
                logger.info(f"Анкета: заполняем портфолио ({context[:35]}...)")
                inp.fill(config.ANSWER_PORTFOLIO)
            elif any(k in context for k in ["ваше имя", "фио", "как вас зовут", "имя", "name"]):
                full_name = getattr(config, "ANSWER_FULL_NAME", "Дмитрий")
                logger.info(f"Анкета: заполняем имя ({full_name})")
                inp.fill(full_name)
            elif any(k in context for k in ["телефон", "phone", "номер телефона", "моб"]):
                phone = getattr(config, "ANSWER_PHONE", "")
                if phone:
                    logger.info(f"Анкета: заполняем телефон ({phone})")
                    inp.fill(phone)
                else:
                    inp.fill(config.ANSWER_TELEGRAM)
            elif any(k in context for k in ["email", "e-mail", "почт", "электрон"]):
                email = getattr(config, "ANSWER_EMAIL", "")
                if email:
                    logger.info(f"Анкета: заполняем email ({email})")
                    inp.fill(email)
                else:
                    inp.fill(config.ANSWER_TELEGRAM)
            elif any(k in context for k in ["гражданств", "страна"]):
                citizenship = getattr(config, "ANSWER_CITIZENSHIP", "РФ")
                logger.info(f"Анкета: заполняем гражданство ({citizenship})")
                inp.fill(citizenship)
            elif any(k in context for k in ["telegram", "телеграм", "тг", "tg", "ник", "мессенджер", "связь", "контакт"]):
                logger.info(f"Анкета: заполняем Telegram ({config.ANSWER_TELEGRAM})")
                inp.fill(config.ANSWER_TELEGRAM)
            elif any(k in context for k in ["опыт", "стаж", "лет", "сколько лет", "коммерческ", "experience"]):
                logger.info(f"Анкета: заполняем опыт работы ({config.ANSWER_EXPERIENCE_YEARS})")
                inp.fill(str(config.ANSWER_EXPERIENCE_YEARS))
            elif any(k in context for k in ["зарплат", "доход", "ожидания", "оклад", "руб", "salary"]):
                logger.info(f"Анкета: заполняем зарплатные ожидания ({config.ANSWER_SALARY})")
                inp.fill(str(config.ANSWER_SALARY))
            elif any(k in context for k in ["город", "локация", "проживание", "где вы"]):
                logger.info(f"Анкета: заполняем город ({config.ANSWER_CITY})")
                inp.fill(config.ANSWER_CITY)
            elif any(k in context for k in ["о себе", "расскажите", "почему", "комментар"]):
                logger.info(f"Анкета: заполняем информацию о себе")
                inp.fill(config.ANSWER_ABOUT_ME)
            else:
                inp_type = (inp.get_attribute("type") or "text").lower()
                if inp_type == "number":
                    inp.fill(str(config.ANSWER_EXPERIENCE_YEARS))
                else:
                    logger.info(f"Анкета: заполняем поле ({context[:35]}...)")
                    inp.fill(config.ANSWER_PORTFOLIO)
            sleep_random(0.3, 0.7)

        # 3. Дополнительные текстовые области (textarea), кроме сопроводительного
        textareas = page.query_selector_all('textarea:not([data-qa*="letter"]):not([name="message"])')
        for ta in textareas:
            check_user_activity_and_pause()
            if not ta.is_visible():
                continue
            if ta.input_value().strip():
                continue
            ta.fill(config.ANSWER_ABOUT_ME)
            sleep_random(0.5, 1)

        # 4. Радиокнопки (тестовые задания, готовность к работе и т.д.)
        radios = page.query_selector_all('input[type="radio"]')
        grouped_radios = {}
        for r in radios:
            name = r.get_attribute("name") or "default"
            grouped_radios.setdefault(name, []).append(r)

        for name, r_list in grouped_radios.items():
            is_checked = any(r.is_checked() for r in r_list)
            if is_checked:
                continue

            picked = False
            for r in r_list:
                try:
                    parent_text = r.evaluate_handle('el => el.closest("label, .bloko-radio, div")').as_element().inner_text().lower()
                    if any(pos in parent_text for pos in ["да", "готов", "конечно", "имею", "есть", "yes", "согласен"]):
                        r.click()
                        picked = True
                        logger.info(f"Анкета: выбрали вариант '{parent_text.strip()}'")
                        break
                except Exception:
                    pass

            if not picked and r_list:
                try:
                    r_list[0].click()
                except Exception:
                    pass

        # 5. Чекбоксы согласий / подтверждений
        checkboxes = page.query_selector_all('input[type="checkbox"]:not(:checked)')
        for cb in checkboxes:
            if cb.is_visible():
                try:
                    parent_text = cb.evaluate_handle('el => el.closest("label, .bloko-checkbox, div")').as_element().inner_text().lower()
                    if any(k in parent_text for k in ["соглас", "ознаком", "подтвержд", "готов"]):
                        cb.click()
                        sleep_random(0.2, 0.5)
                except Exception:
                    pass

        return True
    except Exception as e:
        logger.warning(f"Примечание при обработке анкеты: {e}")
        return True

def apply_to_vacancy(page: Page, vacancy_url: str) -> bool:
    """
    Переход на вакансию, заполнение анкеты, вставка письма и реальная проверка отправки отклика.
    """
    global IS_BOT_ACTING
    IS_BOT_ACTING = True
    try:
        return _apply_to_vacancy_impl(page, vacancy_url)
    finally:
        IS_BOT_ACTING = False

def _apply_to_vacancy_impl(page: Page, vacancy_url: str) -> bool:
    vac_id = vacancy_url.rstrip("/").split("/")[-1]

    if database.is_vacancy_processed(vac_id):
        logger.info(f"Вакансия {vac_id} уже есть в базе данных как обработанная. Пропуск.")
        return False

    logger.info(f"\n--- Открываем вакансию: {vacancy_url} ---")
    if not safe_goto(page, vacancy_url):
        return False

    sleep_random(2, 3)
    check_and_wait_for_captcha(page)

    # Получаем название и компанию
    title_el = page.query_selector('[data-qa="vacancy-title"], h1')
    title = title_el.inner_text().strip() if title_el else "Без названия"

    comp_el = page.query_selector('[data-qa="vacancy-company-name"], a[href*="/employer/"]')
    company = comp_el.inner_text().strip() if comp_el else "Компания не указана"

    logger.info(f"Должность: {title} | Компания: {company}")

    # Проверка черного списка (с сохранением арт-директора)
    if is_blacklisted(title, company):
        database.save_application(vac_id, title, company, vacancy_url, status="skipped_blacklist")
        return False

    # Проверка, не откликались ли уже на сайте
    already_responded = page.query_selector('[data-qa="vacancy-response-link-view-topic"]')
    if not already_responded:
        top_btn = page.query_selector('[data-qa="vacancy-response-link-top"]')
        if top_btn and "вы откликнулись" in top_btn.inner_text().lower():
            already_responded = top_btn

    if already_responded:
        logger.info("Уже откликались на эту вакансию на hh.ru ранее (кнопка 'Вы откликнулись').")
        database.save_application(vac_id, title, company, vacancy_url, status="already_applied_on_site")
        return False

    # Кнопка "Откликнуться"
    response_btn = page.query_selector('[data-qa="vacancy-response-link-top"]')
    if not response_btn:
        response_btn = page.query_selector('button:has-text("Откликнуться"), a:has-text("Откликнуться")')

    if not response_btn:
        logger.info("Кнопка 'Откликнуться' не найдена (вакансия закрыта или в архиве).")
        database.save_application(vac_id, title, company, vacancy_url, status="skipped_no_btn")
        return False

    # Считываем описание вакансии
    desc_el = page.query_selector('[data-qa="vacancy-description"]')
    description = desc_el.inner_text() if desc_el else ""

    # Генерируем естественное сопроводительное письмо
    logger.info("Формируем сопроводительное письмо под стек вакансии...")
    cover_letter = generate_cover_letter(
        vacancy_title=title,
        company=company,
        vacancy_description=description,
        my_role=config.MY_ROLE,
        my_experience=config.MY_EXPERIENCE,
        api_key=config.GEMINI_API_KEY,
        proxy=config.GEMINI_PROXY
    )
    logger.info(f"Текст письма:\n{cover_letter}\n")

    # Нажимаем "Откликнуться"
    try:
        check_user_activity_and_pause()
        response_btn.scroll_into_view_if_needed()
        sleep_random(1, 2)
        response_btn.click()
        sleep_random(2, 3)
    except Exception as e:
        logger.error(f"Ошибка при клике на 'Откликнуться': {e}")
        return False

    check_and_wait_for_captcha(page)

    # Проверка на многостраничный тест
    if page.query_selector('[data-qa="task-test"]'):
        logger.warning(f"Вакансия {vac_id} требует комплексного стороннего тестирования. Безопасно пропускаем.")
        database.save_application(vac_id, title, company, vacancy_url, cover_letter, status="skipped_test")
        return False

    # 1. Автоматическое заполнение анкеты работодателя (вопросы, ссылки, радиокнопки)
    answer_screening_questions(page, title)

    # 2. Раскрываем поле сопроводительного письма, если оно свернуто
    add_letter_btn = page.query_selector(
        '[data-qa="vacancy-response-letter-toggle"], '
        'button:has-text("Добавить сопроводительное"), '
        'button:has-text("Написать сопроводительное"), '
        'span:has-text("Добавить сопроводительное"), '
        'span:has-text("Написать сопроводительное")'
    )
    if add_letter_btn and add_letter_btn.is_visible():
        try:
            logger.info("Открываем поле сопроводительного письма...")
            add_letter_btn.click()
            sleep_random(0.5, 1)
        except Exception:
            pass

    # 3. Вставляем текст сопроводительного письма
    textarea = page.query_selector(
        '[data-qa="vacancy-response-letter-text"], '
        '[data-qa="vacancy-response-popup-letter-text"], '
        'textarea[name="message"], '
        'textarea'
    )
    if textarea and textarea.is_visible():
        try:
            textarea.fill(cover_letter)
            sleep_random(1, 1.5)
        except Exception as e:
            logger.warning(f"Не удалось заполнить поле письма: {e}")

    # 4. Кнопка отправки отклика в модалке / на странице
    submit_btn = page.query_selector(
        '[data-qa="vacancy-response-submit-popup"], '
        '[data-qa="vacancy-response-submit"], '
        'button:has-text("Отправить отклик"), '
        'button:has-text("Отправить"), '
        'button:has-text("Откликнуться")'
    )

    if submit_btn and submit_btn.is_visible():
        try:
            check_user_activity_and_pause()
            logger.info("Нажимаем кнопку отправки отклика...")
            submit_btn.click()
            sleep_random(3, 5)

            check_and_wait_for_captcha(page)

            # Проверяем наличие ошибок валидации анкеты
            errors = page.query_selector_all('.bloko-form-error, [data-qa*="error"], .bloko-input_error')
            visible_errors = [e.inner_text().strip() for e in errors if e.is_visible() and e.inner_text().strip()]

            if visible_errors:
                logger.warning(f"Форма не отправилась из-за обязательного вопроса: {', '.join(visible_errors)}")
                database.save_application(vac_id, title, company, vacancy_url, cover_letter, status="skipped_questionnaire_error")
                return False

            # Проверяем подтверждение отправки
            responded_marker = (
                page.query_selector('[data-qa="vacancy-response-link-view-topic"]') or
                page.query_selector('text="Вы откликнулись"') or
                page.query_selector('text="Отклик отправлен"') or
                (not page.query_selector('[data-qa="vacancy-response-popup"]') and not page.query_selector('[data-qa="vacancy-response-submit-popup"]'))
            )

            if responded_marker:
                logger.info(f"✅ [УСПЕХ] Отклик на «{title}» ({company}) подтвержден и отправлен!")
                database.save_application(vac_id, title, company, vacancy_url, cover_letter, status="applied")
                return True
            else:
                logger.warning(f"Статус отправки на «{title}» не подтвержден сайтом.")
                database.save_application(vac_id, title, company, vacancy_url, cover_letter, status="unconfirmed")
                return False

        except Exception as e:
            logger.error(f"Ошибка при подтверждении отправки: {e}")
            return False
    else:
        # Проверяем мгновенный отклик в 1 клик
        if page.query_selector('[data-qa="vacancy-response-link-view-topic"]') or page.query_selector('text="Вы откликнулись"'):
            logger.info(f"✅ [УСПЕХ] Отклик отправлен в 1 клик!")
            database.save_application(vac_id, title, company, vacancy_url, cover_letter, status="applied")
            return True
        else:
            logger.warning("Окно отклика не закрылось или кнопка отправки была недоступна.")
            return False

def build_search_url_for_page(base_url: str, page_num: int) -> str:
    """Добавление номера страницы к поисковой ссылке hh.ru."""
    parsed = urlparse(base_url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page_num)]
    new_query = urlencode(qs, doseq=True)
    return urlunparse(parsed._replace(query=new_query))

def run_bot():
    """Основной цикл работы бота с учетом лимитов и оптимизацией кеша."""
    database.init_db()
    today_applied = database.get_today_applied_count()
    logger.info(f"Запуск автоотклика. Отправлено за сегодня: {today_applied} / {config.MAX_APPLIES_PER_DAY}.")

    if today_applied >= config.MAX_APPLIES_PER_DAY:
        logger.info(f"🎯 Сегодня уже достигнут дневной лимит откликов ({config.MAX_APPLIES_PER_DAY}). Завершаем работу.")
        return

    # Ограничение размера кеша Chromium
    cache_limit_bytes = getattr(config, "DISK_CACHE_LIMIT_MB", 10) * 1024 * 1024
    chrome_args = [
        "--disable-blink-features=AutomationControlled",
        "--start-maximized",
        f"--disk-cache-size={cache_limit_bytes}",
        f"--media-cache-size={cache_limit_bytes}",
        "--disable-gpu-shader-disk-cache",
        "--disable-application-cache"
    ]

    with sync_playwright() as p:
        # Браузер с сохранением сессии авторизации
        context = p.chromium.launch_persistent_context(
            user_data_dir=config.USER_DATA_DIR,
            headless=getattr(config, "HEADLESS", False),
            slow_mo=100,
            args=chrome_args,
            viewport=None
        )

        page = context.pages[0] if context.pages else context.new_page()
        setup_page_listeners(page)
        context.on("page", lambda new_p: setup_page_listeners(new_p))

        # Проверка авторизации и капчи
        check_and_wait_for_captcha(page)
        if not check_authorization(page):
            wait_for_user_login(page)

        current_page_idx = 0
        total_applied_this_session = 0
        seen_vacancies_this_session = set()

        try:
            while True:
                if today_applied >= config.MAX_APPLIES_PER_DAY:
                    logger.info(f"🎯 Достигнут дневной лимит откликов ({config.MAX_APPLIES_PER_DAY}). Завершаем сессию.")
                    break

                check_user_activity_and_pause()
                search_url = build_search_url_for_page(config.HH_SEARCH_URL, current_page_idx)
                logger.info(f"\n=======================================================")
                logger.info(f"🔍 Поиск: страница #{current_page_idx + 1}")
                logger.info(f"URL: {search_url}")
                logger.info(f"=======================================================")

                if not safe_goto(page, search_url):
                    logger.error("Не удалось открыть страницу поиска, пробуем повторить...")
                    sleep_random(3, 5)
                    if not safe_goto(page, search_url):
                        break

                sleep_random(2, 4)
                check_and_wait_for_captcha(page)
                vacancy_urls = parse_vacancy_urls_from_search(page)

                if not vacancy_urls:
                    logger.info("На этой странице нет доступных вакансий или закончилась выдача поиска.")
                    break

                # Проверка на зацикливание страниц поиска hh.ru
                new_urls = [u for u in vacancy_urls if u not in seen_vacancies_this_session]
                if not new_urls:
                    logger.info("Все вакансии на этой странице уже встречались в этой сессии (конец выдачи).")
                    break

                for v_url in new_urls:
                    seen_vacancies_this_session.add(v_url)

                    if today_applied >= config.MAX_APPLIES_PER_DAY:
                        logger.info(f"🎯 Достигнут дневной лимит откликов ({config.MAX_APPLIES_PER_DAY}). Завершаем сессию.")
                        break

                    check_user_activity_and_pause()
                    check_and_wait_for_captcha(page)
                    success = apply_to_vacancy(page, v_url)
                    if success:
                        today_applied += 1
                        total_applied_this_session += 1
                        logger.info(f"📊 Статистика: отправлено {total_applied_this_session} за сессию (всего за день: {today_applied} / {config.MAX_APPLIES_PER_DAY}).")
                        sleep_random()
                    else:
                        sleep_random(2, 3)

                current_page_idx += 1
                sleep_random(3, 5)

        except KeyboardInterrupt:
            logger.info("\n[ОСТАНОВКА] Бот был остановлен пользователем (Ctrl+C).")
        except Exception as e:
            logger.error(f"Непредвиденная ошибка в основном цикле: {e}", exc_info=True)

        logger.info("\n=======================================================")
        logger.info(f"Работа сессии завершена! Отправлено откликов за сессию: {total_applied_this_session}")
        logger.info("Браузер остается открытым для вашего контроля.")
        logger.info("=======================================================")
        
        try:
            input("\nНажмите Enter в консоли, чтобы закрыть браузер и выйти...")
        except Exception:
            pass

        context.close()

if __name__ == "__main__":
    run_bot()
