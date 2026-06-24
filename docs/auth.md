# Auth Lifecycle

`gptty` uses an existing ChatGPT web session. It does not use the official OpenAI API and it does not use an OpenAI API key.

The local `auth_data.json` file contains captured web-session data such as:

- `accessToken`
- `cookies`
- browser headers
- optional proof or turnstile tokens

## Token Lifetime

ChatGPT web access tokens are temporary. In practice, a captured `accessToken` may need to be refreshed periodically, often after roughly 7-14 days, depending on the account/session behavior.

When the token expires, normal SDK-backed commands can fail until you capture fresh auth data.

## Check Auth Status

This command inspects the local auth file without opening a browser and without requiring auth-capture dependencies:

```bash
gptty auth status
```

Use a custom file:

```bash
gptty auth status --auth ./auth_data.json
```

JSON output for scripts:

```bash
gptty auth status --format json
```

The status command reports whether the file exists, whether a token is present, whether the JWT expiry is known, whether it is expired, and whether cookies, headers, proof token, or turnstile token are present.

## Refresh Auth Data

To capture fresh browser auth data:

```bash
gptty auth refresh --mode wait
```

`wait` mode is the safest default when you may need to log in again. It opens the browser, waits for the chat input to appear, and then asks you to send any message manually in the browser to trigger auth capture.

For an already logged-in browser session, `auto` mode is faster:

```bash
gptty auth refresh --mode auto
```

`auto` mode sends one probe prompt to trigger capture. The default probe prompt is `Hello`:

```bash
gptty auth refresh --mode auto --probe-prompt "Ping"
```

Use a custom output path:

```bash
gptty auth refresh --auth ./auth_data.json --mode wait
```

## Optional Dependencies

`gptty auth status` works with the base install.

`gptty auth refresh` requires browser auth-capture dependencies:

```bash
python -m pip install "gptty-web[auth]"
```

From a checkout, install the auth extra like this:

```bash
python -m pip install -e .[auth]
```

The auth extra currently includes `g4f`, `platformdirs`, and `zendriver`.

## File Format

New captures write `accessToken` as the canonical token field and also write `api_key` as a compatibility alias for older code paths.

Minimal shape:

```json
{
  "timestamp": "2026-06-24T00:00:00Z",
  "accessToken": "...",
  "api_key": "...",
  "cookies": {},
  "headers": {},
  "proof_token": null,
  "turnstile_token": null
}
```

Do not commit `auth_data.json`.
