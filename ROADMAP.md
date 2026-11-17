# Implementation status

The first release implements the discovery and planning experience. The following service features need a separate implementation and configuration; no buttons simulate them.

| Feature              | Implemented foundation                                                     | Remaining acceptance criteria                                                                                                                                      |
| -------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Goal-based discovery | Keyword index, intent mapping, curated starting teams, filters             | Independently labeled query set; measured precision and recall; optional semantic retrieval with cited match reasons                                               |
| Agent profiles       | Exact source snapshots, missions, outputs, capability notes, source hashes | Human-reviewed inputs/prerequisites per role; host/version-specific capability checks                                                                              |
| Team builder         | Editable selections, saved teams, tool exports                             | Role-specific assignments, duplicate-responsibility detection, explicit dependencies                                                                               |
| Workflow workspace   | Runbook groups, task boards, status, custom milestones, handoff notes      | Task dependencies, run/output linking, durable concurrent edits                                                                                                    |
| Live execution       | Portable prompts, task briefs, installation commands                       | Server-side provider credentials, selected model, explicit start, persisted jobs, retries/cancel, time and token usage, output review gates, real tool integration |
| Quality evidence     | Source integrity checks, capability heuristics, review notebook            | Versioned task datasets, agent-versus-baseline blind comparisons, recorded models/settings, independent scoring, confidence intervals, regression history          |
| Personal workspace   | Browser persistence and validated backup import/export                     | Authenticated server storage, account recovery, device synchronization, conflict resolution, data export/deletion                                                  |
| Catalog updates      | Reproducible import script and pinned source revision                      | Automated reviewed snapshot updates, removed/renamed role migration, user-visible catalog change history                                                           |

## Execution service contract

When implementing execution, keep credentials on the server and identify each job by project, selected source hashes, model, input brief, and current status. A successful job must include actual provider output and usage or an explicit record that usage was unavailable. A timeout or disconnected request must not be labeled complete. Task board status alone must never imply a model ran.

Before dispatch, show the chosen roles, input context, provider, and limits. Each specialist receives only its own assignment and necessary context. Store errors and partial results. Provide cancel/retry and review before any publishing, messaging, or other external action.

## Evaluation contract

Use identical task/model settings with and without the specialist instructions. Randomize output order before judging; retain raw outputs, task rubrics, judges, uncertainty, costs, and limitations. Publish actual results only. Do not infer quality from profile wording, installation counts, or unverified community ratings.
