# Profiles, Locks, and Live Observation Roadmap

This document defines the planned direction for profile-aware config paths, conversation locks, and live run observation in `gptty`.

The goal is to make `gptty` behave like a normal installed CLI:

- work from any directory
- support multiple ChatGPT accounts
- make profile switching explicit and persistent
- avoid accidental concurrent writes to the same conversation
- expose enough local status to understand active commands without opening ChatGPT web

## PR14 - Profiles and Global Paths

Goal: make auth and state path resolution profile-aware while preserving current local-file workflows.

Planned commands:

```bash
gptty profile list
gptty profile current
gptty profile create work
gptty profile use work
gptty profile paths
```

Planned global/profile overrides:

```bash
gptty --profile work ask "hello"
GPTTY_PROFILE=work gptty ask "hello"
```

`gptty profile use work` should persist the active profile in global config. Future commands use that profile until the user switches again.

`--profile work` should apply only to the current command.

`GPTTY_PROFILE=work` should apply to the current shell/session and take precedence over the persisted active profile.

### Path Model

Linux/macOS-style layout:

```text
~/.config/gptty/config.toml
~/.local/share/gptty/profiles/default/auth_data.json
~/.local/share/gptty/profiles/default/gptty_state.json
~/.local/share/gptty/profiles/work/auth_data.json
~/.local/share/gptty/profiles/work/gptty_state.json
```

Windows should use platform-appropriate directories through `platformdirs` or an equivalent local helper.

### Resolution Priority

Path/profile resolution should be deterministic:

```text
1. --auth / --state explicit paths
2. --profile NAME
3. GPTTY_PROFILE
4. active_profile from config.toml
5. legacy local fallback: ./auth_data.json and ./gptty_state.json
```

Compatibility rule: existing commands such as this must continue to work:

```bash
gptty ask --auth ./auth_data.json "hello"
```

The existing local default files should remain supported as a fallback:

```text
./auth_data.json
./gptty_state.json
```

### Out of Scope for PR14

- conversation locks
- live run observation
- browser-side live sync
- automatic migration prompts

## PR15 - Conversation Locks

Goal: prevent two local `gptty` commands from mutating the same conversation at the same time.

Locks are local coordination files. They do not represent ChatGPT server state.

Planned lock files:

```text
profiles/<profile>/locks/auth.lock
profiles/<profile>/locks/state.lock
profiles/<profile>/locks/conversation-<conversation_id>.lock
```

Conversation locks should be held while a command is waiting for a reply in that conversation.

Commands that should use conversation locks:

```text
gptty send
gptty chat
```

Commands that only write profile state should use short state/auth locks:

```text
gptty attach
gptty auth refresh
gptty profile use
```

Read-only commands should not block on conversation locks by default:

```text
gptty messages
gptty status
gptty export
gptty auth status
gptty profile current
gptty profile list
```

### Lock UX

Default message when a conversation is already in progress:

```text
gptty: conversation in progress

This conversation is already waiting for a reply.
Wait for the current reply to finish, then try again.

Profile: work
Conversation: 6a3b9265-a8e8-83ed-9b96-3cd163ad7bb0
```

Timeout message:

```text
gptty: conversation still in progress

This conversation is still waiting for a reply.
Try again after the current reply finishes, or send to another conversation.

Profile: work
Conversation: 6a3b9265-a8e8-83ed-9b96-3cd163ad7bb0
Waited: 30s
```

Stale lock cleanup message:

```text
gptty: recovered previous session

A previous command did not finish cleanly, so gptty cleared its local lock.

Continuing...
```

### Lock Options

Planned options:

```bash
gptty send --wait-lock "continue"
gptty send --lock-timeout 120 "continue"
```

Suggested behavior:

- default waits briefly, then exits with a clear message
- `--wait-lock` waits longer using a documented default
- `--lock-timeout N` waits for up to `N` seconds

### Out of Scope for PR15

- sharing live output between processes
- replaying an active response
- remote/multi-machine locks

## PR16 - Run Observer and Live Status

Goal: let another local `gptty` command show what an active `gptty` run is doing.

This requires active commands to write local run events. A lock alone is not enough to reconstruct live status.

Planned run files:

```text
profiles/<profile>/runs/<run_id>.json
profiles/<profile>/runs/<run_id>.jsonl
```

A conversation lock should reference the active run:

```json
{
  "profile": "work",
  "conversation_id": "6a3b9265-a8e8-83ed-9b96-3cd163ad7bb0",
  "run_id": "...",
  "started_at": "2026-06-24T00:00:00Z",
  "pid": 12345,
  "command": "send"
}
```

Planned commands:

```bash
gptty observe
gptty observe <conversation-url-or-id>
gptty observe --profile work
gptty observe --status-only
gptty observe --from-start
```

Planned events:

```text
run_started
prompt_sent
waiting_for_reply
token_delta
required_action
completed
failed
heartbeat
```

Default behavior should show the current active run only, not the full conversation history.

### Observer UX

Status-only example:

```text
gptty: conversation in progress

Profile: work
Conversation: 6a3b9265...
Elapsed: 00:42

Waiting for ChatGPT...
```

Required-action example:

```text
gptty: action needed

ChatGPT is waiting for you to connect Gmail in the web UI.
Open the conversation, complete the card, then retry.

Profile: work
Conversation: 6a3b9265...
Elapsed: 00:34
```

### Observer Limitations

Live token observation is only reliable for commands launched by `gptty` that write local run events.

If a conversation is active only in ChatGPT web, `gptty observe` cannot attach to the browser stream. It may later support polling conversation status/messages through the SDK, but that is not the same as live stream observation.

### Out of Scope for PR16

- browser-side live sync
- remote event sync
- replaying full conversation history by default

## Recommended Sequence

```text
PR14 - Profiles and global paths
PR15 - Conversation locks
PR16 - Run observer and live status
```

Profiles come first because locks and observer state need stable per-profile storage paths.

Locks come second because observer should reference active lock/run metadata.

Observer comes third because it depends on active commands writing structured local run events.
