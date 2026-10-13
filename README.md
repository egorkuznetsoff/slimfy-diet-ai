# slimfy-diet-ai

**Slimfy** — AI-приложение для составления персонального рациона питания. Пользователь регистрируется, отвечает на анкету из 77 вопросов (параметры тела, активность, привычки, здоровье, предпочтения) и получает план питания, который генерирует модель Claude.

Продакшен: [slimfy.ru](https://slimfy.ru), также `24fox.ru/diet/`.

## Стек

| Слой | Технология |
|---|---|
| Бэкенд | Python 3, Flask |
| AI | Anthropic API (`anthropic` SDK, модель `claude-sonnet-4-6`) |
| БД | PostgreSQL (`foxdb`): таблицы `diet_users`, `diet_answers`, план питания |
| Пароли | bcrypt |
| Фронтенд | SPA на Vanilla JS, встроен в `app.py` |
| Запуск | systemd + nginx, порт 8085 |

## API

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/register`, `/api/login`, `/api/logout` | аккаунт |
| GET | `/api/me` | текущий пользователь |
| POST | `/api/answers` | сохранить ответы анкеты |
| POST | `/api/generate` | сгенерировать рацион через Claude |
| GET | `/api/spots` | дополнительные данные для интерфейса |

## Развёртывание

1. **Зависимости:**
   ```bash
   pip install flask psycopg2-binary bcrypt anthropic
   ```
2. **PostgreSQL:** база `foxdb`, пользователь `fox`. Пароль впишите вместо `CHANGE_ME_DB_PASSWORD`, а `app.secret_key` замените на случайную строку.
3. **Клон:**
   ```bash
   git clone https://github.com/egorkuznetsoff/slimfy-diet-ai.git /home/egor/diet
   ```
4. **systemd** (`/etc/systemd/system/diet.service`):
   ```ini
   [Unit]
   Description=Diet AI (Slimfy)
   After=network.target postgresql.service

   [Service]
   User=egor
   WorkingDirectory=/home/egor/diet
   Environment=ANTHROPIC_API_KEY=sk-ant-...
   ExecStart=/usr/bin/python3 /home/egor/diet/app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```
   ```bash
   sudo systemctl daemon-reload && sudo systemctl enable --now diet
   ```
5. **nginx:** для собственного домена — `location / { proxy_pass http://127.0.0.1:8085/; }` и TLS через certbot. Для подпапки — `location ^~ /diet/ { proxy_pass http://127.0.0.1:8085/; }`.

## Секреты

Перед публикацией на GitHub все секреты заменены заглушками `CHANGE_ME_*`.
Перед запуском найдите их и подставьте свои значения:

```bash
grep -rn CHANGE_ME_ .
```

## Автор

**Егор Кузнецов** (Egor Kuznetsov) — идея, разработка, деплой и сопровождение.
GitHub: [@egorkuznetsoff](https://github.com/egorkuznetsoff) · 2026

Часть кода написана в паре с AI-ассистентом Claude (Anthropic).
Репозиторий приватный, все права защищены.
