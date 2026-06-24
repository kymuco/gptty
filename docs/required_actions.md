# Required Actions

Some ChatGPT connector flows stop on a web UI card instead of returning normal assistant text. One example is asking ChatGPT to read Gmail before Gmail is connected. The ChatGPT website can show a card such as "Connect Gmail" / "Not now".

When `chatgpt-web-adapter` exposes this state through `get_required_action()`, `gptty ask` and `gptty send` print a terminal message instead of silently returning an empty response.

Example output:

```text
gptty: ChatGPT requires a web UI action before it can continue (oauth_required).
reason: missing_link
connector: connector_...
requested path: /connector_.../search_emails
available actions: oauth_redirect, deny
next step: open this conversation in ChatGPT web and complete the card there:
  https://chatgpt.com/c/...
then retry the command, or ask again without that connector/tool.
```

## What This Does

- detects required-action states after an empty SDK response
- prints the connector/action metadata when available
- points the user back to the ChatGPT conversation URL
- exits with status `1` so scripts can detect that the command did not complete normally

## What This Does Not Do

`gptty` does not connect Gmail, click OAuth buttons, or bypass ChatGPT web UI authorization. Connector linking still has to happen in ChatGPT web.

This behavior depends on `chatgpt-web-adapter` exposing `get_required_action()`. Older SDK versions still work, but they cannot surface these cards to `gptty`.
