# SDK Boundary

`gptty` is a terminal product on top of `chatgpt-web-adapter`.

## Responsibilities

`chatgpt-web-adapter` owns:

- ChatGPT web-session transport
- backend request payload construction
- streaming response parsing
- conversation attach/read/status helpers
- tool approval protocol helpers
- upload and media backend behavior
- backend error details and request diagnostics

`gptty` owns:

- terminal commands
- stdin/stdout behavior
- interactive chat UX
- local CLI state and config
- auth capture UX wrappers
- output rendering and export formats
- shell-friendly exit codes

## Boundary Rule

CLI command modules should call `GpttyClient` instead of importing `chatgpt_web_adapter` directly.

`GpttyClient` is intentionally thin. It may normalize CLI-friendly arguments, but it should not reimplement backend payload logic, conversation tree traversal, status detection, approval protocol handling, or upload internals.

## Current State

PR1 adds the boundary layer only. The legacy `main.py` runtime is still present and still contains the old standalone backend implementation. Later PRs should migrate command flows to `GpttyClient` one path at a time.
