# Observe

`gptty observe` shows local live status for a conversation that is currently being used by another `gptty` command on the same machine.

It reads local run events written by `gptty send` and `gptty chat`.

## Usage

Observe the attached conversation:

```bash
gptty observe
```

Observe an explicit conversation:

```bash
gptty observe https://chatgpt.com/c/...
```

Show only status metadata:

```bash
gptty observe --status-only
```

Show run text/events from the start instead of only recent events:

```bash
gptty observe --from-start
```

Use a profile:

```bash
gptty observe --profile work
```

## Example Output

```text
gptty: conversation in progress

Profile: work
Conversation: 6a3b9265...
Elapsed: 00:42
Status: running
Last event: token_delta

Assistant:
I can help with that...
```

If there is no active local run:

```text
gptty: no active local run for this conversation

Conversation: 6a3b9265...

`gptty observe` can only show runs started by gptty on this machine.
```

## Limitations

`gptty observe` does not attach to a browser stream and does not read hidden state from the ChatGPT website.

It only observes commands that were started through `gptty` and are writing local run events.

If a conversation is active only in ChatGPT web, `gptty observe` cannot show live tokens for it.

## Storage

For profiles, run logs are stored under the profile directory:

```text
~/.local/share/gptty/profiles/work/runs/
```

For legacy local-file mode, run logs are stored next to the state file:

```text
.gptty_runs/
```
