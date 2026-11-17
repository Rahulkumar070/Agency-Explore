# Agency Explorer

A browser-based directory and planning workspace built around [Agency Agents](https://github.com/msitarzewski/agency-agents). Discover specialists, compare roles, assemble a team, and turn a goal into a project brief and workflow board.

## Run locally

Requires Python 3 and a modern browser. The application has no runtime package dependencies or build step.

```sh
npm run dev
```

Open http://127.0.0.1:4377. An equivalent command is `python3 -m http.server 4377 --bind 127.0.0.1 --directory dist`.

## Available now

- The real catalog: 283 agents across 18 divisions, imported from upstream commit `8ae6164602c95ca78828b148b9052460ee426885`.
- Goal and keyword search, six use cases, division and skill filters, sorting, pagination, and shareable search URLs.
- Source-backed profiles, mission and deliverable summaries, related specialists, copyable instructions, and direct profile links.
- Side-by-side comparison of up to three agents.
- Team suggestions using transparent keyword matching and curated role mappings; manual additions and removals.
- Structured brief generation with editable text, copy/download, and saving to the workspace.
- Favorites, recent profiles, saved teams, project briefs, and workspace JSON export/import.
- Four upstream runbooks with selectable role groups and editable project boards.
- Task status tracking, custom milestones, deliverable links and handoff notes, and project export.
- Per-tool installation commands generated from upstream tool metadata; agent roster download.
- Clearly labeled illustrative examples and a local evidence notebook.
- Snapshot provenance, source hashes, runbook integrity validation, and heuristic capability notes.
- Responsive layouts, keyboard navigation, native modal dialogs, and reduced-motion support.

## Storage and execution boundaries

Personal work is stored in `localStorage` under `agency-explorer-v1`. It remains in that browser and origin. Export a workspace backup before clearing browser data or moving devices. The import flow validates the format and asks before replacing existing work. There are no accounts, cloud synchronization, or model API credentials in this version.

The app provides discovery, planning, and exports. It does not execute agents, install local files, or independently verify their output quality. Installation guides use upstream scripts in the user's terminal. Project statuses record user-entered progress. Agent instructions remain verbatim upstream source; capability notes identify potentially misleading memory language and script references for review. They are heuristics, not comprehensive audits.

Team recommendations are deterministic, not semantic embeddings or an LLM router. Generic requests favor broadly applicable specialists; explicit tools can select narrower specialists. They are suggestions users should review.

## Refresh the catalog

Download and extract a reviewed upstream revision, then run:

```sh
python3 scripts/import-catalog.py /absolute/path/to/agency-agents FULL_COMMIT_SHA
npm test
```

The importer reads upstream divisions, tools, agent frontmatter and headings, and runbook rosters. It writes `dist/catalog.json`, individually loaded `dist/agents/*.md`, and the upstream license. The full commit SHA pins source links to the imported content. Structural checks reject duplicate source IDs and the test suite rejects unresolved runbook references. Fetching a new snapshot does not alter user workspace data.

## Verify

```sh
npm ci
npm run check
npm test
```

Tests cover catalog integrity, recommendation intent, search ranking, composed filters, source hashes, generated briefs, command input validation, HTML escaping, persisted workspace state, source profile loading, comparison, team editing, runbook selection, project progress, review notes, and export initiation. UI behavior tests use JSDOM; they do not establish visual layout or actual tool installation compatibility. The initial desktop screen was inspected in Brave. Full mobile browser QA remains to be performed.

## Source layout

- `dist/index.html`, `style.css`: responsive interface and layout.
- `dist/app.js`: routing, views, forms, local persistence, exports, project boards.
- `dist/core.js`: pure search, recommendation, brief, and command helpers.
- `scripts/import-catalog.py`: reproducible upstream ingestion.
- `tests/`: catalog, core logic, and interaction tests.
- `.openai/hosting.json`: private Sites deployment identity and static directory.

## Further implementation

The next stage needs a server and explicit provider configuration: actual task dispatch, run history and logs, retry/cancel, durable user accounts and synchronization, and model/task-specific evaluations. See [ROADMAP.md](ROADMAP.md) for acceptance criteria. No generated output should be presented as a completed live agent run before that integration exists.

Agent source content is licensed under the upstream MIT license retained in [dist/UPSTREAM-LICENSE.txt](dist/UPSTREAM-LICENSE.txt). This is an independent explorer, not the upstream project's official desktop app.
