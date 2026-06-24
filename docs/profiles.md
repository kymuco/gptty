# Profiles

Profiles let `gptty` keep separate auth and state files for different ChatGPT accounts or workflows.

A profile stores its own:

```text
auth_data.json
gptty_state.json
```

This prevents a personal account and a work account from sharing the same attached conversation state.

## Create and Use a Profile

Create a profile:

```bash
gptty profile create work
```

Make it the active profile:

```bash
gptty profile use work
```

After that, normal commands use `work` by default:

```bash
gptty auth refresh --mode wait
gptty ask "hello"
gptty attach https://chatgpt.com/c/...
gptty send "continue"
```

Check the current profile:

```bash
gptty profile current
```

List profiles:

```bash
gptty profile list
```

Show resolved paths:

```bash
gptty profile paths
gptty profile paths work
```

## One Command Override

Use `--profile` when one command should use a different profile without changing the active profile:

```bash
gptty ask --profile personal "hello from personal"
gptty --profile work ask "hello from work"
```

## Shell Session Override

Use `GPTTY_PROFILE` when a terminal session should keep using a specific profile:

```bash
export GPTTY_PROFILE=work
gptty ask "hello"
gptty send "continue"
```

This is useful when you have multiple terminals open with different accounts.

## Explicit File Paths

Explicit paths still win over profile defaults:

```bash
gptty ask --auth ./auth_data.json "hello"
gptty send --auth ./auth_data.json --state ./gptty_state.json "continue"
```

## Resolution Priority

`gptty` resolves auth and state paths in this order:

```text
1. --auth / --state explicit paths
2. --profile NAME
3. GPTTY_PROFILE
4. active_profile from config.toml
5. legacy local fallback: ./auth_data.json and ./gptty_state.json
```

If no profile is active and no override is provided, `gptty` keeps using the legacy local files. This preserves existing workflows.

## Storage Locations

On Linux/macOS-style systems, config and data are stored under platform-standard directories:

```text
~/.config/gptty/config.toml
~/.local/share/gptty/profiles/work/auth_data.json
~/.local/share/gptty/profiles/work/gptty_state.json
```

On Windows, `gptty` uses the standard roaming/local app data directories.

## Notes

Profiles do not copy or migrate auth data automatically. To set up a new profile, switch to it and refresh auth:

```bash
gptty profile use work
gptty auth refresh --mode wait
```

Conversation locking and live observation are planned as follow-up work. Profiles provide the storage foundation for those features.
