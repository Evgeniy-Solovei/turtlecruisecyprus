# Git: что коммитить и как не засветить ключи

Репозиторий сейчас **без коммитов** — всё untracked. Ниже безопасный первый push.

---

## 1. Файлы с секретами — НИКОГДА в git

| Файл | Почему |
|------|--------|
| `backend/.env` | Stripe, Brevo, Django secret |
| `.turtlecruise_secrets.local.env` | Legacy WP/Stripe ключи |
| `backend/db.sqlite3` | Локальная БД с данными |
| `backend/media/` | Загруженные фото (~200MB+) |
| `backend/.venv/` | Виртуальное окружение |
| `turtlecruisebyscubacat/` | WordPress дамп сайта + SQL с данными |
| `installer.php` | Duplicator installer |

Всё это уже в `.gitignore`.

---

## 2. Проверка перед первым коммитом

```bash
cd /path/to/Cyprus

# Убедиться что секреты игнорируются
git status

# Не должно быть в списке:
#   backend/.env
#   .turtlecruise_secrets.local.env
#   backend/db.sqlite3
#   backend/media/
#   backend/.venv/
```

Если `.env` случайно уже был добавлен в git (в будущем):

```bash
git rm --cached backend/.env
git rm --cached -r backend/media/ 2>/dev/null || true
git commit -m "Stop tracking secrets and media"
```

---

## 3. Что коммитить

```bash
cd /path/to/Cyprus

git init   # если ещё не init
git add .gitignore
git add backend/ --force
git add docs/

# НЕ добавлять:
#   turtlecruisebyscubacat/   (WP dump — хранить отдельно)
#   installer.php
#   admin_hidden_settings_audit.md  (может содержать секреты — проверь)
#   django_migration_plan.md        (внутренние заметки — по желанию)

git status   # ещё раз глазами
git commit -m "Turtle Cruise Django backend: booking, CMS, Docker deploy"
```

### Что войдёт в `backend/`

- Код приложений (`apps/`)
- Шаблоны, static (CSS/JS)
- `docker-compose.yml`, `docker-compose.prod.yml`
- `deploy/nginx/`
- `requirements.txt`
- `.env.example` (без реальных ключей, только `REDACTED`)
- `scripts/`
- Тесты

### Что НЕ войдёт (gitignore)

- `.env`, `db.sqlite3`, `media/`, `.venv/`, `staticfiles/`

---

## 4. Создание репозитория на GitHub

```bash
# На GitHub: New repository → без README (у нас уже есть код)

git remote add origin git@github.com:YOUR_USER/turtlecruise-cyprus.git
git branch -M main
git push -u origin main
```

**Private repository** — обязательно private, пока в истории нет публичных ключей.

---

## 5. На сервере после clone

```bash
git clone git@github.com:YOUR_USER/turtlecruise-cyprus.git /opt/turtlecruise
cd /opt/turtlecruise/backend
cp .env.example .env
nano .env   # вставить РЕАЛЬНЫЕ ключи только на сервере
```

`.env` создаётся **только на сервере**, не копируется с ноутбука через git.

---

## 6. Медиа и SQL на сервер

Не в git. Перенос вручную:

```bash
# С ноутбука на сервер
rsync -avz backend/media/ user@server:/opt/turtlecruise/backend/media/
scp turtlecruisebyscubacat/dup-installer/dup-database__....sql user@server:/opt/dumps/
```

---

## 7. Если ключ уже попал в git

1. Сменить ключ в Stripe / Brevo / Django (rotate)
2. Удалить из истории: `git filter-repo` или BFG Repo-Cleaner
3. Force push (осторожно)

Проще: новый репозиторий + новые ключи, если история короткая.
