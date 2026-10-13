#!/usr/bin/env python3
import re, json, os
import psycopg2, bcrypt
from flask import Flask, request, jsonify, session, Response

app = Flask(__name__)
app.secret_key = "CHANGE_ME_FLASK_SECRET_KEY"

DB_DSN = "host=127.0.0.1 dbname=foxdb user=fox password=CHANGE_ME_DB_PASSWORD"
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# ── 77 вопросов ──────────────────────────────────────────────────────────────

QUESTIONS = [
    # Блок 1 — Основная информация (10)
    {"id":1,"block":1,"bt":"Основная информация","text":"Сколько вам лет?","type":"number","unit":"лет","min":10,"max":100},
    {"id":2,"block":1,"bt":"Основная информация","text":"Ваш пол","type":"radio","opts":["Мужской","Женский"]},
    {"id":3,"block":1,"bt":"Основная информация","text":"Ваш рост","type":"number","unit":"см","min":100,"max":250},
    {"id":4,"block":1,"bt":"Основная информация","text":"Ваш текущий вес","type":"number","unit":"кг","min":30,"max":300},
    {"id":5,"block":1,"bt":"Основная информация","text":"Желаемый вес","type":"number","unit":"кг","min":30,"max":300},
    {"id":6,"block":1,"bt":"Основная информация","text":"Ваша главная цель","type":"radio","opts":["Похудеть","Набрать мышечную массу","Поддержать текущий вес","Оздоровиться и улучшить самочувствие","Нормализовать обмен веществ"]},
    {"id":7,"block":1,"bt":"Основная информация","text":"За какой срок хотите достичь цели?","type":"radio","opts":["1–2 месяца","3–6 месяцев","6–12 месяцев","Более года","Постепенно, без сроков"]},
    {"id":8,"block":1,"bt":"Основная информация","text":"Пробовали ли вы диеты раньше?","type":"radio","opts":["Нет, впервые","Да, с хорошим результатом","Да, без заметного результата","Да, вес возвращался"]},
    {"id":9,"block":1,"bt":"Основная информация","text":"Ваш тип телосложения","type":"radio","opts":["Эктоморф (худощавый, сложно набрать вес)","Мезоморф (мышечный, легко меняет форму)","Эндоморф (склонен к полноте)","Не знаю"]},
    {"id":10,"block":1,"bt":"Основная информация","text":"Ваша профессиональная деятельность","type":"radio","opts":["Офисная / сидячая работа","Физический труд","Смешанная (частично сидячая)","Учёба","Нахожусь дома"]},
    # Блок 2 — Физическая активность (12)
    {"id":11,"block":2,"bt":"Физическая активность","text":"Общий уровень физической активности","type":"radio","opts":["Минимальный (практически не двигаюсь)","Низкий (немного хожу пешком)","Умеренный (регулярные прогулки)","Высокий (спорт несколько раз в неделю)","Очень высокий (ежедневные интенсивные тренировки)"]},
    {"id":12,"block":2,"bt":"Физическая активность","text":"Чем занимаетесь физически?","type":"radio","opts":["Не занимаюсь","Зал / упражнения дома","Бег / велосипед / плавание","Командные виды спорта","Йога / пилатес / растяжка","Несколько видов активности"]},
    {"id":13,"block":2,"bt":"Физическая активность","text":"Как часто тренируетесь?","type":"radio","opts":["Не тренируюсь","1–2 раза в неделю","3–4 раза в неделю","5–6 раз в неделю","Каждый день"]},
    {"id":14,"block":2,"bt":"Физическая активность","text":"Средняя продолжительность тренировки","type":"radio","opts":["Не тренируюсь","До 30 минут","30–60 минут","60–90 минут","Более 90 минут"]},
    {"id":15,"block":2,"bt":"Физическая активность","text":"Интенсивность тренировок","type":"radio","opts":["Лёгкая (не потею, не задыхаюсь)","Средняя (умеренная нагрузка)","Высокая (выкладываюсь полностью)","Не тренируюсь"]},
    {"id":16,"block":2,"bt":"Физическая активность","text":"Примерное количество шагов в день","type":"radio","opts":["Менее 3 000","3 000–6 000","6 000–10 000","10 000–15 000","Более 15 000"]},
    {"id":17,"block":2,"bt":"Физическая активность","text":"Сколько часов в день проводите сидя?","type":"radio","opts":["До 3 часов","3–6 часов","6–9 часов","Более 9 часов"]},
    {"id":18,"block":2,"bt":"Физическая активность","text":"Работаете ли в ночные смены?","type":"radio","opts":["Нет","Иногда","Регулярно (1–2 раза в неделю)","Постоянно"]},
    {"id":19,"block":2,"bt":"Физическая активность","text":"Как проводите выходные?","type":"radio","opts":["Активно (прогулки, спорт, природа)","Спокойно (дома, отдых)","По-разному"]},
    {"id":20,"block":2,"bt":"Физическая активность","text":"Пользуетесь ли лифтом?","type":"radio","opts":["Нет, всегда хожу пешком","Иногда","Да, практически всегда"]},
    {"id":21,"block":2,"bt":"Физическая активность","text":"Как добираетесь на работу / учёбу?","type":"radio","opts":["Пешком или на велосипеде","Общественный транспорт","На автомобиле","Работаю из дома"]},
    {"id":22,"block":2,"bt":"Физическая активность","text":"Планируете добавить физическую активность?","type":"radio","opts":["Да, готов начать","Уже занимаюсь и продолжу","Хотел бы, но сложно найти время","Пока нет"]},
    # Блок 3 — Режим питания (12)
    {"id":23,"block":3,"bt":"Режим питания","text":"Сколько раз в день едите?","type":"radio","opts":["1–2 раза","3 раза","4–5 раз","Более 5 раз","Нерегулярно, когда получится"]},
    {"id":24,"block":3,"bt":"Режим питания","text":"Всегда ли завтракаете?","type":"radio","opts":["Да, всегда","Иногда","Редко","Никогда — не хочу есть утром"]},
    {"id":25,"block":3,"bt":"Режим питания","text":"Время первого приёма пищи","type":"radio","opts":["До 7:00","7:00–9:00","9:00–11:00","После 11:00","Нет чёткого времени"]},
    {"id":26,"block":3,"bt":"Режим питания","text":"Время последнего приёма пищи","type":"radio","opts":["До 18:00","18:00–20:00","20:00–22:00","После 22:00","Нет чёткого времени"]},
    {"id":27,"block":3,"bt":"Режим питания","text":"Перекусываете между едой?","type":"radio","opts":["Нет","Редко","Да, 1–2 перекуса","Да, постоянно перекусываю"]},
    {"id":28,"block":3,"bt":"Режим питания","text":"Что обычно едите на перекус?","type":"radio","opts":["Фрукты / овощи","Орехи / сухофрукты","Сладкое / выпечка","Бутерброды / снэки","Не перекусываю"]},
    {"id":29,"block":3,"bt":"Режим питания","text":"Пропускаете ли приёмы пищи?","type":"radio","opts":["Нет, всегда ем вовремя","Иногда пропускаю обед","Часто пропускаю из-за занятости","Практикую интервальное голодание"]},
    {"id":30,"block":3,"bt":"Режим питания","text":"С какой скоростью едите?","type":"radio","opts":["Быстро (10–15 минут)","Нормально (20–30 минут)","Медленно (30+ минут)"]},
    {"id":31,"block":3,"bt":"Режим питания","text":"Едите ли перед экраном (TV, телефон)?","type":"radio","opts":["Да, почти всегда","Иногда","Нет, ем без гаджетов"]},
    {"id":32,"block":3,"bt":"Режим питания","text":"Едите ли из-за эмоций (стресс, скука)?","type":"radio","opts":["Нет","Иногда","Часто","Да, это главная причина переедания"]},
    {"id":33,"block":3,"bt":"Режим питания","text":"Контролируете ли размер порций?","type":"radio","opts":["Да, слежу за порциями","Нет, ем сколько хочется","Иногда","Склонен к перееданию"]},
    {"id":34,"block":3,"bt":"Режим питания","text":"Когда чаще испытываете сильный голод?","type":"radio","opts":["Утром","В обед","Вечером","Ночью","Равномерно в течение дня","Редко испытываю голод"]},
    # Блок 4 — Пищевые предпочтения (12)
    {"id":35,"block":4,"bt":"Пищевые предпочтения","text":"Предпочитаемая кухня","type":"radio","opts":["Русская / домашняя","Азиатская (суши, лапша, рис)","Средиземноморская","Европейская","Нет особых предпочтений"]},
    {"id":36,"block":4,"bt":"Пищевые предпочтения","text":"Ваш тип питания","type":"radio","opts":["Всеядный (ем всё)","Не ем свинину","Не ем красное мясо","Вегетарианец (без мяса)","Веган (без животных продуктов)","Пескетарианец (рыба, без мяса)"]},
    {"id":37,"block":4,"bt":"Пищевые предпочтения","text":"Есть ли непереносимость лактозы?","type":"radio","opts":["Нет","Да","Небольшая чувствительность","Не знаю"]},
    {"id":38,"block":4,"bt":"Пищевые предпочтения","text":"Есть ли непереносимость глютена?","type":"radio","opts":["Нет","Да, целиакия","Чувствительность к глютену","Не знаю"]},
    {"id":39,"block":4,"bt":"Пищевые предпочтения","text":"Есть ли пищевая аллергия?","type":"radio","opts":["Нет","Орехи","Морепродукты / рыба","Яйца","Цитрусовые","Другое"]},
    {"id":40,"block":4,"bt":"Пищевые предпочтения","text":"Что точно не будете есть?","type":"radio","opts":["Субпродукты (печень, почки)","Рыба и морепродукты","Бобовые","Брокколи / шпинат и подобные","Острые блюда","Готов есть всё"]},
    {"id":41,"block":4,"bt":"Пищевые предпочтения","text":"Как относитесь к сладкому?","type":"radio","opts":["Не ем сладкое","Ем редко (несколько раз в месяц)","Ем умеренно (несколько раз в неделю)","Ем часто (каждый день)","Сладкое — моя главная слабость"]},
    {"id":42,"block":4,"bt":"Пищевые предпочтения","text":"Употребляете ли алкоголь?","type":"radio","opts":["Не пью совсем","Очень редко (праздники)","1–2 раза в месяц","1–2 раза в неделю","Несколько раз в неделю"]},
    {"id":43,"block":4,"bt":"Пищевые предпочтения","text":"Сколько чашек кофе в день?","type":"radio","opts":["Не пью кофе","1 чашка","2–3 чашки","4 и более"]},
    {"id":44,"block":4,"bt":"Пищевые предпочтения","text":"Как часто едите фастфуд?","type":"radio","opts":["Никогда","Редко (раз в месяц)","1–2 раза в неделю","Несколько раз в неделю","Практически каждый день"]},
    {"id":45,"block":4,"bt":"Пищевые предпочтения","text":"Как часто едите полуфабрикаты?","type":"radio","opts":["Никогда, только домашнее","Иногда (раз в неделю)","Часто (несколько раз в неделю)","Постоянно"]},
    {"id":46,"block":4,"bt":"Пищевые предпочтения","text":"Ваше отношение к острой пище","type":"radio","opts":["Люблю острое","Умеренно острое — нормально","Предпочитаю неострое","Совсем не ем острое"]},
    # Блок 5 — Вода и напитки (5)
    {"id":47,"block":5,"bt":"Вода и напитки","text":"Сколько литров воды в день?","type":"radio","opts":["Менее 0.5 л","0.5–1 л","1–1.5 л","1.5–2 л","Более 2 л"]},
    {"id":48,"block":5,"bt":"Вода и напитки","text":"Пьёте ли сладкую газировку / покупные соки?","type":"radio","opts":["Нет","Редко","Иногда","Каждый день"]},
    {"id":49,"block":5,"bt":"Вода и напитки","text":"Как напоминаете себе пить воду?","type":"radio","opts":["Не напоминаю — пью когда хочу","Ставлю таймер","Пользуюсь приложением","Всегда ношу бутылку с собой"]},
    {"id":50,"block":5,"bt":"Вода и напитки","text":"Часто ощущаете жажду?","type":"radio","opts":["Да, часто","Редко","Почти никогда"]},
    {"id":51,"block":5,"bt":"Вода и напитки","text":"Употребляете ли энергетики?","type":"radio","opts":["Нет","Редко","Несколько раз в неделю","Регулярно"]},
    # Блок 6 — Здоровье и самочувствие (10)
    {"id":52,"block":6,"bt":"Здоровье и самочувствие","text":"Есть ли хронические заболевания?","type":"radio","opts":["Нет","Сахарный диабет","Гипертония","Проблемы с щитовидной железой","Заболевания ЖКТ (гастрит, язва)","Сердечно-сосудистые","Несколько заболеваний"]},
    {"id":53,"block":6,"bt":"Здоровье и самочувствие","text":"Принимаете ли постоянные лекарства?","type":"radio","opts":["Нет","Да (гормональные)","Да (сердечно-сосудистые)","Да (другие)"]},
    {"id":54,"block":6,"bt":"Здоровье и самочувствие","text":"Принимаете ли витамины / добавки?","type":"radio","opts":["Нет","Витаминный комплекс","Витамин D","Омега-3","Протеин / спортпит","Несколько добавок"]},
    {"id":55,"block":6,"bt":"Здоровье и самочувствие","text":"Как обычно чувствуете себя после еды?","type":"radio","opts":["Хорошо, легко","Тяжесть в желудке","Вздутие","Сонливость","Изжога","По-разному"]},
    {"id":56,"block":6,"bt":"Здоровье и самочувствие","text":"Есть ли проблемы с пищеварением?","type":"radio","opts":["Нет","Запоры","Диарея / нестабильный стул","Изжога / кислотный рефлюкс","Вздутие / газообразование","Несколько проблем"]},
    {"id":57,"block":6,"bt":"Здоровье и самочувствие","text":"Уровень энергии в течение дня","type":"radio","opts":["Стабильно высокий","Высокий утром, падает к обеду","Низкий утром, растёт к вечеру","Постоянно низкий","Резко скачет"]},
    {"id":58,"block":6,"bt":"Здоровье и самочувствие","text":"Уровень сахара в крови","type":"radio","opts":["В норме (проверял)","Повышен / диабет","Пониженный / гипогликемия","Не знаю, не проверял"]},
    {"id":59,"block":6,"bt":"Здоровье и самочувствие","text":"Уровень холестерина","type":"radio","opts":["В норме","Повышен","Не знаю"]},
    {"id":60,"block":6,"bt":"Здоровье и самочувствие","text":"Было ли резкое изменение веса за последний год?","type":"radio","opts":["Нет, вес стабильный","Сильно похудел без причины","Сильно набрал вес","Вес постоянно колеблется"]},
    {"id":61,"block":6,"bt":"Здоровье и самочувствие","text":"Есть ли гормональные нарушения (диагностированные)?","type":"radio","opts":["Нет","Да (щитовидная железа)","Да (СПКЯ / половые гормоны)","Не знаю"]},
    # Блок 7 — Сон и стресс (8)
    {"id":62,"block":7,"bt":"Сон и стресс","text":"Сколько часов спите в сутки?","type":"radio","opts":["Менее 5 часов","5–6 часов","7–8 часов","9 и более","Нерегулярно"]},
    {"id":63,"block":7,"bt":"Сон и стресс","text":"Качество сна","type":"radio","opts":["Отличное (всегда высыпаюсь)","Хорошее (обычно нормально)","Среднее (бывают проблемы)","Плохое (часто бессонница)"]},
    {"id":64,"block":7,"bt":"Сон и стресс","text":"Просыпаетесь ли ночью?","type":"radio","opts":["Нет, сплю без перерывов","Редко","Часто (1–2 раза)","Постоянно просыпаюсь"]},
    {"id":65,"block":7,"bt":"Сон и стресс","text":"Уровень стресса в жизни","type":"radio","opts":["Низкий (жизнь спокойная)","Умеренный","Высокий (постоянно в напряжении)","Очень высокий (хронический стресс)"]},
    {"id":66,"block":7,"bt":"Сон и стресс","text":"Как справляетесь со стрессом?","type":"radio","opts":["Еда / переедание","Спорт / прогулки","Общение с близкими","Медитация / дыхание","Алкоголь / курение","Никак — накапливается"]},
    {"id":67,"block":7,"bt":"Сон и стресс","text":"Чувствуете ли эмоциональное выгорание?","type":"radio","opts":["Нет","Иногда","Да, часто","Да, постоянно"]},
    {"id":68,"block":7,"bt":"Сон и стресс","text":"Бывают ли депрессивные состояния или апатия?","type":"radio","opts":["Нет","Редко","Иногда","Часто","Да, наблюдаюсь у специалиста"]},
    {"id":69,"block":7,"bt":"Сон и стресс","text":"Есть ли чёткий режим дня?","type":"radio","opts":["Да, строгий распорядок","Примерно да","Нет, каждый день по-разному","Совсем нет режима"]},
    # Блок 8 — Готовка и быт (6)
    {"id":70,"block":8,"bt":"Готовка и быт","text":"Готовите ли дома?","type":"radio","opts":["Да, всегда готовлю сам","Иногда (3–4 раза в неделю)","Редко (1–2 раза в неделю)","Нет, практически не готовлю"]},
    {"id":71,"block":8,"bt":"Готовка и быт","text":"Сколько времени готовы тратить на готовку в день?","type":"radio","opts":["До 15 минут","15–30 минут","30–60 минут","Более часа — люблю готовить"]},
    {"id":72,"block":8,"bt":"Готовка и быт","text":"Как часто едите в кафе / ресторанах?","type":"radio","opts":["Никогда / крайне редко","1–2 раза в месяц","Несколько раз в неделю","Практически каждый день"]},
    {"id":73,"block":8,"bt":"Готовка и быт","text":"Бюджет на питание в месяц","type":"radio","opts":["До 5 000 ₽","5 000–10 000 ₽","10 000–20 000 ₽","Более 20 000 ₽","Без ограничений"]},
    {"id":74,"block":8,"bt":"Готовка и быт","text":"Готовите ли для семьи (не только для себя)?","type":"radio","opts":["Да, для всей семьи","Да, для 1–2 человек","Нет, только для себя"]},
    {"id":75,"block":8,"bt":"Готовка и быт","text":"Есть ли поддержка в изменении питания?","type":"radio","opts":["Да, активно поддерживают","Да, нейтрально","Нет, окружение не поддерживает","Меняю питание для себя"]},
    # Блок 9 — Мотивация и настрой (2)
    {"id":76,"block":9,"bt":"Мотивация и настрой","text":"Главная мотивация изменить питание","type":"radio","opts":["Улучшить здоровье и самочувствие","Улучшить внешний вид и форму","Повысить уровень энергии","Рекомендация врача","Пример для семьи / детей","Несколько мотивов"]},
    {"id":77,"block":9,"bt":"Мотивация и настрой","text":"Какой подход к изменениям вам ближе?","type":"radio","opts":["Хочу быстрый результат (интенсивный старт)","Готов к постепенным изменениям без срывов","Нужна жёсткая система с правилами","Хочу гибкий план без строгих ограничений"]},
]

# ── DB helpers ────────────────────────────────────────────────────────────────

def db():
    return psycopg2.connect(DB_DSN)

# ── Auth helpers ──────────────────────────────────────────────────────────────

def normalize_phone(phone):
    digits = re.sub(r'\D', '', str(phone))
    if digits.startswith('8') and len(digits) == 11:
        digits = '7' + digits[1:]
    elif len(digits) == 10:
        digits = '7' + digits
    return digits if len(digits) == 11 else None

def hash_pw(pw):
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()

def check_pw(pw, hashed):
    return bcrypt.checkpw(pw.encode(), hashed.encode())

# ── Claude generation ─────────────────────────────────────────────────────────

def generate_diet_plan(answers_dict):
    from anthropic import Anthropic
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    lines = []
    for q in QUESTIONS:
        val = answers_dict.get(str(q['id']), '—')
        unit = q.get('unit', '')
        lines.append(f"{q['id']}. {q['text']}: {val}{' ' + unit if unit else ''}")
    questionnaire_text = '\n'.join(lines)

    prompt = f"""Ты профессиональный диетолог и нутрициолог с 20-летним опытом. Проанализируй анкету пользователя и составь персональный план питания.

АНКЕТА ПОЛЬЗОВАТЕЛЯ:
{questionnaire_text}

Верни ТОЛЬКО валидный JSON без markdown-блоков и комментариев. Строгая структура:
{{
  "parameters": {{
    "bmi": <число с 1 знаком после запятой>,
    "bmi_category": "<Дефицит веса / Нормальный вес / Избыточный вес / Ожирение I степени / Ожирение II степени>",
    "tdee": <целое число ккал/день>,
    "recommended_calories": <целое число ккал/день>,
    "protein_g": <целое число г/день>,
    "fat_g": <целое число г/день>,
    "carbs_g": <целое число г/день>,
    "water_l": <число с 1 знаком л/день>
  }},
  "conclusion": "<3–4 предложения: анализ текущего состояния, ключевые факторы, потенциал для улучшения>",
  "diet_name": "<название рекомендуемой диеты>",
  "diet_why": "<2–3 предложения — почему именно эта диета подходит данному человеку с учётом его особенностей>",
  "diet_principles": ["<принцип 1>", "<принцип 2>", "<принцип 3>", "<принцип 4>", "<принцип 5>"],
  "meal_plan": [
    {{"day": "Понедельник", "breakfast": "<блюдо с примерным весом>", "lunch": "<блюдо>", "dinner": "<блюдо>", "snack": "<перекус>"}},
    {{"day": "Вторник", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}},
    {{"day": "Среда", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}},
    {{"day": "Четверг", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}},
    {{"day": "Пятница", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}},
    {{"day": "Суббота", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}},
    {{"day": "Воскресенье", "breakfast": "...", "lunch": "...", "dinner": "...", "snack": "..."}}
  ],
  "recipes": [
    {{
      "name": "<название>",
      "time": "<X мин>",
      "calories": "<~XXX ккал на порцию>",
      "ingredients": ["<ингредиент 1 с количеством>", "<ингредиент 2>", "<ингредиент 3>", "<ингредиент 4>", "<ингредиент 5>"],
      "steps": "<приготовление в 3–4 предложения>"
    }},
    {{"name": "...", "time": "...", "calories": "...", "ingredients": [...], "steps": "..."}},
    {{"name": "...", "time": "...", "calories": "...", "ingredients": [...], "steps": "..."}},
    {{"name": "...", "time": "...", "calories": "...", "ingredients": [...], "steps": "..."}},
    {{"name": "...", "time": "...", "calories": "...", "ingredients": [...], "steps": "..."}}
  ],
  "rules": ["<правило 1>", "<правило 2>", "<правило 3>", "<правило 4>", "<правило 5>", "<правило 6>", "<правило 7>", "<правило 8>", "<правило 9>", "<правило 10>"],
  "eat_more": ["<продукт 1>", "<продукт 2>", "<продукт 3>", "<продукт 4>", "<продукт 5>", "<продукт 6>", "<продукт 7>", "<продукт 8>"],
  "avoid": ["<продукт 1>", "<продукт 2>", "<продукт 3>", "<продукт 4>", "<продукт 5>", "<продукт 6>", "<продукт 7>", "<продукт 8>"],
  "motivation": "<3–4 предложения персонального мотивирующего послания с учётом цели, образа жизни и сильных сторон человека>"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )
    text = msg.content[0].text.strip()
    text = re.sub(r'^```[a-z]*\n?', '', text)
    text = re.sub(r'\n?```$', '', text)
    return json.loads(text)

# ── Auth middleware ───────────────────────────────────────────────────────────

@app.before_request
def auth_guard():
    public = {'/', '/api/register', '/api/login', '/api/spots'}
    if request.path not in public and not session.get('uid'):
        if request.path.startswith('/api/'):
            return jsonify({'error': 'unauthorized'}), 401

# ── Routes ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return Response(HTML, mimetype='text/html')

@app.route('/api/register', methods=['POST'])
def register():
    d = request.json or {}
    phone = normalize_phone(d.get('phone', ''))
    pw = d.get('password', '').strip()
    if not phone:
        return jsonify({'error': 'Неверный формат номера телефона'}), 400
    if len(pw) < 6:
        return jsonify({'error': 'Пароль минимум 6 символов'}), 400
    try:
        with db() as con:
            with con.cursor() as cur:
                cur.execute(
                    'INSERT INTO diet_users (phone, password_hash) VALUES (%s, %s) RETURNING id',
                    (phone, hash_pw(pw))
                )
                uid = cur.fetchone()[0]
        session['uid'] = uid
        return jsonify({'ok': True})
    except psycopg2.errors.UniqueViolation:
        return jsonify({'error': 'Этот номер уже зарегистрирован'}), 400

@app.route('/api/login', methods=['POST'])
def login():
    d = request.json or {}
    phone = normalize_phone(d.get('phone', ''))
    pw = d.get('password', '').strip()
    if not phone:
        return jsonify({'error': 'Неверный формат номера'}), 400
    with db() as con:
        with con.cursor() as cur:
            cur.execute('SELECT id, password_hash FROM diet_users WHERE phone = %s', (phone,))
            row = cur.fetchone()
    if not row or not check_pw(pw, row[1]):
        return jsonify({'error': 'Неверный номер или пароль'}), 403
    session['uid'] = row[0]
    return jsonify({'ok': True})

@app.route('/api/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    uid = session.get('uid')
    if not uid:
        return jsonify({'logged_in': False})
    with db() as con:
        with con.cursor() as cur:
            cur.execute('SELECT 1 FROM diet_answers WHERE user_id = %s', (uid,))
            has_answers = bool(cur.fetchone())
            cur.execute('SELECT result FROM diet_results WHERE user_id = %s', (uid,))
            row = cur.fetchone()
            result = row[0] if row else None
    return jsonify({'logged_in': True, 'has_answers': has_answers, 'result': result})

@app.route('/api/answers', methods=['POST'])
def save_answers():
    uid = session.get('uid')
    answers = request.json or {}
    if len(answers) < 70:
        return jsonify({'error': 'Заполните все вопросы'}), 400
    with db() as con:
        with con.cursor() as cur:
            cur.execute("""
                INSERT INTO diet_answers (user_id, answers) VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET answers = EXCLUDED.answers, created_at = NOW()
            """, (uid, json.dumps(answers)))
    return jsonify({'ok': True})

@app.route('/api/generate', methods=['POST'])
def generate():
    uid = session.get('uid')
    if not ANTHROPIC_API_KEY:
        return jsonify({'error': 'API ключ не настроен. Установите ANTHROPIC_API_KEY.'}), 500
    with db() as con:
        with con.cursor() as cur:
            cur.execute('SELECT answers FROM diet_answers WHERE user_id = %s', (uid,))
            row = cur.fetchone()
    if not row:
        return jsonify({'error': 'Сначала заполните анкету'}), 400
    try:
        result = generate_diet_plan(row[0])
        with db() as con:
            with con.cursor() as cur:
                cur.execute("""
                    INSERT INTO diet_results (user_id, result) VALUES (%s, %s)
                    ON CONFLICT (user_id) DO UPDATE SET result = EXCLUDED.result, created_at = NOW()
                """, (uid, json.dumps(result)))
        return jsonify({'ok': True, 'result': result})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/spots')
def spots():
    with db() as con:
        with con.cursor() as cur:
            cur.execute('SELECT COUNT(*) FROM diet_users')
            taken = cur.fetchone()[0]
    free = max(0, 20 - taken)
    return jsonify({'taken': taken, 'free': free, 'total': 20})

# ── HTML ──────────────────────────────────────────────────────────────────────

HTML = r"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Бесплатный марафон похудения — первые 20 человек бесплатно | Slimfy</title>
<meta name="description" content="2-месячный марафон по снижению веса. Первые 20 участников — бесплатно. Индивидуальный план питания с КБЖУ, рекомендации диетолога, еженедельная корректировка, поддержка.">
<meta name="keywords" content="марафон похудения, снижение веса бесплатно, план питания, диетолог онлайн, КБЖУ, похудеть">
<meta name="robots" content="index, follow">
<link rel="canonical" href="https://slimfy.ru/">
<meta property="og:type" content="website">
<meta property="og:url" content="https://slimfy.ru/">
<meta property="og:title" content="Бесплатный марафон похудения — первые 20 человек бесплатно">
<meta property="og:description" content="2-месячный марафон по снижению веса. Первые 20 участников — бесплатно. Индивидуальный план питания, рекомендации диетолога, поддержка.">
<meta property="og:site_name" content="Slimfy">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Бесплатный марафон похудения — первые 20 человек бесплатно">
<meta name="twitter:description" content="2-месячный марафон по снижению веса. Первые 20 участников бесплатно. Индивидуальный план питания с КБЖУ.">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebApplication","name":"Марафон похудения","description":"Бесплатный 2-месячный марафон по снижению веса. Первые 20 участников бесплатно. Индивидуальный план питания с КБЖУ, рекомендации диетолога.","url":"https://slimfy.ru/","applicationCategory":"HealthApplication","operatingSystem":"All","offers":{"@type":"Offer","price":"0","priceCurrency":"RUB"},"inLanguage":"ru","author":{"@type":"Organization","name":"Slimfy","url":"https://slimfy.ru"}}</script>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
:root{
  --bg:#f4fbf6;--card:#fff;--border:#deeee5;--border2:#c8e0d0;
  --primary:#1a7d3e;--primary-h:#156632;--primary-l:#e6f4ec;
  --text:#111827;--muted:#6b7280;--danger:#dc2626;--warn:#d97706;
  --r:14px;--rs:9px;
  --shadow:0 2px 12px rgba(0,0,0,.07);--shadow-lg:0 8px 40px rgba(0,0,0,.12)
}
body{background:var(--bg);color:var(--text);font-family:'Segoe UI',system-ui,sans-serif;font-size:19px;line-height:1.65}
a{color:inherit;text-decoration:none}
button{font-family:inherit;cursor:pointer}

/* ── Nav ── */
nav{position:fixed;top:0;left:0;right:0;z-index:200;background:rgba(255,255,255,.92);
  backdrop-filter:blur(12px);border-bottom:1px solid var(--border);
  display:flex;align-items:center;justify-content:space-between;padding:0 32px;height:60px}
.nav-logo{font-size:18px;font-weight:800;color:var(--primary);display:flex;align-items:center;gap:8px}
.nav-logo span{font-size:22px}
.nav-r{display:flex;gap:10px}

/* ── Buttons ── */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;
  padding:10px 22px;border-radius:var(--rs);font-size:14px;font-weight:600;
  border:none;transition:all .18s;white-space:nowrap}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn:active:not(:disabled){transform:scale(.97)}
.btn-p{background:var(--primary);color:#fff;box-shadow:0 3px 12px rgba(26,125,62,.3)}
.btn-p:hover:not(:disabled){background:var(--primary-h)}
.btn-o{background:transparent;color:var(--primary);border:1.5px solid var(--primary)}
.btn-o:hover{background:var(--primary-l)}
.btn-g{background:#f3f4f6;color:var(--text);border:1px solid var(--border2)}
.btn-g:hover{background:#e9ebec}
.btn-lg{padding:14px 32px;font-size:16px;border-radius:12px}
.btn-full{width:100%}

/* ── Sections ── */
section{display:none!important}
section.active{display:block!important}

/* Hallmark · genre: editorial · macrostructure: Narrative Workflow · theme: Garden · enrichment: none (typography + numeral marks) · nav: N6 · footer: Ft6 */
/* ═══ GARDEN — MARATHON LANDING (Narrative Workflow) ═══ */
#landing{
  --paper:oklch(97% 0.014 145);--paper-2:oklch(93% 0.02 148);
  --ink:oklch(21% 0.02 155);
  --accent:oklch(54% 0.14 152);--accent-deep:oklch(37% 0.12 150);
  --rule:oklch(21% 0.02 155/.14);--focus:oklch(50% 0.15 152);
  --font-display:'Newsreader',Georgia,serif;--font-body:'IBM Plex Sans',system-ui,sans-serif;
  --font-label:'JetBrains Mono',ui-monospace,monospace;
  --radius:10px;--radius-lg:18px;
  --ease-out:cubic-bezier(.16,1,.3,1);
  --space-sm:.75rem;--space-md:1.25rem;--space-lg:2rem;--space-xl:3rem;--space-2xl:4.5rem;
  background:var(--paper);color:var(--ink);font-family:var(--font-body)
}
#landing *{font-family:inherit}
#landing .grd-shell{max-width:1080px;margin:0 auto;padding-inline:28px}

/* ── Nav: N6 Newspaper masthead ── */
.grd-nav{position:sticky;top:0;z-index:50;background:color-mix(in oklch,var(--paper) 92%,transparent);
  backdrop-filter:blur(8px);padding:18px 28px 0;text-align:center}
.grd-issue{font-family:var(--font-label);font-size:11px;font-weight:500;letter-spacing:.1em;
  text-transform:uppercase;opacity:.55;margin-bottom:6px}
.grd-word{font-family:var(--font-display);font-weight:600;font-size:clamp(22px,3vw,30px);letter-spacing:-.01em}
.grd-word b{color:var(--accent-deep);font-weight:600}
.grd-nav-links{display:flex;align-items:center;justify-content:center;gap:22px;margin-top:10px;min-height:22px}
.grd-navlink{background:none;border:0;font:inherit;font-weight:500;font-size:14px;color:var(--ink);cursor:pointer;
  padding:2px 0;border-bottom:1.5px solid transparent;transition:border-color .2s var(--ease-out)}
.grd-navlink:hover{border-color:var(--ink)}
.grd-navlink:focus-visible,.grd-tab:focus-visible{outline:2px solid var(--focus);outline-offset:3px;border-radius:4px}
.grd-rule{border:0;border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);height:4px;margin:14px 0 0}

/* ── Primary button ── */
.grd-btn{display:inline-flex;align-items:center;justify-content:center;gap:.6em;white-space:nowrap;
  padding:15px 30px;font-weight:600;font-size:16px;font-family:var(--font-body);border:0;border-radius:var(--radius);
  cursor:pointer;color:var(--paper);background:var(--ink);
  box-shadow:0 1px 0 0 var(--rule),0 10px 24px -12px oklch(21% .02 155/.45);
  transition:transform 200ms var(--ease-out),box-shadow 200ms var(--ease-out),background-color 200ms var(--ease-out)}
.grd-btn:hover{transform:translateY(-2px);background:var(--accent-deep);box-shadow:0 14px 28px -12px oklch(21% .02 155/.45)}
.grd-btn:active{transform:translateY(0)}
.grd-btn:focus-visible{outline:2px solid var(--focus);outline-offset:3px}
.grd-arrow{transition:transform 200ms var(--ease-out)}
.grd-btn:hover .grd-arrow{transform:translateX(3px)}

/* ── Hero ── */
.grd-hero{padding:64px 28px 76px;max-width:640px;margin:0 auto}
.grd-kicker{font-family:var(--font-label);font-size:12px;font-weight:500;letter-spacing:.08em;
  text-transform:uppercase;opacity:.6;margin-bottom:22px}
.grd-hero h1{font-family:var(--font-display);font-weight:600;letter-spacing:-.01em;line-height:1.12;
  font-size:clamp(34px,4.2vw + 8px,54px);margin-bottom:22px;overflow-wrap:anywhere;min-width:0}
.grd-lede{font-size:17px;line-height:1.65;opacity:.75;max-width:46ch;margin-bottom:34px}
.grd-cta-row{display:flex;flex-wrap:wrap;align-items:center;gap:20px}
.grd-cta-note{font-size:13.5px;opacity:.62;font-weight:500}
.grd-cta-note strong{color:var(--accent-deep);font-weight:700}

/* ── Stage sequence (Narrative Workflow) ── */
.grd-stage{padding:var(--space-2xl) 28px;border-top:1px solid var(--rule)}
.grd-stage--tint{background:var(--paper-2)}
.grd-stage-inner{max-width:640px;margin:0 auto}
.grd-stage-num{font-family:var(--font-display);font-weight:600;font-size:clamp(40px,6vw,64px);line-height:1;
  color:var(--accent);opacity:.85;margin-bottom:14px;font-variant-numeric:tabular-nums}
.grd-stage h2{font-family:var(--font-display);font-weight:600;letter-spacing:-.01em;
  font-size:clamp(24px,2.6vw + 6px,32px);margin-bottom:14px;max-width:28ch;overflow-wrap:anywhere}
.grd-stage p{font-size:15.5px;line-height:1.65;opacity:.75;max-width:56ch}
.grd-tags{display:flex;flex-wrap:wrap;gap:8px;margin-top:20px}
.grd-tags span{font-family:var(--font-label);font-size:11px;font-weight:500;letter-spacing:.03em;
  text-transform:uppercase;border:1px solid var(--rule);color:var(--ink);opacity:.72;padding:5px 12px;border-radius:999px}

/* ── FAQ ── */
.grd-band{padding:var(--space-2xl) 28px}
.grd-h2{font-family:var(--font-display);font-weight:600;letter-spacing:-.01em;
  font-size:clamp(26px,3vw + 6px,36px);margin-bottom:36px;max-width:28ch}
.grd-faq{max-width:720px;margin:0 auto;border-top:1px solid var(--rule)}
.grd-faq-item{padding:26px 0;border-bottom:1px solid var(--rule)}
.grd-faq-item dt{font-family:var(--font-display);font-weight:600;font-size:18px;margin-bottom:10px}
.grd-faq-item dd{font-size:15px;line-height:1.65;opacity:.75;max-width:60ch}

/* ── Registration ── */
.grd-reg{padding:var(--space-2xl) 28px;display:flex;flex-direction:column;align-items:center;
  background:var(--ink);color:var(--paper)}
.grd-reg-h{text-align:center;margin-bottom:36px}
.grd-reg .grd-h2{margin:0 0 10px;max-width:none;color:var(--paper)}
.grd-reg-sub{font-size:15px;opacity:.65}
.grd-card{background:var(--paper);border-radius:var(--radius-lg);padding:32px 30px;width:100%;max-width:400px;
  box-shadow:0 28px 56px -24px oklch(21% .02 155/.4)}
.grd-tabs{display:flex;gap:24px;margin-bottom:26px;border-bottom:1px solid var(--rule)}
.grd-tab{padding:0 0 12px;font-size:14.5px;font-weight:600;cursor:pointer;color:var(--ink);opacity:.45;
  border:none;background:none;font-family:inherit;border-bottom:2px solid transparent;margin-bottom:-1px;
  transition:all .2s var(--ease-out)}
.grd-tab.on{opacity:1;border-color:var(--accent-deep)}
#landing .grd-card .fg{margin-bottom:16px}
#landing .grd-card label{opacity:.55;font-size:11px;font-weight:600;color:var(--ink);
  text-transform:uppercase;letter-spacing:.06em;margin-bottom:7px}
#landing .grd-card input{width:100%;background:var(--paper-2);border:1.5px solid transparent;color:var(--ink);
  border-radius:var(--radius);padding:13px 14px;font-size:15px;outline:none;font-family:inherit;
  transition:all .2s var(--ease-out)}
#landing .grd-card input::placeholder{color:var(--ink);opacity:.32}
#landing .grd-card input:focus{border-color:var(--accent-deep)!important;background:var(--paper)!important;
  box-shadow:0 0 0 3px oklch(54% .14 152/.16)!important}
.grd-submit{width:100%;background:var(--accent-deep);color:var(--paper);border:none;border-radius:var(--radius);
  padding:14px 16px;font-size:15px;font-weight:600;font-family:inherit;cursor:pointer;margin-top:8px;
  box-shadow:0 1px 0 0 oklch(30% .11 150),0 10px 22px -10px oklch(37% .12 150/.55);
  transition:transform 200ms var(--ease-out),box-shadow 200ms var(--ease-out),background-color 200ms var(--ease-out)}
.grd-submit:hover:not(:disabled){transform:translateY(-2px);background:oklch(32% .12 150)}
.grd-submit:active:not(:disabled){transform:translateY(0)}
.grd-submit:disabled{opacity:.5;cursor:not-allowed}
.grd-card .err-msg{background:oklch(54% .14 152/.1)!important;border-color:transparent!important;
  color:var(--accent-deep)!important;font-size:13px;border-radius:var(--radius);margin-top:10px}
.grd-reg-foot{margin-top:24px;font-family:var(--font-label);font-size:12px;letter-spacing:.03em;opacity:.55}

/* ── Footer: Ft6 Letter close ── */
.grd-footer{background:var(--ink);color:var(--paper);padding:var(--space-2xl) 28px}
.grd-footer-inner{max-width:60ch;margin:0 auto}
.grd-footer-close{font-family:var(--font-display);font-style:italic;font-size:20px;line-height:1.5}
.grd-footer-sign{font-style:normal;font-weight:600;color:var(--paper)}
.grd-footer-ps{font-size:13px;margin-top:16px;opacity:.6}
.grd-footer-ps strong{color:var(--paper);opacity:1}

/* ── Reveal: sweep horizontal (drives existing IntersectionObserver) ── */
.ms-reveal{opacity:0;transform:translateX(-14px);transition:opacity .6s var(--ease-out),transform .6s var(--ease-out)}
.ms-reveal.visible{opacity:1;transform:none}

@media (prefers-reduced-motion: reduce){
  .grd-btn,.grd-submit,.ms-reveal{transition:opacity .15s,background-color .15s!important;transform:none!important}
  .grd-btn:hover,.grd-submit:hover{transform:none!important}
}

/* ── Mobile ── */
@media(max-width:760px){
  .grd-hero{padding:44px 20px 56px}
  .grd-stage{padding:var(--space-xl) 20px}
  .grd-band{padding:var(--space-xl) 20px}
}
@media(max-width:640px){
  .grd-nav{padding:16px 20px 0}
  .grd-nav-links{gap:14px}
  .grd-reg{padding:var(--space-xl) 20px}
  .grd-stage-num{font-size:40px}
}



/* ── Questionnaire: block headers & submit ── */
.q-block-section{margin-bottom:48px}
.q-block-header{display:flex;align-items:center;gap:12px;margin-bottom:24px;
  padding:16px 22px;background:linear-gradient(135deg,var(--primary-l),#f0fdf4);
  border-radius:14px;border-left:4px solid var(--primary);position:sticky;top:60px;z-index:10}
.q-block-title-h{font-size:18px;font-weight:800;color:#0f172a}
.q-submit-wrap{text-align:center;padding:48px 0 32px;border-top:2px solid var(--border);margin-top:16px}
.q-submit-wrap .btn{font-size:19px;padding:16px 48px}


.fg{margin-bottom:14px}
label{display:block;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:.4px;
  color:var(--muted);margin-bottom:6px}
input[type=text],input[type=tel],input[type=password],input[type=number]{
  width:100%;background:#f9fafb;border:1.5px solid var(--border2);border-radius:var(--rs);
  padding:11px 14px;color:var(--text);font-size:15px;outline:none;transition:border-color .15s,box-shadow .15s;
  font-family:inherit}
input:focus{border-color:var(--primary);box-shadow:0 0 0 3px rgba(26,125,62,.12);background:#fff}
.err-msg{background:#fef2f2;border:1px solid #fecaca;color:var(--danger);
  padding:10px 14px;border-radius:var(--rs);font-size:13px;margin-top:12px;display:none}
.err-msg.on{display:block}

/* ── Questionnaire ── */
#questionnaire{background:var(--bg)}
.q-header{background:var(--card);border-bottom:1px solid var(--border);padding:20px 24px}
.q-header-inner{max-width:720px;margin:0 auto}
.q-progress-wrap{display:flex;align-items:center;gap:14px;margin-bottom:8px}
.q-progress-bar{flex:1;height:8px;background:#e5e7eb;border-radius:4px;overflow:hidden}
.q-progress-fill{height:100%;background:var(--primary);border-radius:4px;transition:width .4s ease}
.q-progress-text{font-size:13px;color:var(--muted);white-space:nowrap;font-weight:600}
.q-block-info{display:flex;align-items:center;gap:10px}
.q-block-num{background:var(--primary);color:#fff;border-radius:6px;padding:2px 10px;
  font-size:12px;font-weight:700}
.q-block-title{font-size:15px;font-weight:700}
.q-body{max-width:720px;margin:0 auto;padding:32px 24px}
.q-list{display:flex;flex-direction:column;gap:20px;margin-bottom:32px}
.q-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:24px;box-shadow:var(--shadow)}
.q-card.error{border-color:#fca5a5;box-shadow:0 0 0 3px rgba(220,38,38,.08)}
.q-num{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;margin-bottom:8px}
.q-text{font-size:16px;font-weight:600;margin-bottom:16px}
.q-opts{display:flex;flex-direction:column;gap:8px}
.q-opt{display:flex;align-items:center;gap:12px;padding:10px 14px;border:1.5px solid var(--border2);
  border-radius:var(--rs);cursor:pointer;transition:all .15s;font-size:14px}
.q-opt:hover{border-color:var(--primary);background:var(--primary-l)}
.q-opt.selected{border-color:var(--primary);background:var(--primary-l);color:var(--primary);font-weight:600}
.q-opt input[type=radio]{accent-color:var(--primary);width:16px;height:16px;flex-shrink:0}
.q-num-wrap{display:flex;align-items:center;gap:12px}
.q-num-inp{width:120px;font-size:18px;font-weight:700;text-align:center}
.q-unit{color:var(--muted);font-size:15px}
.q-nav{display:flex;gap:12px;justify-content:space-between;align-items:center}
.q-err-banner{background:#fef2f2;border:1px solid #fecaca;color:var(--danger);
  padding:12px 16px;border-radius:var(--rs);font-size:14px;margin-bottom:16px;display:none}
.q-err-banner.on{display:block}

/* ── Generating ── */
#generating{background:linear-gradient(160deg,#e8f5ee,#f4fbf6)}
.gen-center{min-height:100%;display:flex;align-items:center;justify-content:center;padding:32px 24px}
.gen-card{background:var(--card);border-radius:20px;padding:56px 40px;text-align:center;
  max-width:440px;box-shadow:var(--shadow-lg)}
.gen-icon{font-size:56px;margin-bottom:24px;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{transform:scale(1)}50%{transform:scale(1.1)}}
.gen-title{font-size:24px;font-weight:800;margin-bottom:12px}
.gen-sub{color:var(--muted);font-size:15px;margin-bottom:32px}
.gen-steps{text-align:left;display:flex;flex-direction:column;gap:10px}
.gen-step{display:flex;align-items:center;gap:12px;font-size:14px;color:var(--muted)}
.gen-step.done{color:var(--primary);font-weight:600}
.gen-step.active{color:var(--text);font-weight:600}
.gen-dot{width:10px;height:10px;border-radius:50%;background:#d1d5db;flex-shrink:0}
.gen-step.done .gen-dot{background:var(--primary)}
.gen-step.active .gen-dot{background:var(--warn);animation:blink .8s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.3}}

/* ── Results ── */
#result{padding-top:60px}
.result-nav{background:var(--card);border-bottom:1px solid var(--border);
  padding:16px 24px;display:flex;align-items:center;justify-content:space-between}
.result-nav-title{font-size:17px;font-weight:800;color:var(--primary)}
.result-body{max-width:900px;margin:0 auto;padding:32px 24px}
.r-section{margin-bottom:32px}
.r-section-title{font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.6px;
  color:var(--muted);margin-bottom:16px;display:flex;align-items:center;gap:8px}
.r-section-title::after{content:'';flex:1;height:1px;background:var(--border)}

/* Params */
.params-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px}
.param-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:18px 16px;text-align:center;box-shadow:var(--shadow)}
.param-val{font-size:26px;font-weight:800;color:var(--primary);line-height:1.1}
.param-unit{font-size:12px;color:var(--muted);margin-top:2px}
.param-label{font-size:12px;color:var(--muted);margin-top:6px;font-weight:600;text-transform:uppercase;letter-spacing:.3px}
.bmi-card{background:linear-gradient(135deg,var(--primary),#2ecc71);color:#fff;border:none}
.bmi-card .param-val{color:#fff;font-size:32px}
.bmi-card .param-unit,.bmi-card .param-label{color:rgba(255,255,255,.8)}

/* Conclusion */
.conclusion-card{background:var(--card);border:1px solid var(--border);border-left:4px solid var(--primary);
  border-radius:var(--r);padding:24px;box-shadow:var(--shadow);font-size:15px;line-height:1.7;color:var(--text)}

/* Diet */
.diet-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:28px;box-shadow:var(--shadow)}
.diet-name{font-size:22px;font-weight:800;color:var(--primary);margin-bottom:10px}
.diet-why{color:var(--muted);font-size:14px;margin-bottom:20px;line-height:1.6}
.principles{display:flex;flex-direction:column;gap:8px}
.principle{display:flex;align-items:flex-start;gap:10px;font-size:14px}
.principle::before{content:'✓';color:var(--primary);font-weight:800;flex-shrink:0;margin-top:1px}

/* Meal plan */
.meal-table{width:100%;border-collapse:collapse;background:var(--card);border-radius:var(--r);
  overflow:hidden;box-shadow:var(--shadow);border:1px solid var(--border)}
.meal-table th{background:#f0f9f3;padding:10px 14px;font-size:12px;font-weight:700;
  text-transform:uppercase;letter-spacing:.5px;color:var(--primary);text-align:left;
  border-bottom:1px solid var(--border)}
.meal-table td{padding:12px 14px;font-size:13px;border-bottom:1px solid var(--border);vertical-align:top}
.meal-table tr:last-child td{border-bottom:none}
.meal-table tr:hover td{background:#f9fafb}
.meal-type{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;
  color:var(--muted);margin-bottom:3px}

/* Recipes */
.recipes-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.recipe-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:22px;box-shadow:var(--shadow)}
.recipe-name{font-size:16px;font-weight:700;margin-bottom:8px}
.recipe-meta{display:flex;gap:12px;margin-bottom:14px}
.recipe-tag{background:var(--primary-l);color:var(--primary);border-radius:6px;
  padding:3px 10px;font-size:12px;font-weight:600}
.recipe-ingr{font-size:13px;color:var(--muted);margin-bottom:12px}
.recipe-ingr ul{list-style:none;padding:0;margin-top:6px;display:flex;flex-direction:column;gap:3px}
.recipe-ingr li::before{content:'·  '}
.recipe-steps{font-size:13px;line-height:1.6;color:var(--text)}

/* Rules */
.rules-list{display:flex;flex-direction:column;gap:10px}
.rule-item{display:flex;align-items:flex-start;gap:14px;background:var(--card);
  border:1px solid var(--border);border-radius:var(--rs);padding:14px 16px;box-shadow:var(--shadow)}
.rule-n{background:var(--primary);color:#fff;border-radius:50%;width:26px;height:26px;
  display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:800;flex-shrink:0}
.rule-text{font-size:14px;line-height:1.5}

/* Foods */
.foods-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.foods-card{background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:22px;box-shadow:var(--shadow)}
.foods-card.eat h4{color:#16a34a}
.foods-card.avoid h4{color:#dc2626}
.foods-card h4{font-size:15px;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.foods-list{display:flex;flex-direction:column;gap:8px}
.food-item{display:flex;align-items:center;gap:10px;font-size:14px}
.food-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.eat .food-dot{background:#22c55e}
.avoid .food-dot{background:#ef4444}

/* Motivation */
.motivation-card{background:linear-gradient(135deg,var(--primary),#2ecc71);color:#fff;
  border-radius:var(--r);padding:32px;box-shadow:0 6px 28px rgba(26,125,62,.3);text-align:center}
.motivation-icon{font-size:40px;margin-bottom:16px}
.motivation-text{font-size:16px;line-height:1.7}

/* Spinner */
.spinner{display:inline-block;width:18px;height:18px;border:2.5px solid rgba(255,255,255,.3);
  border-top-color:#fff;border-radius:50%;animation:spin .7s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* Toast */
#toasts{position:fixed;bottom:22px;right:22px;z-index:9999;display:flex;flex-direction:column;gap:8px}
.toast{background:#1f2937;color:#fff;border-radius:var(--rs);padding:12px 18px;font-size:14px;
  font-weight:500;box-shadow:0 8px 28px rgba(0,0,0,.3);
  transform:translateX(120%);transition:transform .3s cubic-bezier(.34,1.56,.64,1);display:flex;align-items:center;gap:8px}
.toast.on{transform:none}

@media(max-width:640px){
  nav{padding:0 16px}
  .hero{padding:80px 16px 40px}
  .hero h1{font-size:32px}
  .features,.how-it-works,.cta-section{padding:56px 16px}
  .steps{flex-direction:column;align-items:center}
  .step:not(:last-child)::after{display:none}
  .modal{padding:24px 20px}
  .q-body{padding:20px 16px}
  .result-body{padding:20px 16px}
  .foods-grid{grid-template-columns:1fr}
  .meal-table{font-size:12px}
  .meal-table th,.meal-table td{padding:8px 10px}
  .recipes-grid{grid-template-columns:1fr}
  .params-grid{grid-template-columns:repeat(2,1fr)}
}

/* ══ LAYOUT ══ */
html,body{overflow:hidden;height:100%;margin:0}
#landing{position:fixed;inset:0;overflow-y:auto;-webkit-overflow-scrolling:touch}
section{position:fixed;inset:0;display:none}
section.active{display:block;overflow-y:auto;-webkit-overflow-scrolling:touch}

/* ═══ GLOBAL FONT CORRECTIONS ═══ */
.nav-logo{font-size:20px}.nav-logo span{font-size:26px}
.btn{font-size:16px!important}.btn-lg{font-size:18px!important}
.tab{font-size:16px}
label{font-size:14px}
input[type=text],input[type=tel],input[type=password],input[type=number]{font-size:17px;padding:13px 15px}
.err-msg{font-size:15px}
.q-progress-text{font-size:15px;font-weight:700}
.q-block-num{font-size:14px;padding:3px 12px}
.q-block-title{font-size:17px}
.q-num{font-size:13px}
.q-text{font-size:20px;line-height:1.45}
.q-opt{font-size:17px;padding:12px 16px}
.q-num-inp{font-size:22px}
.q-unit{font-size:18px}
.q-err-banner{font-size:16px}
.gen-title{font-size:30px}
.gen-sub{font-size:19px}
.gen-step{font-size:18px}
.result-nav-title{font-size:21px}
.r-section-title{font-size:16px}
.param-val{font-size:30px}
.param-unit{font-size:14px}
.param-label{font-size:14px}
.bmi-card .param-val{font-size:38px}
.conclusion-card{font-size:18px;line-height:1.75}
.diet-name{font-size:25px}
.diet-why{font-size:17px;line-height:1.7}
.principle{font-size:17px}
.meal-table th{font-size:14px;padding:12px 15px}
.meal-table td{font-size:15px;padding:13px 15px}
.meal-type{font-size:12px}
.recipe-name{font-size:20px}
.recipe-tag{font-size:14px;padding:4px 12px}
.recipe-ingr{font-size:16px}
.recipe-steps{font-size:16px;line-height:1.7}
.rule-n{font-size:14px;width:32px;height:32px;min-width:32px}
.rule-text{font-size:17px;line-height:1.6}
.foods-card h4{font-size:19px}
.food-item{font-size:17px}
.motivation-text{font-size:19px;line-height:1.8}
.toast{font-size:16px}
.modal-t{font-size:23px}
.modal-x{font-size:24px}
</style>
</head>
<body>

<div id="landing">
  <header class="grd-nav">
    <p class="grd-issue">Slimfy · Поток №1 · Регистрация открыта</p>
    <div class="grd-word">Slim<b>fy</b></div>
    <div class="grd-nav-links" role="navigation" aria-label="Основное">
      <button class="grd-navlink" onclick="document.getElementById('stage1').scrollIntoView({behavior:'smooth'})">Как это работает</button>
      <button class="grd-navlink" id="humLoginBtn" onclick="wTab('login');document.getElementById('msReg').scrollIntoView({behavior:'smooth'})">Войти</button>
      <div id="mldNavR"></div>
    </div>
    <hr class="grd-rule" aria-hidden="true">
  </header>

  <!-- ── HERO ── -->
  <div class="grd-hero">
    <p class="grd-kicker">Марафон снижения веса · бесплатно для первых 20</p>
    <h1>Похудеть за 30 дней — с планом, а не с силой воли.</h1>
    <p class="grd-lede">Личный план питания под ваш КБЖУ, тренировки под ваш уровень и куратор, который не даст сорваться.</p>
    <div class="grd-cta-row">
      <button class="grd-btn" id="humHeroCta" onclick="document.getElementById('msReg').scrollIntoView({behavior:'smooth'})">Участвовать бесплатно <span class="grd-arrow">→</span></button>
      <div class="grd-cta-note">Осталось <strong id="spotsLeft3">...</strong> из 20 мест</div>
    </div>
  </div>

  <!-- ── STAGE 1.0 — РЕГИСТРАЦИЯ ── -->
  <div class="grd-stage" id="stage1">
    <div class="grd-stage-inner ms-reveal">
      <div class="grd-stage-num">1.0</div>
      <h2>Займите место — их всего 20.</h2>
      <p>Вход по номеру телефона. Без карты и без подтверждений по почте.</p>
    </div>
  </div>

  <!-- ── STAGE 2.0 — АНКЕТА ── -->
  <div class="grd-stage grd-stage--tint">
    <div class="grd-stage-inner ms-reveal">
      <div class="grd-stage-num">2.0</div>
      <h2>Расскажите, кто вы.</h2>
      <p>77 вопросов о целях, образе жизни, тренировках и еде — про аллергии и непереносимости тоже спросим. Отвечаете один раз, план подстраивается под каждый ответ.</p>
    </div>
  </div>

  <!-- ── STAGE 3.0 — ПЛАН ── -->
  <div class="grd-stage">
    <div class="grd-stage-inner ms-reveal">
      <div class="grd-stage-num">3.0</div>
      <h2>ИИ собирает меню и КБЖУ.</h2>
      <p>Питание на каждый день — без продуктов, которые вы отметили как недопустимые, и без блюд, которые вы не будете готовить.</p>
    </div>
  </div>

  <!-- ── STAGE 4.0 — МАРАФОН ── -->
  <div class="grd-stage grd-stage--tint">
    <div class="grd-stage-inner ms-reveal">
      <div class="grd-stage-num">4.0</div>
      <h2>30 дней с куратором рядом.</h2>
      <p>Личный куратор следит за прогрессом и корректирует план, а чат участников — на связи всё время марафона.</p>
      <div class="grd-tags"><span>Завтрак</span><span>Обед</span><span>Ужин</span><span>Перекусы</span><span>КБЖУ каждый день</span><span>Тренировки</span><span>Чат поддержки</span></div>
    </div>
  </div>

  <!-- ── FAQ ── -->
  <div class="grd-band">
    <div class="grd-shell">
      <h2 class="grd-h2 ms-reveal">Вопросы, которые обычно задают</h2>
      <dl class="grd-faq">
        <div class="grd-faq-item ms-reveal">
          <dt>Это правда бесплатно?</dt>
          <dd>Да — для первых 20 участников потока. Мест не открывают заново: если место занято, оно недоступно до следующего набора.</dd>
        </div>
        <div class="grd-faq-item ms-reveal">
          <dt>Нужно ли готовить сложные блюда?</dt>
          <dd>Нет. План собирается из продуктов и блюд, которые вы отметили как приемлемые в анкете, — сложность рецептов можно ограничить прямо там.</dd>
        </div>
        <div class="grd-faq-item ms-reveal">
          <dt>У меня аллергия или непереносимость — это учтут?</dt>
          <dd>Да. Анкета отдельно спрашивает про лактозу, глютен и аллергии — план исключает эти продукты полностью.</dd>
        </div>
        <div class="grd-faq-item ms-reveal">
          <dt>Сколько времени займёт анкета?</dt>
          <dd>Несколько минут — 77 коротких вопросов, у большинства уже есть готовые варианты ответа.</dd>
        </div>
        <div class="grd-faq-item ms-reveal">
          <dt>Что будет, когда 20 мест закончатся?</dt>
          <dd>Регистрация закроется до следующего потока — дату следующего набора объявим отдельно.</dd>
        </div>
      </dl>
    </div>
  </div>

  <!-- ── REGISTRATION ── -->
  <div id="msReg" class="grd-reg">
    <div class="grd-reg-h">
      <h2 class="grd-h2 ms-reveal">Займите своё место</h2>
      <div class="grd-reg-sub ms-reveal">Регистрация занимает 30 секунд</div>
    </div>
    <div class="grd-card ms-reveal">
      <div class="grd-tabs">
        <button class="grd-tab on" id="wTabReg" onclick="wTab('register')">Регистрация</button>
        <button class="grd-tab" id="wTabLog" onclick="wTab('login')">Войти</button>
      </div>
      <div id="wFormReg">
        <div class="fg"><label>Телефон</label><input type="tel" id="wRegPhone" placeholder="+7 (900) 000-00-00"></div>
        <div class="fg"><label>Пароль</label><input type="password" id="wRegPw" placeholder="Минимум 6 символов"></div>
        <div class="fg"><label>Повтор пароля</label><input type="password" id="wRegPw2" placeholder="Повторите пароль"></div>
        <button class="grd-submit" id="wRegBtn" onclick="doRegister()">Участвовать бесплатно →</button>
        <div class="err-msg" id="wRegErr"></div>
      </div>
      <div id="wFormLog" style="display:none">
        <div class="fg"><label>Телефон</label><input type="tel" id="wLogPhone" placeholder="+7 (900) 000-00-00"></div>
        <div class="fg"><label>Пароль</label><input type="password" id="wLogPw" placeholder="Введите пароль"></div>
        <button class="grd-submit" id="wLogBtn" onclick="doLogin()">Войти →</button>
        <div class="err-msg" id="wLogErr"></div>
      </div>
    </div>
    <div class="grd-reg-foot">Осталось <span id="spotsLeft2">...</span> из 20 мест · бесплатно для первых участников</div>
  </div>

  <footer class="grd-footer">
    <div class="grd-footer-inner">
      <p class="grd-footer-close">До встречи в потоке,<br><span class="grd-footer-sign">— команда Slimfy</span></p>
      <p class="grd-footer-ps">P.S. — свободно <strong id="spotsLeft">...</strong> из 20 мест.</p>
    </div>
  </footer>
</div>

<!-- ── Questionnaire ── -->
<section id="questionnaire">
  <div class="q-header">
    <div class="q-header-inner">
      <div class="q-progress-wrap">
        <div class="q-progress-bar"><div class="q-progress-fill" id="qProgressFill" style="width:0%"></div></div>
        <div class="q-progress-text" id="qProgressText">0 / 77</div>
      </div>
      <div class="q-block-info">
        <span class="q-block-title" id="qBlockTitle">Заполните все вопросы и получите персональный план</span>
      </div>
    </div>
  </div>
  <div class="q-body">
    <div class="q-err-banner" id="qErrBanner"></div>
    <div class="q-list" id="qList"></div>
    <div class="q-submit-wrap">
      <button class="btn btn-p btn-lg" id="qSubmitBtn" onclick="submitQuestionnaire()">Получить результат ✨</button>
    </div>
  </div>
</section>

<!-- ── Generating ── -->
<section id="generating">
  <div class="gen-center"><div class="gen-card">
    <div class="gen-icon">🧬</div>
    <div class="gen-title">Анализируем ваши данные</div>
    <div class="gen-sub">Claude AI составляет персональный план питания. Обычно занимает 20–40 секунд.</div>
    <div class="gen-steps">
      <div class="gen-step done" id="gs1"><div class="gen-dot"></div>Анкета сохранена</div>
      <div class="gen-step active" id="gs2"><div class="gen-dot"></div>Расчёт параметров и ИМТ</div>
      <div class="gen-step" id="gs3"><div class="gen-dot"></div>Подбор типа диеты</div>
      <div class="gen-step" id="gs4"><div class="gen-dot"></div>Составление меню на 7 дней</div>
      <div class="gen-step" id="gs5"><div class="gen-dot"></div>Подбор рецептов и правил</div>
    </div>
  </div></div>
</section>

<!-- ── Result ── -->
<section id="result">
  <div class="result-nav">
    <div class="result-nav-title">🥗 Ваш персональный план питания</div>
    <div style="display:flex;gap:10px">
      <button class="btn btn-g" style="font-size:13px;padding:8px 14px" onclick="retake()">Пройти заново</button>
      <button class="btn btn-g" style="font-size:13px;padding:8px 14px" onclick="doLogout()">Выйти</button>
    </div>
  </div>
  <div class="result-body" id="resultBody"></div>
</section>

<div id="toasts"></div>

<script>
const BASE = location.pathname.replace(/\/?$/, '/');

// ── Questions data ──
const QUESTIONS = """ + json.dumps(QUESTIONS, ensure_ascii=False) + r""";
const BLOCKS = [...new Set(QUESTIONS.map(q => q.block))].map(b => ({
  block: b,
  title: QUESTIONS.find(q => q.block === b).bt,
  questions: QUESTIONS.filter(q => q.block === b)
}));
const TOTAL_BLOCKS = BLOCKS.length;

// ── State ──
let answers = {};
let isLoggedIn = false;

// ── Auth tabs ──
function wTab(type) {
  var isLog = type === 'login';
  document.getElementById('wTabLog').classList.toggle('on', isLog);
  document.getElementById('wTabReg').classList.toggle('on', !isLog);
  document.getElementById('wFormLog').style.display = isLog ? '' : 'none';
  document.getElementById('wFormReg').style.display = isLog ? 'none' : '';
}

// ── Auth ──
async function doLogin() {
  const phone = document.getElementById('wLogPhone').value;
  const password = document.getElementById('wLogPw').value;
  const btn = document.getElementById('wLogBtn');
  const err = document.getElementById('wLogErr');
  err.classList.remove('on');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Вхожу...';
  try {
    const r = await fetch(BASE + 'api/login', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({phone, password})
    });
    const d = await r.json();
    if (r.ok) { await afterLogin(); }
    else { err.textContent = d.error; err.classList.add('on'); }
  } catch { err.textContent = 'Ошибка соединения'; err.classList.add('on'); }
  finally { btn.disabled = false; btn.textContent = 'Войти →'; }
}

async function doRegister() {
  const phone = document.getElementById('wRegPhone').value;
  const password = document.getElementById('wRegPw').value;
  const pw2 = document.getElementById('wRegPw2').value;
  const btn = document.getElementById('wRegBtn');
  const err = document.getElementById('wRegErr');
  err.classList.remove('on');
  if (password !== pw2) { err.textContent = 'Пароли не совпадают'; err.classList.add('on'); return; }
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Регистрация...';
  try {
    const r = await fetch(BASE + 'api/register', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({phone, password})
    });
    const d = await r.json();
    if (r.ok) { await afterLogin(); }
    else { err.textContent = d.error; err.classList.add('on'); }
  } catch { err.textContent = 'Ошибка соединения'; err.classList.add('on'); }
  finally { btn.disabled = false; btn.textContent = 'Участвовать бесплатно →'; }
}

async function doLogout() {
  await fetch(BASE + 'api/logout', {method:'POST'});
  isLoggedIn = false;
  showSection('welcome');
  updateNav(false);
  answers = {};
}

function updateNav(loggedIn) {
  const el = document.getElementById('mldNavR') || document.getElementById('navR');
  const loginBtn = document.getElementById('humLoginBtn');
  if (loginBtn) loginBtn.style.display = loggedIn ? 'none' : '';
  if (!el) return;
  el.innerHTML = loggedIn
    ? '<button class="grd-navlink" onclick="doLogout()">Выйти</button>'
    : '';
}

async function afterLogin() {
  isLoggedIn = true;
  updateNav(true);
  const r = await fetch(BASE + 'api/me');
  const d = await r.json();
  if (!d.logged_in) return;
  if (d.result) { renderResult(d.result); showSection('result'); }
  else { startQuestionnaire(); }
}

// ── Section nav ──
function showSection(id) {
  document.querySelectorAll('section').forEach(s => s.classList.remove('active'));
  const landing = document.getElementById('landing');
  if (id === 'welcome') {
    landing.style.display = '';
    landing.scrollTop = 0;
  } else {
    landing.style.display = 'none';
    const sec = document.getElementById(id);
    sec.classList.add('active');
    sec.scrollTop = 0;
  }
}

// ── Questionnaire ──
function startQuestionnaire() {
  answers = {};
  renderAllQuestions();
  showSection('questionnaire');
}

function renderAllQuestions() {
  document.getElementById('qErrBanner').classList.remove('on');
  const list = document.getElementById('qList');
  list.innerHTML = BLOCKS.map(block => `
    <div class="q-block-section" id="qblock${block.block}">
      <div class="q-block-header">
        <div class="q-block-num">Блок ${block.block} из ${TOTAL_BLOCKS}</div>
        <div class="q-block-title-h">${esc(block.title)}</div>
      </div>
      ${block.questions.map(q => renderQuestion(q)).join('')}
    </div>
  `).join('');
  // Restore saved answers
  for (const [qid, val] of Object.entries(answers)) {
    const q = QUESTIONS.find(q => String(q.id) === String(qid));
    if (!q) continue;
    if (q.type === 'number') {
      const inp = document.getElementById('q' + qid);
      if (inp) inp.value = val;
    } else {
      const opts = document.querySelectorAll('.q-opt[data-qid="' + qid + '"]');
      opts.forEach(opt => {
        if (opt.dataset.val === val) {
          opt.classList.add('selected');
          opt.querySelector('input').checked = true;
        }
      });
    }
  }
  updateProgress();
}

function renderQuestion(q) {
  let body = '';
  if (q.type === 'number') {
    body = `<div class="q-num-wrap">
      <input type="number" class="q-num-inp" id="q${q.id}" min="${q.min}" max="${q.max}"
        placeholder="—" onchange="answers[${q.id}]=this.value;updateProgress()">
      <span class="q-unit">${q.unit}</span>
    </div>`;
  } else {
    body = `<div class="q-opts">${q.opts.map((opt, i) =>
      `<label class="q-opt" data-qid="${q.id}" data-val="${esc(opt)}" onclick="selectOpt(this,${q.id},'${esc(opt)}')">
        <input type="radio" name="q${q.id}" value="${esc(opt)}">
        ${esc(opt)}
      </label>`
    ).join('')}</div>`;
  }
  return `<div class="q-card" id="qcard${q.id}">
    <div class="q-num">Вопрос ${q.id}</div>
    <div class="q-text">${esc(q.text)}</div>
    ${body}
  </div>`;
}

function selectOpt(el, qid, val) {
  document.querySelectorAll('.q-opt[data-qid="' + qid + '"]').forEach(o => {
    o.classList.remove('selected');
    o.querySelector('input').checked = false;
  });
  el.classList.add('selected');
  el.querySelector('input').checked = true;
  answers[qid] = val;
  document.getElementById('qcard' + qid)?.classList.remove('error');
  updateProgress();
}

function updateProgress() {
  const answered = countAnswered();
  document.getElementById('qProgressText').textContent = answered + ' / 77';
  const fill = Math.round((answered / 77) * 100);
  document.getElementById('qProgressFill').style.width = fill + '%';
  const titleEl = document.getElementById('qBlockTitle');
  if (titleEl) titleEl.textContent = answered === 77 ? '✓ Все вопросы заполнены — нажмите кнопку ниже' : 'Заполните все вопросы и получите персональный план';
}

function countAnswered() {
  return Object.keys(answers).length;
}

async function submitQuestionnaire() {
  const missing = QUESTIONS.filter(q => !answers[q.id]);
  if (missing.length > 0) {
    const banner = document.getElementById('qErrBanner');
    banner.textContent = 'Пожалуйста, ответьте на все вопросы (' + missing.length + ' осталось)';
    banner.classList.add('on');
    missing.forEach(q => document.getElementById('qcard' + q.id)?.classList.add('error'));
    document.getElementById('qcard' + missing[0].id)?.scrollIntoView({behavior:'smooth', block:'center'});
    return;
  }
  document.getElementById('qErrBanner').classList.remove('on');
  const btn = document.getElementById('qSubmitBtn');
  btn.disabled = true; btn.innerHTML = '<span class="spinner"></span> Сохраняем...';
  try {
    const strAnswers = {};
    for (const [k, v] of Object.entries(answers)) strAnswers[String(k)] = String(v);
    const r = await fetch(BASE + 'api/answers', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(strAnswers)
    });
    if (!r.ok) { toast('Ошибка сохранения анкеты', true); return; }
    showSection('generating');
    animateGenSteps();
    await generateResult();
  } catch(e) {
    toast('Ошибка: ' + e.message, true);
  } finally {
    btn.disabled = false; btn.textContent = 'Получить результат ✨';
  }
}

let genStepTimer = null;
function animateGenSteps() {
  const steps = ['gs2','gs3','gs4','gs5'];
  let i = 0;
  clearInterval(genStepTimer);
  genStepTimer = setInterval(() => {
    if (i > 0) {
      document.getElementById(steps[i-1]).classList.remove('active');
      document.getElementById(steps[i-1]).classList.add('done');
    }
    if (i < steps.length) {
      document.getElementById(steps[i]).classList.add('active');
      i++;
    } else { clearInterval(genStepTimer); }
  }, 7000);
}

async function generateResult() {
  try {
    const r = await fetch(BASE + 'api/generate', {method:'POST', signal: AbortSignal.timeout(120000)});
    const d = await r.json();
    clearInterval(genStepTimer);
    if (r.ok && d.result) {
      renderResult(d.result);
      showSection('result');
    } else {
      toast(d.error || 'Ошибка генерации', true);
      showSection('questionnaire');
    }
  } catch(e) {
    clearInterval(genStepTimer);
    toast('Ошибка: ' + e.message, true);
    showSection('questionnaire');
  }
}

async function retake() {
  if (!confirm('Пройти анкету заново? Текущие результаты будут перезаписаны.')) return;
  answers = {};
  ['gs2','gs3','gs4','gs5'].forEach(id => document.getElementById(id).classList.remove('active','done'));
  document.getElementById('gs1').className = 'gen-step done';
  document.getElementById('gs2').className = 'gen-step active';
  renderAllQuestions();
  showSection('questionnaire');
}

// ── Results ──
function renderResult(r) {
  const p = r.parameters || {};
  const bmiColor = p.bmi < 18.5 ? '#3b82f6' : p.bmi < 25 ? '#16a34a' : p.bmi < 30 ? '#d97706' : '#dc2626';

  const mealRows = (r.meal_plan || []).map(day => `
    <tr>
      <td style="font-weight:700;white-space:nowrap">${day.day}</td>
      <td><div class="meal-type">Завтрак</div>${day.breakfast}</td>
      <td><div class="meal-type">Обед</div>${day.lunch}</td>
      <td><div class="meal-type">Ужин</div>${day.dinner}</td>
      <td><div class="meal-type">Перекус</div>${day.snack}</td>
    </tr>`).join('');

  const recipeCards = (r.recipes || []).map(rec => `
    <div class="recipe-card">
      <div class="recipe-name">${esc(rec.name)}</div>
      <div class="recipe-meta">
        <span class="recipe-tag">⏱ ${esc(rec.time)}</span>
        <span class="recipe-tag">🔥 ${esc(rec.calories)}</span>
      </div>
      <div class="recipe-ingr"><strong>Ингредиенты:</strong>
        <ul>${(rec.ingredients||[]).map(i => `<li>${esc(i)}</li>`).join('')}</ul>
      </div>
      <div class="recipe-steps">${esc(rec.steps)}</div>
    </div>`).join('');

  const ruleItems = (r.rules || []).map((rule, i) => `
    <div class="rule-item"><div class="rule-n">${i+1}</div><div class="rule-text">${esc(rule)}</div></div>`).join('');

  const eatItems = (r.eat_more || []).map(f =>
    `<div class="food-item"><div class="food-dot"></div>${esc(f)}</div>`).join('');
  const avoidItems = (r.avoid || []).map(f =>
    `<div class="food-item"><div class="food-dot"></div>${esc(f)}</div>`).join('');

  document.getElementById('resultBody').innerHTML = `
    <div class="r-section">
      <div class="r-section-title">Ваши параметры</div>
      <div class="params-grid">
        <div class="param-card bmi-card">
          <div class="param-val">${p.bmi ?? '—'}</div>
          <div class="param-unit">ИМТ</div>
          <div class="param-label">${esc(p.bmi_category ?? '')}</div>
        </div>
        <div class="param-card">
          <div class="param-val" style="color:#d97706">${p.tdee ?? '—'}</div>
          <div class="param-unit">ккал/день</div>
          <div class="param-label">Расход энергии</div>
        </div>
        <div class="param-card">
          <div class="param-val">${p.recommended_calories ?? '—'}</div>
          <div class="param-unit">ккал/день</div>
          <div class="param-label">Рекомендую съедать</div>
        </div>
        <div class="param-card">
          <div class="param-val" style="color:#3b82f6">${p.protein_g ?? '—'}г</div>
          <div class="param-unit">белки в день</div>
          <div class="param-label">Протеин</div>
        </div>
        <div class="param-card">
          <div class="param-val" style="color:#f59e0b">${p.fat_g ?? '—'}г</div>
          <div class="param-unit">жиры в день</div>
          <div class="param-label">Жиры</div>
        </div>
        <div class="param-card">
          <div class="param-val" style="color:#8b5cf6">${p.carbs_g ?? '—'}г</div>
          <div class="param-unit">углеводы в день</div>
          <div class="param-label">Углеводы</div>
        </div>
        <div class="param-card">
          <div class="param-val" style="color:#06b6d4">${p.water_l ?? '—'}л</div>
          <div class="param-unit">воды в день</div>
          <div class="param-label">Норма воды</div>
        </div>
      </div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Общий вывод</div>
      <div class="conclusion-card">${esc(r.conclusion ?? '')}</div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Рекомендуемая диета</div>
      <div class="diet-card">
        <div class="diet-name">🥗 ${esc(r.diet_name ?? '')}</div>
        <div class="diet-why">${esc(r.diet_why ?? '')}</div>
        <div class="principles">${(r.diet_principles||[]).map(p=>`<div class="principle">${esc(p)}</div>`).join('')}</div>
      </div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Меню на 7 дней</div>
      <div style="overflow-x:auto">
        <table class="meal-table">
          <thead><tr><th>День</th><th>Завтрак</th><th>Обед</th><th>Ужин</th><th>Перекус</th></tr></thead>
          <tbody>${mealRows}</tbody>
        </table>
      </div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Рецепты</div>
      <div class="recipes-grid">${recipeCards}</div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Правила соблюдения</div>
      <div class="rules-list">${ruleItems}</div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Продукты</div>
      <div class="foods-grid">
        <div class="foods-card eat">
          <h4>✅ Ешьте больше</h4>
          <div class="foods-list eat">${eatItems}</div>
        </div>
        <div class="foods-card avoid">
          <h4>❌ Избегайте</h4>
          <div class="foods-list avoid">${avoidItems}</div>
        </div>
      </div>
    </div>

    <div class="r-section">
      <div class="r-section-title">Мотивация</div>
      <div class="motivation-card">
        <div class="motivation-icon">🌟</div>
        <div class="motivation-text">${esc(r.motivation ?? '')}</div>
      </div>
    </div>
  `;
}

// ── Utils ──
function esc(s) {
  return String(s ?? '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function toast(msg, err=false) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = (err ? '❌ ' : '✅ ') + msg;
  document.getElementById('toasts').appendChild(el);
  requestAnimationFrame(() => el.classList.add('on'));
  setTimeout(() => { el.classList.remove('on'); setTimeout(() => el.remove(), 350); }, 4000);
}

// ── Enter key on auth form ──
document.addEventListener('keydown', function(e) {
  if (e.key !== 'Enter') return;
  var logVisible = document.getElementById('wFormLog').style.display !== 'none';
  if (logVisible) doLogin(); else doRegister();
});

// ── Init ──
(async () => {
  try {
    const [rMe, rSpots] = await Promise.all([
      fetch(BASE + 'api/me'),
      fetch(BASE + 'api/spots')
    ]);
    const dMe = await rMe.json();
    const dSpots = await rSpots.json();
    if (dSpots.free != null) {
      ['spotsLeft','spotsLeft2','spotsLeft3'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = dSpots.free;
      });
    }
    if (dMe.logged_in) {
      updateNav(true);
      if (dMe.result) { renderResult(dMe.result); showSection('result'); }
      else { startQuestionnaire(); }
    }
  } catch {}
})();
</script>
<script>
// ── Scroll reveal via IntersectionObserver ──
(function(){
  const obs = new IntersectionObserver((entries)=>{
    entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('visible')});
  },{threshold:0.15});
  document.querySelectorAll('.ms-reveal').forEach(el=>obs.observe(el));
})();
</script>
</body>
</html>"""

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8085, debug=False)
