import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";

const catalog = JSON.parse(readFileSync(new URL("../dist/catalog.json", import.meta.url), "utf8"));
assert.ok(Array.isArray(catalog.agents) && catalog.agents.length > 0, "catalog has agents");
assert.ok(catalog.divisions && Object.keys(catalog.divisions).length > 0, "catalog has divisions");
assert.ok(catalog.tools && Object.keys(catalog.tools).length > 0, "catalog has installation tools");
assert.ok(Array.isArray(catalog.runbooks), "catalog has runbooks");
assert.match(catalog.revision, /^[a-f0-9]{40}$/, "catalog pins a full upstream commit SHA");
assert.equal(new Set(catalog.agents.map((agent) => agent.id)).size, catalog.agents.length, "agent IDs are unique");

for (const agent of catalog.agents) {
  assert.match(agent.id, /^[a-z0-9-]+$/, `safe agent id: ${agent.id}`);
  assert.ok(catalog.divisions[agent.division], `known division: ${agent.division}`);
  assert.ok(agent.name && agent.description && agent.source, `profile metadata: ${agent.id}`);
  const source = readFileSync(new URL(`../dist/agents/${agent.id}.md`, import.meta.url));
  const hash = createHash("sha256").update(source).digest("hex");
  assert.equal(hash, agent.sourceHash, `source hash: ${agent.id}`);
}

const ids = new Set(catalog.agents.map((agent) => agent.id));
for (const runbook of catalog.runbooks) {
  assert.ok(runbook.title && Array.isArray(runbook.roster), `runbook metadata: ${runbook.slug}`);
  for (const group of runbook.roster) {
    for (const id of group.agents) assert.ok(ids.has(id), `${runbook.slug} references ${id}`);
  }
}

console.log(`Catalog valid: ${catalog.agents.length} agents, ${Object.keys(catalog.divisions).length} divisions, ${catalog.runbooks.length} runbooks.`);
