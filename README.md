# gptty

English version. Russian version: [README.ru.md](README.ru.md)

Terminal client for existing ChatGPT web sessions.

> [!WARNING]
> Not the official OpenAI API.
> Uses an existing ChatGPT web session.
> Web backend behavior may change.

`gptty` is the successor to `webchat-openai-cli`. The project is being migrated from a standalone script into a terminal-native product powered by [`chatgpt-web-adapter`](https://github.com/kymuco/chatgpt-web-adapter).

The current release line keeps the existing interactive CLI working while the new package layout, command entrypoint, and SDK-backed internals are introduced step by step.

## Product Direction

```text
SDK = chatgpt-web-adapter
CLI = gptty
```

`gptty` is intended for terminal workflows:

```bash
gptty chat
gptty ask "explain this error"
git diff | gptty ask "review this patch"
gptty attach https://chatgpt.com/c/...
gptty messages --last 5
gptty status
gptty export --format md
```

`gptty ask` is the first SDK-backed command. The legacy interactive chat entrypoint remains available as `gptty chat` while the rest of the CLI is migrated in later PRs.

## Current Features

- one-shot SDK-backed prompts through `gptty ask`
- pipe-friendly prompts, for example `git diff | gptty ask "review this patch"`
- interactive terminal chat through the legacy `main.py` runtime
- streaming replies in the terminal
- latency metrics: `first_token`, `last_token`, `total`
- single local state file: `webchat_state.json`
- atomic writes for local state and `auth_data.json`
- image prompts through `/img`
- `auto` and `wait` auth capture modes
- English and Russian CLI localization
- transitional `gptty` console command

## Requirements

- Python 3.10+
- system `curl` available in `PATH`
- Chrome or Chromium for `auth_fetcher.py`
- valid `auth_data.json` for an existing ChatGPT web session

## Installation From Checkout

Create and activate a virtual environment:

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -e .[auth]
```

On Windows `cmd.exe`:

```cmd
python -m venv venv
venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -e .[auth]
```

The package distribution name is planned as `gptty-web` because the PyPI name `gptty` is already occupied. The installed command remains `gptty`.

## Get `auth_data.json`

Fast mode for an already logged-in browser session:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode auto
```

Wait mode if you need time to log in or register first:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode wait
```

In `wait` mode the browser stays open until the chat is ready. After that, send any message manually in the browser to trigger auth capture.

Optional: override the one-shot probe prompt used by `auto` mode:

```cmd
venv\Scripts\python.exe auth_fetcher.py --mode auto --probe-prompt "Ping"
```

Short alias for wait mode:

```cmd
venv\Scripts\python.exe auth_fetcher_wait.py
```

After a successful capture, `auth_data.json` will appear in the project directory.

## Run the CLI

One-shot SDK-backed prompt:

```bash
gptty ask "explain this error"
```

Pipe stdin into the prompt:

```bash
git diff | gptty ask "review this patch"
```

Disable streaming and print the final response:

```bash
gptty ask --no-stream "summarize this session"
```

Preferred transitional interactive command:

```bash
gptty chat
```

Legacy entrypoint, still supported:

```bash
python main.py
```

You can also override local paths:

```bash
gptty ask --auth ./auth_data.json --timeout 120 "hello"
gptty chat --auth ./auth_data.json --state ./webchat_state.json
```

## Useful Legacy Chat Commands

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

## Important Files

- `auth_data.json` - local auth data, do not commit it
- `webchat_state.json` - local chat history and runtime settings, do not commit it

## Notes

- `auth_data.json` is the primary auth source.
- `.env` is optional. If present, `accessToken` is used as a fallback even when `auth_data.json` is missing, but a full `auth_data.json` remains the most compatible setup.
- In `auto` mode, `auth_fetcher.py` sends one probe message to trigger capture. The default text is `"Hello"`, and you can override it with `--probe-prompt`.
- In `wait` mode, `auth_fetcher.py` does not send the probe automatically. Log in or register, then send any message manually in the browser to trigger capture.
- Do not mix `cookies` and `api_key/accessToken` from different accounts.
- Local state and auth files are written atomically to reduce the chance of truncated JSON after interruption.
- If `main.py` says that `curl` is missing, install system `curl.exe` and check `curl --version`.

## Troubleshooting

- `curl` not found
  Install system `curl.exe` and make sure `curl --version` works.
- `auth_data.json` is missing
  Run `python auth_fetcher.py --mode wait`, complete login in the browser, then send any message in the chat window.
- `ImportError: cannot import name 'nodriver'`
  Reinstall auth dependencies with `python -m pip install -e .[auth]`. Recent `g4f` releases use `zendriver` instead of the older `nodriver` package name.
- The wrong account opens in `auth_fetcher`
  The browser profile already contains another session. Log out there first, or use the wait mode and sign in to the intended account.
- Requests start failing after working before
  Your session cookies or `api_key/accessToken` may have expired. Regenerate `auth_data.json`.
- `gptty chat` starts but cannot answer
  Check that `auth_data.json` exists, `curl` is installed, and the captured browser session still belongs to the same account.

## Status

This repository is in transition from `webchat-openai-cli` to `gptty`.

PR0 establishes the package skeleton and console command. PR1 adds the SDK client boundary. PR2 adds the first SDK-backed command, `gptty ask`. Later PRs will add attach existing ChatGPT conversations, messages/status, export, richer pipe workflows, and improved auth UX.
