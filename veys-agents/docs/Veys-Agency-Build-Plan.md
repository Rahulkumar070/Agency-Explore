# Veys agency CLI build plan

## The first job to finish

Give a solo agency owner one command to open a client engagement and pick up the next piece of work. Start with the path from a qualified lead to a reviewed proposal and a delivery kickoff. That path connects the owner's immediate sales goal to the work the agency must actually deliver after a sale.

For the first release, use one representative brief end to end. A bookstore wants a page for its monthly reading club, supplies its own calendar and photographs, and already has a booking form. Its spending ceiling is ₹30,000. The sales team should draft a discovery follow-up and proposed scope. After the operator reviews it, the delivery team should receive the accepted version, the original brief, open decisions and one specific next assignment. A change to the existing booking form, an agreed ₹30,000 fee or a promised launch date would each require evidence from the client.

## What the reference repository contributes

I inspected msitarzewski/agency-agents at commit `8ae6164602c95ca78828b148b9052460ee426885`. The count below includes Markdown files with named agent frontmatter inside declared division directories. Generated integration outputs and strategy documents are excluded. I counted 283 specialist definitions across 18 divisions, 17 tool targets in the manifest and four scenario runbooks. All roster references in those four runbooks resolved to source roles. This review covered the manifests, representative roles, campaign runbook, handoff formats, conversion and installation structure, and validation scripts. It did not evaluate the output quality of every specialist. [Source snapshot](https://github.com/msitarzewski/agency-agents/tree/8ae6164602c95ca78828b148b9052460ee426885)

| Upstream evidence | Veys design decision |
|---|---|
| The campaign roster has five core roles, five channel specialists and four support roles. Channel and support roles activate as needed. | Let the owner choose a business outcome. Start the smallest team that can produce the requested artifact. A one-headline brief should generally need one writer. |
| The handoff format describes the requested deliverable, quality criteria, evidence and next recipient. | Save each handoff as a record with the source project, approved draft version, next team and exact assignment. The next team can distinguish client requirements from internal proposals. |
| Sales, brand and QA profiles each define different work products and review expectations. | Give each original Veys role its own output and acceptance check. A scope specialist preserves fee status and ownership. A copywriter preserves the requested destination for the call to action. |
| Tool definitions, generated integration directories and installation scripts are separate from source roles. | Keep one Veys role catalog and one project engine. The CLI and optional messaging adapters invoke the same engine. Keep model providers separate from messaging platforms. |
| Repository checks validate role references and division consistency. | Require a contributor adding a role or workflow to supply one example brief, its expected artifact and a test that catches an actual failure. |

[Runbook manifest](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/strategy/runbooks.json) · [Handoff formats](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/strategy/coordination/handoff-templates.md) · [Tool manifest](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/tools.json) · [Roster validation](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/scripts/check-runbooks.sh)

Hermes provides a separate reference for terminal interaction, model selection and optional gateways. The Veys CLI, roles and workflows should be authored in this project. Both upstream references belong to their respective projects. The Agency Agents source lists the MIT license and AgentLand Contributors. Keep provenance for any future third-party dependency or distributed asset, including model weights. [Agency Agents license](https://github.com/msitarzewski/agency-agents/blob/8ae6164602c95ca78828b148b9052460ee426885/LICENSE) · [Hermes Agent](https://github.com/NousResearch/hermes-agent)

## Where the prototype stands

The Mac working tree has an interactive desk, client project board, twelve Veys specialists, SQLite checkpoints, tasks, draft revisions, approval, Markdown export and handoff. In a temporary workspace, the offline sample exported v1, preserved v1 after a correction, required fresh approval of v2 and rejected approval against the stale version. Repeating the same approved handoff returned the same receiving project ID. These checks establish the workflow mechanics. The last downloadable source archive is v0.3.0. The newer desk is local development work.

A live studio test on the Mac stopped when the small local model assigned the same copywriter twice. The validator caught it before specialist execution. An earlier live bookstore draft also added changes to the existing booking form. Fixing both is more valuable to a solo operator than adding more roles.

## Recommended build order

| Milestone | Implementation | Acceptance example |
|---|---|---|
| 1. Reliable lead-to-proposal workflow | Add one bounded plan-repair attempt for invalid live assignments. Preserve the first failure reason. Validate the repaired role, evidence and task list. Build a review view that shows the proposed scope next to the original client constraints. | A duplicate writer triggers one repair. A still-invalid plan gives an actionable error and starts zero workers. The bookstore proposal preserves the budget ceiling and client-owned assets. Interrupting and resuming a successful plan keeps completed drafts. |
| 2. Sales-to-delivery handoff | Build on versioned drafts and internal approval. Track client acceptance separately and make unresolved fees, dates, scope and asset ownership visible to the receiving team. | The delivery kickoff names the source version and next owner. Repeating the same handoff creates one project. Editing the sales draft leaves an earlier handoff traceable to the version used. |
| 3. Creative production and account updates | Add two original workflows, campaign production and recurring client reporting. Give each a brief type, eligible roles, expected files and example outputs. | An Instagram-only brief yields requested creative for that channel. A report computes a rate from supplied counts and flags missing inputs. The owner can see tasks waiting on a client. |
| 4. First connected workflow | Connect one actual service the agency already uses. A Notion project tracker is a sensible first choice if it is where client work lives. Keep an external record ID for each exported milestone. | Export one approved milestone to a test project with the correct owner and due date. A retry updates or reuses that item. A connection error leaves the local work recoverable. |
| 5. Contributor release | Package the standalone CLI, document setup for a local model and one hosted model, publish fixtures and contribution instructions, and check distribution contents and licenses. | A fresh installation completes the offline example. A separately authenticated model completes a real brief. A new contributor can add a role and run its evaluation. Public GitHub launch follows the owner's release decision. |

## What to measure

Keep the same briefs when comparing models or changing prompts. Record duplicate assignments, invented commitments, useful artifacts, corrective edits, run time and model calls per accepted draft. Count errors against the original brief. A passing schema proves that a plan can be parsed. Human review of a deliverable establishes whether it is actually usable.

The first milestone is complete when the owner can take a real lead through a reviewed proposal and reopen the project the next day with its facts, draft versions and outstanding decisions intact.
