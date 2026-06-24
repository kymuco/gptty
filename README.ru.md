# gptty

Русская версия. English version: [README.md](README.md)

Terminal-клиент для существующих ChatGPT web-сессий.

> [!WARNING]
> Это не официальный OpenAI API.
> Используется существующая ChatGPT web-сессия.
> Поведение web backend может измениться.

`gptty` — новое имя и направление бывшего `webchat-openai-cli`. Проект постепенно переезжает из standalone-скрипта в terminal-native продукт поверх [`chatgpt-web-adapter`](https://github.com/kymuco/chatgpt-web-adapter).

Текущая переходная версия сохраняет legacy CLI доступным, но уже добавляет package layout, команду `gptty` и SDK-backed internals.

## Направление проекта

```text
SDK = chatgpt-web-adapter
CLI = gptty
```

Целевой CLI должен поддерживать сценарии вроде:

```bash
gptty chat
gptty ask "explain this error"
gptty ask --image screenshot.png "describe this UI"
git diff | gptty ask "review this patch"
gptty attach https://chatgpt.com/c/...
gptty send "continue from here"
gptty messages --last 5 --format markdown
gptty status --format json
gptty export --format markdown --output conversation.md
```

`gptty ask`, `gptty send`, default `gptty chat`, команды inspection для conversation и export уже работают через SDK boundary. Legacy interactive runtime остаётся доступен через `gptty chat --legacy`, пока feature parity переносится отдельными PR.

## Возможности сейчас

- минимальный SDK-backed interactive chat через `gptty chat`
- attach существующих conversations через `gptty attach`
- отправка prompt в attached, explicit или новый conversation через `gptty send`
- SDK-backed image prompts через `gptty ask --image` и `gptty send --image`
- просмотр attached или explicit conversations через `gptty messages` и `gptty status`
- export attached или explicit conversations через `gptty export`
- output modes для `messages`, `status`, `send` и `export`: `plain`, `json`, `markdown`
- legacy interactive chat fallback через `gptty chat --legacy`
- one-shot SDK-backed запросы через `gptty ask`
- централизованная stdin-политика для pipe-friendly prompts
- pipe-friendly prompts, например `git diff | gptty ask "review this patch"`
- потоковый вывод ответа в терминал
- минимальный SDK chat state-файл: `gptty_state.json`
- legacy state-файл для `--legacy`: `webchat_state.json`
- атомарная запись локального state и `auth_data.json`
- legacy-запросы с изображениями через `/img` в `gptty chat --legacy`
- режимы авторизации `auto` и `wait`
- локализация CLI на английский и русский в legacy runtime
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

Прикрепить существующий ChatGPT conversation:

```bash
gptty attach https://chatgpt.com/c/...
```

Отправить prompt в attached conversation:

```bash
gptty send "continue from here"
```

Передать stdin в attached conversation:

```bash
git diff | gptty send "review this patch"
```

Отправить в explicit conversation без предварительного `attach`:

```bash
gptty send --to https://chatgpt.com/c/... "continue there"
```

Начать новый conversation и сохранить возвращённую ссылку/ID в `gptty_state.json`:

```bash
gptty send --new "start a new conversation"
```

Отправить image prompt через SDK-backed команды:

```bash
gptty ask --image screenshot.png "describe this UI"
gptty ask --image https://example.com/chart.png "summarize this chart"
gptty send --image diagram.webp "continue with this image"
gptty send --image before.png --image after.png "compare these images"
```

`--image` принимает локальные пути к файлам, `http(s)` URL и data URI. Опцию можно использовать несколько раз. Поддерживаемые SDK форматы изображений: PNG, JPEG/JPG, GIF и WebP.

Посмотреть attached conversation:

```bash
gptty messages --last 5
gptty status
```

Использовать JSON или Markdown output для scripts и exports:

```bash
gptty messages --last 5 --format json
gptty messages --last 5 --format markdown
gptty status --format json
gptty send --format json "summarize the current thread"
gptty export --format markdown --output conversation.md
gptty export --format json --output conversation.json
```

Когда `gptty send` используется с `--format json` или `--format markdown`, streaming отключается внутри команды, чтобы output оставался полным и пригодным для парсинга.

Можно смотреть или экспортировать explicit conversation без attach:

```bash
gptty messages https://chatgpt.com/c/... --last 5
gptty status https://chatgpt.com/c/...
gptty export https://chatgpt.com/c/... --last 20 --output conversation.md
```

`gptty export` по умолчанию выводит Markdown. Если `--output` указывает на существующий файл, добавьте `--overwrite`, чтобы заменить его.

Минимальный SDK-backed interactive chat:

```bash
gptty chat
```

SDK-backed chat loop сейчас поддерживает:

```text
/help
/new
/exit
/quit
```

Запустить полный legacy interactive runtime:

```bash
gptty chat --legacy
```

One-shot SDK-backed prompt:

```bash
gptty ask "explain this error"
```

Передать stdin в prompt:

```bash
git diff | gptty ask "review this patch"
```

Если одновременно переданы stdin и prompt, `gptty ask` и `gptty send` отправляют stdin как контекст, а prompt добавляют ниже под `User prompt:`.

Принудительно читать stdin:

```bash
gptty ask --stdin "summarize this input"
```

Игнорировать piped stdin:

```bash
cat noisy.log | gptty ask --no-stdin "explain this from the prompt only"
```

Отключить streaming и напечатать финальный ответ:

```bash
gptty ask --no-stream "summarize this session"
gptty send --no-stream "summarize this conversation"
```

Старый entrypoint пока поддерживается:

```bash
python main.py
```

Можно явно указать пути:

```bash
gptty attach https://chatgpt.com/c/... --auth ./auth_data.json --state ./gptty_state.json
gptty send --auth ./auth_data.json --state ./gptty_state.json "hello"
gptty send --auth ./auth_data.json --state ./gptty_state.json --image ./screenshot.png "describe this"
gptty export --auth ./auth_data.json --state ./gptty_state.json --output conversation.md
gptty chat --auth ./auth_data.json --state ./gptty_state.json
gptty chat --legacy --auth ./auth_data.json --state ./webchat_state.json
gptty ask --auth ./auth_data.json --timeout 120 "hello"
```

## Полезные legacy-команды

Доступны в `gptty chat --legacy`:

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
- `gptty_state.json` - минимальный SDK-backed chat state, не коммитить
- `webchat_state.json` - legacy-история чатов и runtime-настройки, не коммитить

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
- `gptty send`, `gptty messages`, `gptty status` или `gptty export` сообщает, что нет attached conversation
  Сначала выполните `gptty attach <url-or-id>`, передайте conversation URL/id прямо в команду или используйте `gptty send --new`.
- `gptty ask --image` или `gptty send --image` сообщает, что image file не существует
  Проверьте локальный путь или передайте `http(s)` URL изображения.
- В `auth_fetcher` открывается не тот аккаунт
  В используемом браузерном профиле уже сохранена другая сессия. Выйдите из неё или используйте wait-режим и войдите в нужный аккаунт.
- Сначала всё работало, а потом запросы перестали проходить
  Скорее всего истекли cookies сессии или `api_key`. Сгенерируйте `auth_data.json` заново.
- `gptty chat` запускается, но не отвечает
  Проверьте, что `auth_data.json` существует, а сохранённая браузерная сессия относится к нужному аккаунту.
- `gptty chat --legacy` запускается, но не отвечает
  Проверьте, что `auth_data.json` существует, `curl` установлен, а сохранённая браузерная сессия относится к нужному аккаунту.

## Статус

Репозиторий находится в переходе от `webchat-openai-cli` к `gptty`.

PR0 закладывает package skeleton и console command. PR1 добавляет SDK client boundary. PR2 добавляет первую SDK-backed команду, `gptty ask`. PR3 централизует stdin pipe handling. PR4 переносит default `gptty chat` на минимальный SDK-backed loop с legacy fallback. PR5 добавляет attach/messages/status conversation operations. PR6 добавляет отправку в attached, explicit и новый conversation. PR7 добавляет shared output modes для messages/status/send. PR8 добавляет conversation export. PR9 добавляет SDK-backed image prompts для ask/send. В следующих PR появятся более богатые pipe-сценарии, SDK chat `/img` parity и улучшенный auth UX.
