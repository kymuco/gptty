# Conversation Locks

`gptty` uses local conversation locks to avoid sending multiple prompts to the same conversation at the same time.

This is local coordination. It does not mean ChatGPT is down or busy. It means another `gptty` command has already started a request for that conversation and has not finished yet.

## Default Behavior

When a conversation is already waiting for a reply, `gptty send` and `gptty chat` stop before sending another prompt:

```text
gptty: conversation in progress

This conversation is already waiting for a reply.
Wait for the current reply to finish, then try again.

Profile: work
Conversation: 6a3b9265-a8e8-83ed-9b96-3cd163ad7bb0
```

## Wait For The Lock

Wait longer before failing:

```bash
gptty send --wait-lock "continue"
gptty chat --wait-lock
```

Use an explicit timeout:

```bash
gptty send --lock-timeout 120 "continue"
gptty chat --lock-timeout 120
```

If the conversation is still in progress after the timeout:

```text
gptty: conversation still in progress

This conversation is still waiting for a reply.
Try again after the current reply finishes, or send to another conversation.

Profile: work
Conversation: 6a3b9265-a8e8-83ed-9b96-3cd163ad7bb0
Waited: 30s
```

## Stale Locks

If a previous command exits unexpectedly, a local lock file may remain. When the lock is old enough, `gptty` clears it and continues:

```text
gptty: recovered previous session

A previous command did not finish cleanly, so gptty cleared its local lock.

Continuing...
```

## Storage

For profiles, locks are stored inside the profile directory:

```text
~/.local/share/gptty/profiles/work/locks/
```

For legacy local-file mode, locks are stored next to the state file:

```text
.gptty_locks/
```

## Notes

- `gptty send --new` does not lock before sending because the conversation does not exist yet.
- Read-only commands such as `messages`, `status`, and `export` do not use conversation locks.
- Live observation is planned separately. Locks only prevent unsafe concurrent writes; they do not stream another command's output.
