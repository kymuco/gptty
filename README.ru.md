# gptty

Русская версия. English version: [README.md](README.md)

Terminal-клиент для существующих ChatGPT web-сессий.

> [!WARNING]
> Это не официальный OpenAI API.
> Используется существующая ChatGPT web-сессия.
> Поведение web backend может измениться.

`gptty` — новое имя и направление бывшего `webchat-openai-cli`. Проект постепенно переезжает из standalone-скрипта в terminal-native продукт поверх [`chatgpt-web-adapter`](https://github.com/kymuco/chatgpt-web-adapter).

Текущая переходная версия сохраняет старый интерактивный CLI, но уже добавляет package layout и команду `gptty`.

## Направление проекта

```text
SDK = chatgpt-web-adapter
CLI = gptty
```

Целевой CLI должен поддерживать сценарии вроде:

```bash
gptty chat
gptty ask "explain this error"
git diff | gptty ask "review this patch"
gptty attach https://chatgpt.com/c/...
gptty messages --last 5
gptty status
gptty export --format md
```

В PR0 подключён только переходный интерактивный режим `gptty chat`. Остальные команды будут добавляться отдельными PR.

## Возможности сейчас

- интерактивный terminal-chat через legacy runtime из `main.py`
- потоковый вывод ответа в терминал
- метрики задержки: `first_token`, `last_token`, `total`
- единый локальный state-файл: `webchat_state.json`
- атомарная запись локального state и `auth_data.json`
- запросы с изображениями через `/img`
- режимы авторизации `auto` и `wait`
- локализация CLI на английский и русский
- переходная команда `gptty`

## Требования

- Python 3.10+
- системный `curl` в `PATH`
- Chrome или Chromium для `auth_fetcher.py`
- валидный `auth_data.json` для существующей ChatGPT web-сессии

## Установка из checkout

Создать и активировать виртуальное окружение:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e .[auth]
```

В Windows `cmd.exe`:

```cmd
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .[auth]
```

PyPI distribution name планируется как `gptty-web`, потому что имя `gptty` на PyPI уже занято. Установленная команда всё равно будет называться `gptty`.

## Получение `auth_data.json`

Быстрый режим для уже авторизованной браузерной сессии:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode auto
```

Режим ожидания, если нужно сначала войти или зарегистрироваться:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode wait
```

В `wait`-режиме браузер остаётся открытым до готовности чата. После этого отправьте любое сообщение вручную в окне браузера, чтобы запустить захват авторизации.

Опционально можно переопределить одноразовый probe-message, который используется в `auto`-режиме для захвата авторизации:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode auto --probe-prompt "Ping"
```

Короткий запуск wait-режима:

```cmd
venv\Scripts\python.exe auth_fetcher_wait.py
```

После успешного захвата рядом появится `auth_data.json`.

## Запуск CLI

Предпочтительная переходная команда:

```bash
gptty chat
```

Старый entrypoint пока поддерживается:

```bash
python main.py
```

Можно явно указать пути:

```bash
gptty chat --auth ./auth_data.json --state ./webchat_state.json
```

## Полезные legacy-команды

- `/help`
- `/models`
- `/new`
- `/list`
- `/use <chat_id>`
- `/reset`
- `/img <path_or_url> :: <prompt>`
- `/settings`
- `/model <name>`
- `/lang <en|ru>`
- `/ws <true|false>`
- `/effort <standard|extended|off>`
- `/metrics <true|false>`

## Важные файлы

- `auth_data.json` - локальные данные авторизации, не коммитить
- `webchat_state.json` - локальная история чатов и runtime-настройки, не коммитить

## Замечания

- `auth_data.json` является основным источником авторизации.
- `.env` не обязателен. Если он есть, `accessToken` используется как запасной fallback даже при отсутствии `auth_data.json`, но полный `auth_data.json` остаётся самым совместимым вариантом.
- В `auto`-режиме `auth_fetcher.py` отправляет одно probe-сообщение для запуска захвата. По умолчанию это `"Hello"`, но текст можно заменить через `--probe-prompt`.
- В `wait`-режиме `auth_fetcher.py` не отправляет probe автоматически. Войдите или зарегистрируйтесь, затем отправьте любое сообщение вручную в браузере, чтобы запустить захват.
- Не смешивайте `cookies` и `api_key/accessToken` от разных аккаунтов.
- Локальный state и auth-файлы записываются атомарно, чтобы снизить риск битого JSON при прерывании процесса.
- Если `main.py` сообщает, что не найден `curl`, установите системный `curl.exe` и проверьте `curl --version`.

## Устранение проблем

- Не найден `curl`
  Установите системный `curl.exe` и проверьте, что команда `curl --version` работает.
- Отсутствует `auth_data.json`
  Запустите `python auth_fetcher.py --mode wait`, завершите вход в браузере, затем отправьте любое сообщение в окне чата.
- В `auth_fetcher` открывается не тот аккаунт
  В используемом браузерном профиле уже сохранена другая сессия. Выйдите из неё или используйте wait-режим и войдите в нужный аккаунт.
- Сначала всё работало, а потом запросы перестали проходить
  Скорее всего истекли cookies сессии или `api_key`. Сгенерируйте `auth_data.json` заново.
- `gptty chat` запускается, но не отвечает
  Проверьте, что `auth_data.json` существует, `curl` установлен, а сохранённая браузерная сессия относится к нужному аккаунту.

## Статус

Репозиторий находится в переходе от `webchat-openai-cli` к `gptty`.

PR0 закладывает package skeleton и console command. В следующих PR backend-поведение будет переноситься на `chatgpt-web-adapter`, появятся `gptty ask`, pipe-сценарии, attach существующих ChatGPT-чтов, export и улучшенный auth UX.
