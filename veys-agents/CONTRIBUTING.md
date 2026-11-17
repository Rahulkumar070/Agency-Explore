# Contributing to Veys Agents

Run the project from a checkout with Python 3.11 or newer. All unit tests and the offline evaluation run without provider credentials.

```sh
python3 -m unittest discover -s tests -v
python3 -m evals
```

**Add a specialist.** Add a unique ID, desk, title and original instructions in `veys/catalog/specialists.toml`. Describe the artifact the role should deliver and which facts may need confirmation. Give the role a fictional case. If it participates in the offline demonstration, add its sample in `veys/team_sample.py`. Check that the manager can assign it and that sibling work stays isolated. The manager, reviewer and editor IDs are reserved.

**Report a bug.** Include the Python version, the command, the desk, and the smallest fictional brief that reproduces the behavior. Include expected and actual output. Replace client data and credentials with placeholders.

**Propose a change.** Explain which agency task improves and how someone can verify it. Include the test or before-and-after example. For a new integration, document which data it reads or sends, any external actions it can take, how retries behave, and applicable third-party terms. Original contributions use the project's MIT license.
