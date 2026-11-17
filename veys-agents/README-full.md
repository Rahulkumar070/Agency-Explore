# Veys Agents

One local workspace for running a small agency's sales, creative, delivery and operations teams. Give the account manager a client brief. It selects specialists, gives each a concrete assignment, and hands their drafts to a reviewer and an editor. You get a Markdown work pack, a record of who produced it, and the lines from the brief behind each assignment.

## Open the agency desk

From the project folder run `./bin/veys` (or `python3 -m veys desk`). Type `example` for an offline project, `review` to read its draft, and `board` to list client work. The desk stores projects in `.veys/`. The local model lives in `models/`, previous model runs in `runs/`, and the downloadable source archive in `dist/`.

## Take a lead from proposal to kickoff

From the checkout, create a sales project, run its agents and compare their draft with the original client brief:

```sh
project=$(./bin/veys new --client "Demo bookstore" --title "Reading club proposal" --team sales --brief examples/client-brief.md)
./bin/veys work "$project"
./bin/veys review "$project"
```

Review groups source passages about scope, fees, dates and client inputs. It flags some common changes, including adding work to a form the brief only asks to link to. These are text checks. Read the original brief and the draft for issues they miss. To edit, save only the deliverable with `./bin/veys review "$project" --draft-only > proposal.md`. After editing, run:

```sh
./bin/veys revise "$project" --version 1 --file proposal.md --note "Corrected scope and asset owners"
./bin/veys approve "$project" --version 2
kickoff=$(./bin/veys handoff "$project" --version 2 --team delivery --owner "Delivery lead" \
  --assignment "Prepare the kickoff checklist" --open-items "Fee, dates and final booking URL")
./bin/veys intake "$kickoff"
./bin/veys work "$kickoff"
```

Internal approval makes a draft available for export and handoff. After receiving actual client confirmation, record it with `./bin/veys accept "$project" --version 2 --by "Client contact" --evidence "Confirmation reference"`. A handoff captures the acceptance status at creation. Running the same handoff again reopens that project. Revising the source creates a new version with its own approval and acceptance status. Earlier handoffs retain their original brief.

## Run with a real model or chat account

On the prepared Mac, run `python3 scripts/run-local.py` for a live bookstore brief. The launcher starts the local model and prints the work pack. For a cloud model, choose a preset with `python3 -m veys providers`, set `VEYS_PROVIDER` and `VEYS_MODEL`, and use `--ask-key` on your run. In Hermes, send `/veys sales <client brief>` to invoke the same team with the profile’s model. [Local, API key and messaging setup](docs/hermes.md).

## Try an offline run

From the checkout, with Python 3.11 or newer:

```sh
python3 -m veys catalog
python3 -m veys demo --team agency runs/campaign-demo
python3 -m veys status runs/campaign-demo
python3 -m veys show runs/campaign-demo > runs/campaign-demo/work-pack.md
```

The demo runs a fictional coffee subscription campaign with fixed responses. It needs no keys or additional packages. In the sample, the scope specialist preserves ₹45,000 as a budget ceiling, the copywriter drafts the page CTA, and the measurement specialist reports 12 checkout starts out of 240 visitors as 5%.

| Team | Available specialists | Use it for |
|---|---|---|
| sales | Qualification, pitch, scope | Discovery calls, follow-up copy and proposals |
| studio | Brand, copy, content | Campaign direction, production calendars and ready-to-edit copy |
| delivery | Web, production, QA | Kickoff, web journeys, milestones and acceptance tests |
| operations | Measurement, accounts, resourcing | Client updates, reporting and capacity planning |
| agency | All twelve | A brief that spans departments |

## Use a model for your own work

Start a server that supports OpenAI-style Chat Completions. Set its actual model ID. The default URL points to a local service. For a hosted provider, set its HTTPS base URL and provide `VEYS_API_KEY` if required.

```sh
export VEYS_BASE_URL=http://127.0.0.1:11434/v1
export VEYS_MODEL='your-installed-model-id'
python3 -m veys run examples/campaign.md runs/campaign --team agency --metrics examples/funnel.csv
python3 -m veys resume runs/campaign
```

A new run needs an unused folder. `resume` retries unfinished work. Use `show` to reopen a saved work pack and `status` to inspect completed stages and their durations. To run the original sequential discovery → proposal → delivery workflow, omit `--team` from a demo or live run. Existing run directories are supported.

The optional metrics CSV accepts the columns `period,visitors,checkout_starts`. Local code computes the checkout-start percentage for each period. Zero visitors produce an unknown rate. The metrics snapshot reaches the measurement and account specialists when selected, plus the reviewer and editor. The raw file path stays local.

## Use an existing assistant through files

This mode lets a person or an agent host supply the responses on the same computer. It needs no model server or credentials in Veys.

```sh
python3 -m veys run examples/campaign.md runs/assisted --team agency --via-files --metrics examples/funnel.csv
```

Open the requested JSON file under `runs/assisted/requests/`. Give its system and user messages to your chosen assistant. Save its reply as plain UTF-8 text in the corresponding `responses/<role>.txt`, then run `python3 -m veys resume runs/assisted`. Use a fresh conversation per specialist for isolated context. Repeat for review and editing. The same plan validator, evidence checks and checkpoints apply. If a reply fails validation, correct that response file and resume. Completed checkpoints take precedence over later edits to response files.

The included [campaign work pack](examples/campaign-work-pack.md) was produced through this exchange with an assistant supplying each response. The file workflow is a manual handoff. For an automatic Hermes connection, use the included chat plugin.

To export just the finished editor output for client review, run:

```sh
python3 -m veys show runs/assisted --final > runs/assisted/client-draft.md
```

## How delegation works

1. The manager selects one to four roles from the chosen team. The runtime validates each role, task and exact quote from the brief. For an invalid live plan the manager receives the validation error and gets one repair attempt. Progress retains the first reason. If the repair still fails validation, the run stops before any specialist starts.
2. Up to three specialists work concurrently. Each sees the brief and its own assignment. Their outputs are saved independently in SQLite.
3. The reviewer checks all completed drafts against the brief. The editor receives the drafts and review and writes the final work pack. Reports preserve the plan and internal review below the synthesis.
4. The run folder stores the original brief, roster, manager instructions, metrics and completed steps. The scheduler lock prevents two processes from dispatching the same run at once. Provider calls whose response was lost before checkpointing can be repeated on resume.

A successful managed run uses four to seven model requests, plus one if its plan needs repair. The scope here is draft production. Publishing content, sending email, changing a CRM, and browsing from inside a Veys worker are possible future integrations. A hosted model receives the brief and each call's assigned context. Stored Markdown and SQLite records contain client material in plain text.

## Measure and extend

```sh
python3 -m unittest discover -s tests -v
python3 -m evals
python3 -m evals --live --baseline > comparison.json
```

The first evaluation checks nine observable properties on fictional outputs across three desks. The live comparison runs both architectures with the same configured model and brief per desk. It saves the actual outputs alongside the checks. Read them to judge accuracy, usefulness and editing effort. Keyword checks can miss equivalent wording or accept a misleading sentence. The demo scores exercise fixtures only.

The optional `python3 -m pip install .` installs the `veys` command. The runtime has no third-party Python dependencies.

[Veys agency build plan](docs/Veys-Agency-Build-Plan.md) · [Contribution guide](CONTRIBUTING.md) · [MIT license](LICENSE)
