# Contributing to Agency Explorer

Thanks for helping improve the project. Small, focused pull requests are easiest to review.

## Before you start

- Search existing issues and pull requests to avoid duplicate work.
- For a large change, open an issue first to discuss the problem and scope.
- Do not include secrets, private client material, or personal data in source, issues, screenshots, or test fixtures.
- Changes to imported agent content must preserve the upstream license and source attribution. Prefer updating the importer or documenting a reproducible catalog refresh over hand-editing generated files.

## Set up locally

Requirements: Node.js 22 or later and Python 3.11 or later. The browser app itself is static; Node is used for checks and tests.

```sh
git clone https://github.com/Rahulkumar070/Agency-Explore.git
cd Agency-Explore
npm ci
npm run dev
```

Open `http://127.0.0.1:4377`.

## Make and verify a change

```sh
npm run check
npm test
npm run test:veys
node scripts/check-catalog.mjs
```

The Veys Agents Python project lives in `veys-agents/` and keeps its own README, contribution guide, and license. Run it from that directory with `python3 -m veys`, or use `npm run veys` from the repository root. Its standard-library tests can be run with `npm run test:veys`.

Keep generated catalog output consistent with `scripts/import-catalog.py`. When refreshing upstream content, record the full source commit and inspect the changed agent files, license, division and tool metadata, and runbook references.

For interface changes, check keyboard operation, readable focus, narrow layouts, and reduced-motion behavior. Keep examples clearly labeled as illustrative. Do not present task board state as evidence that an agent executed.

## Pull requests

Open a pull request against `main`, explain the user problem and resulting behavior, and include verification results. CI must pass before merge. Maintainers review and merge contributions; contributors do not push directly to `main`.

By submitting a contribution, you agree that it is distributed under the repository's MIT license. Upstream agent files retain the notices included with their source distribution.
