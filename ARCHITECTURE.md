# Startup Ideas Collector — Архитектура проекта

## Общее описание

Система автоматического поиска и анализа стартап-идей из онлайн-дискуссий. Скрейпит Reddit, Hacker News и другие источники, фильтрует через AI, проводит глубокий анализ проблем, генерирует стартап-идеи и оценивает рыночный потенциал.

**Стек:**
- Backend: Python 3.9, FastAPI, SQLAlchemy, SQLite
- Frontend: Next.js 16, React 19, TypeScript, Tailwind CSS 4
- AI: Claude Haiku (фильтрация), Claude Sonnet (анализ), Tavily (поиск конкурентов)
- Scheduling: APScheduler

---

## Структура проекта

```
startup-ideas/
├── backend/
│   ├── api/
│   │   ├── main.py                    # FastAPI app, CORS, lifecycle, routers
│   │   └── routes/
│   │       ├── problems.py            # CRUD проблем, фильтры, card management
│   │       ├── scraper.py             # Запуск скрейпинга, расписание, история
│   │       └── stats.py               # Статистика для дашборда
│   ├── agents/
│   │   ├── scrapers/                  # 9 скрейперов
│   │   │   ├── base_agent.py          # Базовый класс скрейпера
│   │   │   ├── reddit_agent.py        # Reddit (без API ключа!)
│   │   │   ├── hackernews_agent.py    # Hacker News
│   │   │   ├── twitter_agent.py       # Twitter/X
│   │   │   ├── producthunt_agent.py   # Product Hunt
│   │   │   ├── youtube_agent.py       # YouTube
│   │   │   ├── indiehackers_agent.py  # Indie Hackers
│   │   │   ├── quora_agent.py         # Quora
│   │   │   ├── medium_agent.py        # Medium
│   │   │   └── discourse_agent.py     # Discourse форумы
│   │   └── analyzers/                 # AI-анализаторы
│   │       ├── base_analyzer.py       # Обёртка над Claude API
│   │       ├── problem_analyzer.py    # Фильтр + извлечение проблем
│   │       └── marketing_agent.py     # Маркетинговый анализ
│   ├── services/
│   │   ├── orchestrator.py            # Координатор pipeline анализа
│   │   └── scheduler.py              # APScheduler для расписания
│   ├── db/
│   │   ├── models.py                  # SQLAlchemy модели (11 таблиц)
│   │   └── database.py               # Подключение к SQLite, миграции
│   ├── config.py                      # Pydantic Settings (env vars)
│   ├── config.yaml                    # Конфигурация скрейперов
│   ├── requirements.txt               # Python-зависимости
│   ├── .env                           # API ключи (не в git)
│   └── data/
│       ├── startup_ideas.db           # SQLite база данных
│       └── schedule.json              # Сохранённое расписание
│
├── frontend/
│   ├── app/                           # Next.js App Router
│   │   ├── page.tsx                   # Дашборд (/)
│   │   ├── layout.tsx                 # Root layout
│   │   ├── problems/
│   │   │   ├── page.tsx               # Список проблем (/problems)
│   │   │   └── [id]/page.tsx          # Детали проблемы (/problems/:id)
│   │   ├── archive/page.tsx           # Архив (/archive)
│   │   └── scraping/page.tsx          # Управление скрейпингом (/scraping)
│   ├── components/
│   │   ├── ProblemCard.tsx            # Карточка проблемы
│   │   ├── FilterPanel.tsx            # Панель фильтров
│   │   ├── StatusBadge.tsx            # Бейдж статуса
│   │   ├── StarButton.tsx             # Кнопка избранного
│   │   ├── StatsCard.tsx              # Карточка статистики
│   │   ├── TagInput.tsx               # Редактор тегов
│   │   └── NotesEditor.tsx            # Редактор заметок
│   ├── lib/
│   │   └── api.ts                     # API-клиент (все запросы к backend)
│   ├── types/
│   │   └── index.ts                   # TypeScript-типы
│   └── package.json
│
└── .env                               # API ключи
```

---

## Как работает pipeline

```
1. СКРЕЙПИНГ
   POST /api/scrape → BackgroundTask
   ┌─────────────────────────────────────┐
   │ RedditScraper / HackerNewsScraper   │
   │ Скрейпит посты + комментарии        │
   │ Фильтрует по upvotes + keywords     │
   │ Дедупликация по URL                 │
   │ Сохраняет → таблица discussions     │
   └──────────────┬──────────────────────┘
                  ↓
2. ФИЛЬТРАЦИЯ (Claude Haiku — быстро, дёшево)
   ┌─────────────────────────────────────┐
   │ ProblemAnalyzer.filter_discussion() │
   │ Промпт: "Это реальная проблема?"    │
   │ Ответ: YES / NO                     │
   │ ~60-70% отсеивается                 │
   └──────────────┬──────────────────────┘
                  ↓ (только YES)
3. ГЛУБОКИЙ АНАЛИЗ (Claude Sonnet — медленно, качественно)
   ┌─────────────────────────────────────┐
   │ ProblemAnalyzer.analyze_problem()   │
   │ Извлекает:                          │
   │   - problem_statement               │
   │   - severity (1-10)                 │
   │   - target_audience                 │
   │   - current_solutions               │
   │   - why_they_fail                   │
   │ Генерирует: 2-4 startup ideas      │
   │ Сохраняет → problems, startup_ideas │
   └──────────────┬──────────────────────┘
                  ↓
4. МАРКЕТИНГОВЫЙ АНАЛИЗ
   ┌─────────────────────────────────────┐
   │ MarketingAgent.analyze_market()     │
   │ 1. Tavily API → поиск конкурентов   │
   │ 2. Claude Sonnet → анализ рынка     │
   │ Извлекает:                          │
   │   - TAM / SAM / SOM                 │
   │   - positioning, pricing_model      │
   │   - gtm_strategy, competitive_moat  │
   │   - market_score (0-100)            │
   │ Сохраняет → marketing_analysis      │
   └──────────────┬──────────────────────┘
                  ↓
5. СКОРИНГ
   ┌─────────────────────────────────────┐
   │ Формула (Tier 2):                   │
   │ Overall = Market×0.7 + Severity×3   │
   │ Диапазон: 0-100                     │
   │ Сохраняет → overall_scores          │
   └─────────────────────────────────────┘
```

---

## База данных (SQLite, 11 таблиц)

### sources
Источники контента (Reddit, HN, YouTube и т.д.)

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| name | str, unique | Например "reddit_freelance" |
| type | Enum | REDDIT, HACKERNEWS, TWITTER, PRODUCTHUNT, YOUTUBE, INDIEHACKERS, QUORA, MEDIUM, DISCOURSE |
| config | JSON | Конфигурация источника |
| last_scraped | datetime | Когда последний раз собирали |
| is_active | bool | Активен ли |
| created_at | datetime | |

### discussions
Сырые дискуссии со скрейперов

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| source_id | int, FK → sources | |
| url | str, unique | Дедупликация по URL |
| external_id | str | ID на источнике (Reddit ID, HN ID) |
| title | text | |
| content | text | Пост + топ-комментарии |
| author | str | |
| upvotes | int | |
| comments_count | int | |
| posted_at | datetime | |
| scraped_at | datetime | |
| is_analyzed | bool | Прошёл через pipeline? |
| passed_filter | bool | Прошёл фильтр Haiku? |

### problems
Извлечённые проблемы

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| discussion_id | int, FK → discussions | |
| problem_statement | text | Формулировка проблемы |
| severity | int (1-10) | Критичность |
| target_audience | text | Целевая аудитория |
| current_solutions | text | Текущие решения |
| why_they_fail | text | Почему не работают |
| analysis_tier | Enum | NONE / BASIC / DEEP |
| extracted_at | datetime | |
| **Card management** | | |
| card_status | str | new / viewed / in_review / verified / archived / rejected |
| first_viewed_at | datetime | |
| last_viewed_at | datetime | |
| archived_at | datetime | |
| verified_at | datetime | |
| view_count | int | |
| is_starred | bool | |
| user_notes | text | |
| user_tags | JSON | Массив строк |

### startup_ideas
Сгенерированные AI идеи

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| problem_id | int, FK → problems | |
| idea_title | str | |
| description | text | |
| approach | str | SaaS, marketplace, tool, API |
| value_proposition | text | |
| core_features | JSON | Массив фич |
| tags | JSON | Категории |

### marketing_analysis
Маркетинговый анализ (Tier 2)

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| problem_id | int, FK, unique | |
| tam | str | Total Addressable Market |
| sam | str | Serviceable Addressable Market |
| som | str | Serviceable Obtainable Market |
| market_description | text | |
| competitors_json | JSON | [{name, url, description}] |
| positioning | text | |
| pricing_model | str | freemium / subscription / etc |
| target_segments | JSON | |
| gtm_strategy | text | |
| gtm_channels | JSON | |
| competitive_moat | text | Устойчивое преимущество |
| market_score | int (0-100) | |
| score_reasoning | text | |

### overall_scores
Агрегированные оценки

| Поле | Тип | Описание |
|------|-----|----------|
| problem_id | int, FK, unique | |
| market_score | int | 0-100 |
| overall_confidence_score | int | 0-100, формула: Market×0.7 + Severity×3 |
| analysis_tier | Enum | BASIC или DEEP |

### scrape_logs
Лог запусков скрейпинга

| Поле | Тип | Описание |
|------|-----|----------|
| id | int, PK | |
| source | str | reddit / hackernews |
| status | str | running / completed / failed |
| discussions_found | int | |
| problems_created | int | |
| error_message | text | |
| started_at | datetime | |
| completed_at | datetime | |
| triggered_by | str | manual / schedule |

### Таблицы для будущего Tier 3 (пока пустые)
- **design_analysis** — UX/UI анализ
- **tech_analysis** — техническая реализуемость
- **validation_analysis** — существующие решения
- **trend_analysis** — Google Trends

---

## API эндпоинты

### Проблемы

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/problems` | Список проблем с фильтрами (status, is_starred, min_score, sort_by, tags, source_type, date_from/to, include_archived) |
| GET | `/api/problems/archive` | Архивные/отклонённые проблемы |
| GET | `/api/problems/{id}` | Детали проблемы. Автоматически: view_count++, NEW→VIEWED |
| PATCH | `/api/problems/{id}/status` | Изменить статус: `{status: "verified"}` |
| PATCH | `/api/problems/{id}/star` | Избранное: `{is_starred: true}` |
| PATCH | `/api/problems/{id}/notes` | Заметки: `{user_notes: "текст"}` |
| PATCH | `/api/problems/{id}/tags` | Теги: `{user_tags: ["tag1", "tag2"]}` |
| GET | `/api/problems/{id}/competitors` | Конкуренты из маркетинг-анализа |

### Скрейпинг

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/scrape?source=reddit&limit=10&analyze=true` | Запустить скрейпинг (фоновая задача) |
| GET | `/api/scrape/history?limit=20` | История запусков |
| GET | `/api/sources/status` | Статус всех источников |

### Расписание

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/schedule` | Текущее расписание |
| POST | `/api/schedule` | Установить: `{interval_hours: 6, source: "all", limit: 10, analyze: true}` |
| DELETE | `/api/schedule` | Удалить расписание |

### Статистика

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/stats` | Дашборд: totals, today, scores, card_statuses, sources |
| GET | `/api/stats/recent-activity?days=7` | Активность по дням |

---

## AI-агенты

### 1. Problem Analyzer — Фильтр (Haiku)
- **Модель:** `claude-3-haiku-20240307`
- **Задача:** Быстро определить "это реальная проблема?" (YES/NO)
- **Критерии:** реальная боль, несколько людей, решаема технологией, не шутка, не нишево
- **Результат:** ~60-70% дискуссий отсеивается → экономия на Sonnet

### 2. Problem Analyzer — Глубокий анализ (Sonnet)
- **Модель:** `claude-sonnet-4-5-20250929`
- **Задача:** Извлечь проблему, оценить severity, сгенерировать 2-4 стартап-идеи
- **Вывод на русском языке**
- **Output:** JSON с problem_statement, severity, target_audience, current_solutions, why_they_fail, startup_ideas[]

### 3. Marketing Agent (Sonnet + Tavily)
- **Tavily:** 2 поисковых запроса для нахождения конкурентов
- **Sonnet:** Анализ TAM/SAM/SOM, позиционирование, GTM-стратегия, конкурентное преимущество
- **Скоринг:**
  - 90-100: Огромный рынок, слабая конкуренция
  - 70-89: Большой рынок, есть дифференциация
  - 50-69: Средний рынок, конкурентный
  - 30-49: Маленький рынок
  - 0-29: Крошечный рынок или уже решено

---

## Скрейперы (9 штук)

| Скрейпер | Источник | API ключ | Метод |
|----------|----------|----------|-------|
| RedditScraper | Reddit | **Не нужен** | Public JSON (old.reddit.com) |
| HackerNewsScraper | Hacker News | Не нужен | Firebase API |
| TwitterScraper | Twitter/X | TWITTER_BEARER_TOKEN | Tweepy |
| ProductHuntScraper | Product Hunt | PRODUCTHUNT_API_TOKEN (опц.) | GraphQL / HTML |
| YouTubeScraper | YouTube | YOUTUBE_API_KEY | Data API v3 |
| IndieHackersScraper | Indie Hackers | Не нужен | HTML scraping |
| QuoraScraper | Quora | Не нужен | HTML scraping |
| MediumScraper | Medium | Не нужен | RSS + HTML |
| DiscourseScraper | Discourse | Не нужен | Discourse API |

**Общая логика скрейперов (BaseScraper):**
1. Получить или создать Source запись в БД
2. Скрейпить посты/дискуссии по ключевым словам из config.yaml
3. Фильтровать по минимальным upvotes
4. Собирать top-N комментариев для контекста
5. Дедупликация по URL (unique constraint)
6. Сохранить новые Discussion записи
7. Обновить source.last_scraped

**Конфигурация в config.yaml:**
```yaml
reddit:
  subreddits:
    - name: "mildlyinfuriating"
      keywords: [annoying, frustrating, hate when]
      min_upvotes: 50
      max_posts: 20
  problem_indicators: [I wish, frustrated, why is there no, ...]

hackernews:
  min_score: 10
  max_items: 30
  keywords: [the problem with, I wish, frustrating, pain point]
  item_types: [ask_hn, show_hn]
```

---

## Frontend

### Страницы

| Путь | Файл | Описание |
|------|------|----------|
| `/` | app/page.tsx | Дашборд: статистика, статусы карточек, последние проблемы, навигация |
| `/problems` | app/problems/page.tsx | Список проблем с FilterPanel, сортировка, фильтры |
| `/problems/:id` | app/problems/[id]/page.tsx | Детали: статус, звёздочка, скоры, идеи, маркетинг, заметки, теги |
| `/archive` | app/archive/page.tsx | Архивные карточки с кнопкой "Восстановить" |
| `/scraping` | app/scraping/page.tsx | Ручной запуск, расписание, история, статус источников |

### Компоненты

| Компонент | Описание |
|-----------|----------|
| ProblemCard | Карточка: заголовок, score (цвет по порогу), статус, теги, звёздочка, метаданные |
| FilterPanel | Сортировка, min_score, статус, избранное, analysis_tier |
| StatusBadge | Цветной бейдж: Новая(синий), Просмотрена(серый), На рассмотрении(жёлтый), Проверена(зелёный), Архив(серый), Отклонена(красный) |
| StarButton | ★/☆ с API-вызовом, e.stopPropagation для работы внутри Link |
| StatsCard | Метрика с иконкой, значением, sublabel |
| TagInput | Цветные pills, добавление/удаление с авто-сохранением |
| NotesEditor | Textarea + кнопка "Сохранить" с отслеживанием изменений |

### API-клиент (lib/api.ts)

Класс `ApiClient` с методами:
```typescript
// Статистика
getStats()

// Проблемы
getProblems(filters?)
getProblem(id)
getArchivedProblems(params?)
getCompetitors(problemId)

// Card management
updateCardStatus(problemId, status)
toggleStar(problemId, isStarred)
updateNotes(problemId, notes)
updateTags(problemId, tags)

// Скрейпинг
triggerScrape({ source, limit, analyze })
getSourcesStatus()
getScrapeHistory(limit)

// Расписание
getSchedule()
setSchedule({ interval_hours, source, limit, analyze })
deleteSchedule()
```

---

## Workflow карточек

```
         ┌──────┐
         │ NEW  │ (автоматически при создании)
         └──┬───┘
            │ (открытие → view_count++, auto-transition)
         ┌──┴──────┐
         │ VIEWED  │
         └──┬──────┘
            │ (ручное действие пользователя)
    ┌───────┼───────┐
    ↓       ↓       ↓
┌────────┐ ┌──────┐ ┌──────────┐
│IN_REVIEW│ │ARCHVD│ │ REJECTED │
└───┬────┘ └──────┘ └──────────┘
    │
    ↓
┌──────────┐
│ VERIFIED │
└──────────┘
```

Дополнительно: is_starred (звёздочка), user_notes (заметки), user_tags (теги).

---

## Environment переменные (.env)

```bash
# Обязательные
ANTHROPIC_API_KEY=sk-ant-...      # Claude API
TAVILY_API_KEY=tvly-...           # Поиск конкурентов

# Опциональные (для дополнительных скрейперов)
TWITTER_BEARER_TOKEN=...          # Twitter API
YOUTUBE_API_KEY=...               # YouTube Data API v3
PRODUCTHUNT_API_TOKEN=...         # Product Hunt
REDDIT_CLIENT_ID=...              # Reddit OAuth (не обязательно, работает без)
REDDIT_CLIENT_SECRET=...

# С дефолтами (можно не указывать)
DATABASE_PATH=./backend/data/startup_ideas.db
API_HOST=0.0.0.0
API_PORT=8000
FILTER_MODEL=claude-3-haiku-20240307
ANALYSIS_MODEL=claude-sonnet-4-5-20250929
```

---

## Как запустить

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Создать .env с ключами (ANTHROPIC_API_KEY, TAVILY_API_KEY)

# Инициализировать БД
python -m db.database

# Запустить сервер
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### Первый запуск скрейпинга
1. Открыть http://localhost:3000/scraping
2. Выбрать источник (Reddit работает без ключей)
3. Нажать "Запустить скрейпинг"
4. Через 1-2 минуты проблемы появятся на дашборде

---

## Ключевые архитектурные решения

1. **Двухуровневый AI:** Haiku фильтр (дёшево) → Sonnet анализ (дорого). Экономия ~60-70% на API.

2. **Reddit без API ключа:** Используем public JSON endpoint `old.reddit.com/{subreddit}.json` — не нужна регистрация приложения.

3. **SQLite без Alembic:** Миграции через raw `ALTER TABLE` в `database.py`. Простое `create_all` не добавляет колонки к существующим таблицам.

4. **card_status как String(20):** Не Enum в SQLAlchemy — избегаем проблем с маппингом enum name/value в SQLite.

5. **BackgroundTasks:** Скрейпинг и анализ запускаются как FastAPI BackgroundTasks. API возвращает ответ сразу, работа идёт в фоне.

6. **APScheduler:** Persistent schedule через JSON-файл. Восстанавливается при перезапуске backend.

7. **Весь UI на русском.** Все промпты для AI тоже генерируют ответы на русском.

8. **Tier 2 vs Tier 3:** Сейчас работает Tier 2 (Problem + Marketing). Tier 3 (Design, Tech, Validation, Trends) подготовлен в моделях, но ещё не реализован.
