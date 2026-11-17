# Use Veys with Hermes and API keys

## Run a real model on this Mac

From the Veys checkout, run the included bookstore brief or pass your own UTF-8 text file. Each invocation prints its run folder and final work pack. The launcher starts a private loopback llama.cpp server, runs the team, and stops the server on exit.

```sh
python3 scripts/run-local.py
python3 scripts/run-local.py examples/campaign.md --team studio
```

The default local file is `models/qwen2.5-1.5b-instruct-q4_k_m.gguf` under the Veys checkout. For another machine install Python 3.11+ and a llama.cpp release with `llama-server` on PATH. Supply a downloaded instruction-tuned GGUF with `--model /path/to/model.gguf`. The Mac setup uses Qwen2.5-1.5B-Instruct Q4_K_M on CPU. A small local model is useful for testing the workflow. Review its output for invented prices, commitments and client facts before using a draft. If a run pauses, use `python3 scripts/run-local.py --resume runs/<run-folder>`. The [model weights](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct-GGUF) and [llama.cpp](https://github.com/ggml-org/llama.cpp) are separate downloads.

## Use your own API key

```sh
python3 -m veys providers
export VEYS_PROVIDER=openai
export VEYS_MODEL='your-enabled-chat-model-id'
python3 -m veys doctor --live --ask-key
python3 -m veys run examples/client-brief.md runs/first-api --team sales --ask-key
python3 -m veys show runs/first-api --final
```

Each `--ask-key` invocation prompts in Terminal with hidden input. For unattended runs, set the credential variable shown by `providers` in your service's environment. Veys reads it in memory. `doctor` checks settings locally. `doctor --live` sends one short request and can incur a provider charge. A complete managed team normally uses four to seven requests, plus one when an invalid live plan needs repair. With a hosted model, the provider receives the brief and the context for each stage.

| Provider preset | Credential variable |
|---|---|
| openai | OPENAI_API_KEY |
| anthropic | ANTHROPIC_API_KEY |
| gemini | GEMINI_API_KEY |
| openrouter | OPENROUTER_API_KEY |
| groq | GROQ_API_KEY |
| deepseek | DEEPSEEK_API_KEY |
| mistral | MISTRAL_API_KEY |
| xai | XAI_API_KEY |
| together | TOGETHER_API_KEY |
| fireworks | FIREWORKS_API_KEY |
| ollama, lmstudio | VEYS_API_KEY if your local server requires it |
| custom | VEYS_BASE_URL and optional VEYS_API_KEY |

Anthropic uses its native Messages API. The other hosted presets use each vendor's Chat Completions route. Choose a chat model available to your account. Providers that require an OAuth exchange, request signing or a different protocol can use the account configured inside Hermes where it supports that provider. A named preset refuses a different base URL to keep its key bound to that vendor. Use `custom` to supply a different destination and its own credential. Set `VEYS_PLAN_FORMAT=schema` only for a backend that supports JSON Schema response formats. The local launcher enables this automatically and asks for shorter drafts.

## Run the team inside a conversation

The plugin exposes `/veys` through Hermes's command registry and calls the active Hermes model through its plugin LLM API. Selecting a different provider with `hermes model` changes the model used by Veys in that profile. Key and channel setup stay in Hermes. The Veys specialists call the text model directly and receive no shell, browser or messaging tools.

**Optional messaging setup.** Install Hermes separately to use this adapter. From the Veys checkout link the plugin directory into that profile and enable it. The directory link below is for macOS/Linux. Use an unused plugin slot. For an owner-managed Python environment you can instead install the Veys package into the same environment as Hermes and use its packaged plugin entry point.

```sh
mkdir -p "${HERMES_HOME:-$HOME/.hermes}/plugins"
ln -s "$PWD/veys" "${HERMES_HOME:-$HOME/.hermes}/plugins/veys"
hermes plugins doctor "$PWD/veys" --ci
hermes plugins enable veys
hermes model
hermes gateway setup
hermes gateway
```

In a connected chat send `/veys sales Draft a discovery email for a bookstore. The client has a ₹30,000 ceiling. Fees are still open.` Expect a run ID and an edited draft in that conversation. If the model fails, correct its configuration and send `/veys resume RUN_ID` from the same user and conversation. An operator can inspect checkpoints under the active profile's `plugin-data/veys/` folder. Workspace paths and credentials are never accepted as chat command arguments for loading files or configuring the model.

| First channel to test | What you configure in Hermes | Acceptance check |
|---|---|---|
| Telegram | A BotFather bot token and your allowed Telegram user ID or DM pairing | DM the bot the sales brief and check the reply |
| Discord | A bot token, installation in your server, message permissions and allowed user | Invoke the command in a channel where the bot can read and reply |
| Slack | A Slack app and bot credentials for the configured connection mode, authorization and channel membership | Send the brief from the connected conversation |
| WhatsApp | Pair or configure the adapter for your chosen account and allow the test sender | Send the command from that sender and check the reply |
| Other Hermes adapters | Use the adapter-specific setup, authorization and supported command surface | Check that the adapter passes slash command text and stable sender identity to Hermes |

The local plugin returns text to Hermes. Channel transport, reply length, native command menus, gateway uptime and account permissions depend on the adapter. The external account test above is the final check for each installation. See the [official messaging matrix and platform setup](https://hermes-agent.nousresearch.com/docs/user-guide/messaging/), [plugin commands](https://hermes-agent.nousresearch.com/docs/developer-guide/plugins/) and [plugin model API](https://hermes-agent.nousresearch.com/docs/developer-guide/plugin-llm-access).

## Compatibility record

The local source review and integration test used NousResearch/hermes-agent commit `40d1e95f37e409f9f618f32c170661c66b86a4f4`. The relevant seams are [gateway dispatch](https://github.com/NousResearch/hermes-agent/blob/40d1e95f37e409f9f618f32c170661c66b86a4f4/gateway/run_inbound_hooks.py), [plugin model access](https://github.com/NousResearch/hermes-agent/blob/40d1e95f37e409f9f618f32c170661c66b86a4f4/agent/plugin_llm.py) and [profile-scoped storage](https://github.com/NousResearch/hermes-agent/blob/40d1e95f37e409f9f618f32c170661c66b86a4f4/plugins/plugin_storage.py). Hermes, model weights, account credentials and saved client runs are separate from the Veys MIT source archive.

### Checks performed on the prepared Mac

- A fresh `scripts/run-local.py` run processed the bookstore brief with the local Qwen model. It saved a manager plan, three specialist drafts, a review and an editor response. Comparing that response against the brief revealed an error: it proposed changes to the existing booking form although the client asked only for a link. Treat the edited work pack as a draft for review.
- The pinned Hermes checkout loaded the Veys manifest and registered its command. Invoking the registered command with the active local model returned a discovery email. A paused run resumed from saved checkpoints.
- The actual gateway selected the Veys command and returned usage text for synthetic events across all 22 values of its platform enum, which includes local and internal routes. This check exercised gateway dispatch. Vendor authentication, inbound transport and external message delivery require a connected account.
- The automated suite covers a full managed run over loopback HTTP, Anthropic request and response formatting, provider-specific key selection, HTTPS redirect handling, ownership of resumable chat runs, and the existing offline and file workflows.
