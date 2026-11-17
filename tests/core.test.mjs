import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createHash } from "node:crypto";
import {
  caseFor,
  searchAgents,
  recommend,
  makeBrief,
  installCommand,
  escapeHtml,
} from "../dist/core.js";
const c = JSON.parse(
  readFileSync(new URL("../dist/catalog.json", import.meta.url)),
);
test("catalog retains unique source identities, exact content hashes and resolvable runbooks", () => {
  assert.equal(new Set(c.agents.map((a) => a.id)).size, c.agents.length);
  assert.ok(c.agents.length > 250);
  for (const a of c.agents) {
    assert.ok(c.divisions[a.division]);
    const content = readFileSync(
      new URL("../dist/agents/" + a.id + ".md", import.meta.url),
    );
    assert.equal(
      createHash("sha256").update(content).digest("hex"),
      a.sourceHash,
    );
  }
  for (const r of c.runbooks)
    for (const g of r.roster)
      for (const id of g.agents)
        assert.ok(
          c.agents.some((a) => a.id === id),
          id,
        );
});
test("goal intent distinguishes a slow site from a new website", () => {
  assert.equal(caseFor("My website is slow").id, "performance");
  assert.equal(caseFor("Build a clothing ecommerce website").id, "website");
  assert.equal(caseFor("Please review app security").id, "security");
  assert.equal(caseFor("analyze customer data").id, "data");
  assert.equal(caseFor("something totally unspecified"), null);
});
test("search ranks an exact specialist and composes division and technology filters", () => {
  assert.equal(
    searchAgents(c.agents, { q: "Frontend Developer" })[0].name,
    "Frontend Developer",
  );
  assert.equal(
    searchAgents(c.agents, { q: "React website" })[0].name,
    "Frontend Developer",
  );
  const results = searchAgents(c.agents, {
    division: "engineering",
    tag: "React",
  });
  assert.ok(results.length > 0);
  assert.ok(
    results.every(
      (a) => a.division === "engineering" && a.tags.includes("React"),
    ),
  );
  assert.equal(searchAgents(c.agents, { q: "zzzzzzzznomatch" }).length, 0);
});
test("team suggestions favor general specialists for a general goal and explicit tools for specific goals", () => {
  const marketing = recommend(c.agents, "Create a content strategy");
  assert.equal(marketing[0].name, "Content Creator");
  const performance = recommend(c.agents, "My website is slow");
  assert.ok(performance.some((a) => a.name === "Database Optimizer"));
  const wordpress = recommend(c.agents, "Improve WordPress performance");
  assert.match(wordpress[0].name, /WordPress/);
  assert.equal(new Set(performance.map((a) => a.id)).size, performance.length);
});
test("brief exports preserve user constraints and selected specialist identities", () => {
  const a = c.agents.find((a) => a.name === "Frontend Developer");
  const brief = makeBrief({
    name: "Store launch",
    goal: "Accessible storefront",
    constraints: "Keep the existing checkout",
    team: [a],
  });
  assert.match(brief, /Keep the existing checkout/);
  assert.match(brief, /Frontend Developer/);
  assert.match(brief, /Acceptance criteria/);
});
test("installation text accepts real slugs and rejects shell syntax", () => {
  for (const a of c.agents)
    assert.doesNotThrow(() => installCommand("claude-code", [a.id]));
  assert.match(
    installCommand("cursor", ["engineering-frontend-developer"]),
    /--tool cursor --agent engineering-frontend-developer/,
  );
  assert.throws(() => installCommand("cursor; rm -rf", ["test"]));
  assert.throws(() => installCommand("cursor", ["$(whoami)"]));
  assert.throws(() => installCommand("cursor", []));
});
test("HTML rendering escapes imported text and source code", () => {
  assert.equal(
    escapeHtml('<img src=x onerror="alert(1)">'),
    "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;",
  );
});
