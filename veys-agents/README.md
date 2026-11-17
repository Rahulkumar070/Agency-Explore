# Veys Agents runtime

Veys is the optional execution companion included with Agency Explorer. Agency Explorer's browser interface helps people discover specialist roles, compare them, and prepare briefs. Veys runs selected agency teams locally, coordinates specialist drafts, reviews the results, and saves a Markdown work pack.

The two tools are independently runnable. The static browser app does not invoke Veys or transmit briefs to it.

## Requirements

- Python 3.11 or newer.
- No third-party Python packages for the standard-library workflow.
- A local OpenAI-compatible model server for automated model runs, or use the offline sample and file-assisted workflow.

## Try the offline sample

From the repository root:

```sh
cd veys-agents
./bin/veys
```

At the desk prompt, type `example`, then `review`. To run a deterministic command-line demo:

```sh
python3 -m veys catalog
python3 -m veys demo --team agency /tmp/agency-explorer-demo
python3 -m veys show /tmp/agency-explorer-demo
```

The demo uses fictional content and fixed responses. It requires no model server, API key, or third-party dependencies.

## Run a real project

Start an OpenAI-compatible Chat Completions server, then set its actual model ID and URL:

```sh
export VEYS_BASE_URL=http://127.0.0.1:11434/v1
export VEYS_MODEL='your-installed-model-id'
python3 -m veys run examples/campaign.md /tmp/my-campaign --team agency
python3 -m veys show /tmp/my-campaign
```

For a hosted provider, use its HTTPS endpoint and set `VEYS_API_KEY` in your shell environment when required. Never put credentials in project files or commits. Hosted providers receive the brief and assigned context. Veys stores outputs and SQLite data locally; treat them as potentially containing confidential client material.

For a human-assisted run without a model server, use `--via-files`. The CLI writes request files; a person supplies responses and resumes the run. See the [full Veys guide](README-full.md) for sales-to-kickoff handoffs, teams, review, evaluation, and Hermes integration.

## License and maintenance

Veys is distributed under its own [MIT license](LICENSE). Preserve this notice when copying or modifying the Veys subproject. Its source and tests are maintained under `veys-agents/`; run its standard-library tests from this directory with `python3 -m unittest discover -s tests -v`, or from the monorepo root with `npm run test:veys`.
