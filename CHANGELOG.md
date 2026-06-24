# Changelog

All notable changes to this project should be documented in this file.

The format is intentionally lightweight. Keep entries focused on user-visible behavior, compatibility notes, and release-impacting changes.

## Unreleased

- feat: add profile-aware auth/state path resolution with `gptty profile` commands
- feat: add local conversation locks for `gptty send` and `gptty chat`
- feat: add `gptty observe` for local active run status and recent output
- docs: document profile usage, resolution priority, and storage paths
- docs: document conversation lock behavior and lock wait options
- docs: document observe usage and local live-status limitations

## 0.1.1 - 2026-06-24

- feat: show a clear terminal message when ChatGPT stops on a connector required-action card such as Gmail OAuth/linking
- changed: require `chatgpt-web-adapter>=0.1.5,<0.2.0` so required-action detection is available in supported installs

## 0.1.0

Initial `gptty-web` release candidate.

### Added

- package layout with the `gptty` console command.
- SDK client boundary powered by `chatgpt-web-adapter`.
- one-shot prompts through `gptty ask`.
- minimal SDK-backed interactive chat through `gptty chat`.
- legacy runtime fallback through `gptty chat --legacy`.
- stdin pipe support for `ask` and `send`.
- conversation attach, messages, status, send, and export commands.
- output formats for script-friendly workflows: `plain`, `json`, and `markdown` where supported.
- SDK-backed image prompt support for `gptty ask --image` and `gptty send --image`.
- auth inspection through `gptty auth status`.
- auth refresh wrapper through `gptty auth refresh`.
- English and Russian README documentation.
- auth lifecycle documentation in `docs/auth.md`.

### Changed

- `gptty` now treats `chatgpt-web-adapter` as the SDK engine instead of keeping web-session transport logic in the CLI layer.
- new auth captures write canonical `accessToken` plus the legacy-compatible `api_key` field.
- local state and auth files are written atomically.

### Compatibility Notes

- The PyPI distribution name is `gptty-web`; the installed command is `gptty`.
- The project uses existing ChatGPT web-session auth, not the official OpenAI API.
- `gptty auth refresh` requires optional browser-capture dependencies installed with `gptty-web[auth]`.
- `auth_data.json` may need periodic refresh when ChatGPT web-session auth expires.
