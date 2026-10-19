import os
import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

import config

# Подавляем избыточные HTTP-логи от библиотек запросов
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("google.genai").setLevel(logging.WARNING)

PORTFOLIO_URL = getattr(config, "PORTFOLIO_URL", "https://228burger228.github.io/burgerportfolio2.0/#design")
GAME_PORTFOLIO_URL = getattr(config, "GAME_PORTFOLIO_URL", "https://228burger228.github.io/Game-portfolio/")
TELEGRAM = getattr(config, "TELEGRAM", "@aimovl")

_GEMINI_DISABLED = False
_GEMINI_TESTED = False

def extract_ats_focus(title: str, description: str) -> dict:
    """
    Выделение ключевых фокусов вакансии для точной адаптации письма.
    Анализирует требования: B2B/SaaS, мобильные приложения, дизайн-системы,
    Adobe Creative Cloud, полиграфию, лендинги и фронтенд.
    """
    text = (title + " " + description).lower()

    is_adobe = any(w in text for w in [
        "adobe", "photoshop", "illustrator", "indesign", "after effects", "creative cloud",
        "фотошоп", "иллюстратор", "индизайн", "адоб", "ps", "ai", "id"
    ])
    is_polygraphy = any(w in text for w in [
        "полиграф", "допечатн", "препресс", "prepress", "типографи", "печать", "cmyk",
        "каталог", "буклет", "листовк", "высечк", "вылеты", "цветокоррекц"
    ])
    is_motion = any(w in text for w in [
        "after effects", "motion", "моушн", "анимаци", "видеомонтаж", "premiere", "моушен"
    ])
    is_graphic = any(w in text for w in [
        "графическ", "айдентик", "брендбук", "логотип", "фирменн", "баннер", "баннеры",
        "креатив", "маркетплейс", "wildberries", "ozon", "карточк", "соцсет", "smm", "постер"
    ])
    is_mobile = any(w in text for w in [
        "мобильн", "mobile", "ios", "android", "приложени", "hig", "material"
    ])
    is_design_system = any(w in text for w in [
        "дизайн-систем", "ui-kit", "ui kit", "компонент", "компоненты", "атомарн", "ui-кит", "автолейаут", "auto layout", "variables"
    ])
    is_b2b_saas = any(w in text for w in [
        "b2b", "saas", "dashboard", "дашборд", "crm", "панель", "сервис", "личный кабинет", "аналитик", "портал"
    ])
    is_landing = any(w in text for w in [
        "лендинг", "landing", "промо", "маркетинг", "тильда", "tilda", "конверси", "презентаци"
    ])
    is_poly_layout = any(p in text for p in [
        "indesign", "индизайн", "полиграф", "каталог", "буклет", "журнал", "книг", "печать", "допечатн", "prepress", "типографи"
    ])
    is_frontend = any(w in text for w in [
        "frontend", "фронтенд", "vue", "javascript", "react", "разработчик", "html", "css", "веб-верстк", "верстальщик сайтов"
    ]) or ("верстк" in text and not is_poly_layout)
    is_design = any(w in text for w in [
        "дизайн", "figma", "ui/ux", "ux/ui", "ui", "ux", "интерфейс", "веб-дизайн"
    ])

    return {
        "adobe": is_adobe,
        "polygraphy": is_polygraphy,
        "motion": is_motion,
        "graphic": is_graphic,
        "mobile": is_mobile,
        "design_system": is_design_system,
        "b2b": is_b2b_saas,
        "landing": is_landing,
        "frontend": is_frontend,
        "design": is_design
    }

def generate_smart_fallback(
    vacancy_title: str,
    company: str,
    vacancy_description: str,
    portfolio_url: str = PORTFOLIO_URL,
    game_portfolio_url: str = GAME_PORTFOLIO_URL,
    telegram: str = TELEGRAM
) -> str:
    """
    Интеллектуальная адаптивная сборка письма под конкретную вакансию и компанию.
    Анализирует текст вакансии, выявляет боли работодателя (B2B, Mobile, Design Systems,
    E-Commerce, Adobe/Graphic, Frontend) и формирует живой партнерский ответ без шаблонности.
    """
    focus = extract_ats_focus(vacancy_title, vacancy_description)
    comp_clean = company.strip() if company and company != "Компания не указана" else ""
    comp_target = f"в команду {comp_clean}" if comp_clean else "в вашей компании"

    # 1. Вводная часть
    intro = f"Здравствуйте!\n\nЗаинтересовала вакансия «{vacancy_title}» {comp_target}."

    # 2. Основной фокус под конкретную потребность работодателя
    if focus["polygraphy"]:
        main_focus = (
            "Свободно работаю в связке Adobe (InDesign, Photoshop, Illustrator) и Figma. "
            "Отлично знаю допечатную подготовку (prepress, CMYK, вылеты под обрез, цветоделение, шрифты) "
            "и аккуратную верстку многостраничных изданий и каталогов."
        )
    elif focus["b2b"]:
        main_focus = (
            "Специализируюсь на проектировании B2B-сервисов, личных кабинетов и сложных веб-интерфейсов в Figma. "
            "Глубоко прорабатываю логику пользовательских сценариев (UX), эргономику таблиц и плотность данных, "
            "чтобы интерфейс закрывал реальные потребности клиентов и бизнес-цели компании."
        )
    elif focus["mobile"]:
        main_focus = (
            "Проектирую адаптивные и мобильные интерфейсы в Figma по гайдлайнам iOS (HIG) и Material Design. "
            "Уделяю особое внимание логике взаимодействия под пальцы, чистоте экранов и интерактивным прототипам, "
            "чтобы продуктом было по-настоящему удобно пользоваться каждый день."
        )
    elif focus["design_system"]:
        main_focus = (
            "Фокусируюсь на создании масштабируемых дизайн-систем и UI Kit в Figma. "
            "Выстраиваю чистую компонентную базу, Auto Layout, переменные (Variables) и дизайн-токены, "
            "чтобы продукт легко развивался, а команда разработки не тратила время на переделки."
        )
    elif focus["landing"] or focus["graphic"]:
        if focus["adobe"]:
            main_focus = (
                "Создаю сильную графику и визуал в связке Figma + Adobe Creative Cloud (Photoshop, Illustrator): "
                "от конверсионных страниц, баннеров и промо-материалов до векторных ассетов и айдентики, "
                "строго соблюдая композицию, сетки и визуальные стандарты бренда."
            )
        else:
            main_focus = (
                "Проектирую конверсионные веб-страницы и интерфейсы в Figma: выстраиваю сильную визуальную иерархию, "
                "аккуратную типографику и логику, которая закрывает задачи бизнеса и мягко ведет пользователя к целевому действию."
            )
    elif focus["frontend"] and not focus["design"]:
        main_focus = (
            "Занимаюсь фронтенд-разработкой и адаптивной версткой. "
            "Сам проектирую макеты в Figma и работаю с графикой в Adobe, поэтому собираю чистый семантический код "
            "пиксель-в-пиксель, оптимизирую графику (SVG/WebP) и держу Lighthouse 95+."
        )
    else:
        # Универсальный продуктовый / UI/UX фокус высокого уровня
        adobe_str = " и свободно владею пакетом Adobe (Photoshop, Illustrator)" if focus["adobe"] else ""
        main_focus = (
            f"Занимаюсь продуктовым и UI/UX дизайном. Проектирую интерфейсы в Figma{adobe_str}, "
            f"которые закрывают реальные потребности пользователей и помогают бизнесу расти — "
            f"от исследований и сценариев до дизайн-систем и адаптивных макетов."
        )

    # 3. Техническое преимущество / связка навыков под требования вакансии
    support_points = []
    if focus["frontend"] and not focus["polygraphy"] and "фронтенд" not in main_focus.lower():
        support_points.append(
            "Отлично понимаю веб-разработку, поэтому макеты проектирую с учетом реального кода — верстальщики собирают их в продакшн чисто и без переделок."
        )
    elif focus["adobe"] and "adobe" not in main_focus.lower():
        support_points.append(
            "В работе активно использую Photoshop и Illustrator для сложной графики, ретуши и векторных ассетов."
        )
    elif not focus["polygraphy"] and not focus["frontend"]:
        support_points.append(
            "Хорошо понимаю принципы верстки и продуктовой аналитики, ориентируюсь на измеримую пользу для продукта."
        )

    support_str = (" " + " ".join(support_points)) if support_points else ""
    body = f"{main_focus}{support_str}"

    return (
        f"{intro}\n\n"
        f"{body}\n\n"
        f"Мои реальные проекты и интерактивные работы:\n"
        f"• Основное портфолио: {portfolio_url}\n"
        f"• Интерактивная игра-портфолио: {game_portfolio_url}\n\n"
        f"Буду рад познакомиться с командой и обсудить задачи! Для связи: Telegram {telegram}."
    )

def generate_cover_letter(
    vacancy_title: str,
    company: str,
    vacancy_description: str,
    my_role: str,
    my_experience: str,
    api_key: Optional[str] = None,
    proxy: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    """
    Генератор письма. Если Gemini доступен — генерирует персональное письмо под описание вакансии,
    иначе мгновенно отдает глубоко адаптированный Smart ATS ответ под стек компании.
    """
    global _GEMINI_DISABLED, _GEMINI_TESTED

    if api_key and not _GEMINI_DISABLED:
        try:
            from google import genai
            from google.genai import types

            client_kwargs = {"api_key": api_key}
            if proxy:
                client_kwargs["http_options"] = types.HttpOptions(proxy=proxy)

            client = genai.Client(**client_kwargs)

            prompt = f"""
Ты — опытный продуктовый дизайнер и карьерный консультант. Напиши живое, убедительное сопроводительное письмо на вакансию "{vacancy_title}" в компанию "{company}".

ВНИМАТЕЛЬНО ИЗУЧИ ОПИСАНИЕ ВАКАНСИИ И ВЫДЕЛИ ГЛАВНЫЕ ПОТРЕБНОСТИ РАБОТОДАТЕЛЯ:
{vacancy_description[:1800]}

Профиль кандидата:
- Специализация: Продуктовый дизайнер, UI/UX дизайнер, Design Technologist, Графический дизайнер.
- Мышление: закрывать реальные потребности клиентов и задачи бизнеса, а не просто рисовать макеты.
- Инструменты: Figma (Auto Layout, UI Kit, дизайн-системы, компоненты, переменные), Adobe Creative Cloud (Photoshop, Illustrator, InDesign, After Effects).
- Frontend: HTML5, CSS3, JavaScript, Vue 3, чистый адаптивный код (Lighthouse 95+), полное понимание ограничений верстки.
- Опыт: B2B-сервисы (HgStroy), SaaS платформы (KINDORF), EdTech, промо-страницы, графика.

ПРАВИЛА НАПИСАНИЯ:
1. Пиши живо, от первого лица, как уверенный партнер (без списков 1, 2, 3 и без корпоративного канцелярита).
2. Сделай прямой акцент именно на тех задачах и инструментах, которые требует ЭТА конкретная вакансия (если просят Figma/UI — акцент на интерфейсах и логике; если просят Photoshop/Illustrator — органично покажи сильный визуал в Adobe; если B2B/SaaS — акцент на сценариях и эргономике данных).
3. Длина письма: 3-4 емких, плотных предложения.
4. Обязательно включи ссылки:
• Основное портфолио: {PORTFOLIO_URL}
• Интерактивная игра-портфолио: {GAME_PORTFOLIO_URL}
Telegram: {TELEGRAM}
5. Выведи ТОЛЬКО готовый текст письма.
"""
            target_model = model or getattr(config, "GEMINI_MODEL", "gemini-2.5-flash")
            models_to_try = [target_model, "gemini-2.5-flash-lite", "gemini-2.0-flash"]
            seen = set()
            models_to_try = [m for m in models_to_try if not (m in seen or seen.add(m))]

            for model_name in models_to_try:
                try:
                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    letter = response.text.strip()
                    if letter:
                        _GEMINI_TESTED = True
                        return letter
                except Exception as inner_e:
                    err_msg = str(inner_e).lower()
                    if "user location" in err_msg or "unregistered" in err_msg or "forbidden" in err_msg:
                        logger.info("ℹ️ Gemini API недоступен в текущей сети (нужен прокси/VPN). Работает встроенный Smart ATS генератор.")
                        _GEMINI_DISABLED = True
                        break
                    continue

        except Exception as e:
            logger.debug(f"Gemini API пропущен: {e}")
            if not _GEMINI_TESTED:
                _GEMINI_DISABLED = True
                logger.info("ℹ️ Gemini API недоступен. Работает встроенный Smart ATS генератор.")

    return generate_smart_fallback(
        vacancy_title=vacancy_title,
        company=company,
        vacancy_description=vacancy_description,
        portfolio_url=PORTFOLIO_URL,
        game_portfolio_url=GAME_PORTFOLIO_URL,
        telegram=TELEGRAM
    )
