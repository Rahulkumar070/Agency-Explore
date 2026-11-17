import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { JSDOM } from "jsdom";
import * as core from "../dist/core.js";

const base = new URL("../dist/", import.meta.url);
const tick = () => new Promise((r) => setTimeout(r, 20));
async function boot(saved) {
  const dom = new JSDOM(readFileSync(new URL("index.html", base), "utf8"), {
    url: "https://agency.test/#/discover",
    runScripts: "outside-only",
    pretendToBeVisual: true,
  });
  const w = dom.window,
    errors = [],
    downloads = [];
  w.core = core;
  w.structuredClone = structuredClone;
  w.scrollTo = () => {};
  w.HTMLElement.prototype.scrollIntoView = () => {};
  w.HTMLDialogElement.prototype.showModal = function () {
    this.open = true;
  };
  w.HTMLDialogElement.prototype.close = function () {
    this.open = false;
  };
  w.fetch = async (path) => ({
    ok: true,
    json: async () =>
      JSON.parse(readFileSync(new URL(path.slice(1), base), "utf8")),
    text: async () => readFileSync(new URL(path.slice(1), base), "utf8"),
  });
  w.URL.createObjectURL = (blob) => {
    downloads.push(blob);
    return "blob:test";
  };
  w.URL.revokeObjectURL = () => {};
  w.HTMLAnchorElement.prototype.click = function () {};
  w.addEventListener("error", (ev) => errors.push(ev.error));
  if (saved)
    w.localStorage.setItem("agency-explorer-v1", JSON.stringify(saved));
  const code = readFileSync(new URL("app.js", base), "utf8").replace(
    /^import[\s\S]*?from ["']\.\/core\.js["'];\n/,
    "const {useCases, searchAgents, recommend, makeBrief, installCommand, escapeHtml:e, tokens}=globalThis.core;\n",
  );
  await w.eval("(async()=>{" + code + "})()");
  await tick();
  const $ = (s) => w.document.querySelector(s),
    click = (s) => {
      assert.ok($(s), s);
      $(s).click();
    },
    change = (s, value) => {
      assert.ok($(s), s);
      $(s).value = value;
      $(s).dispatchEvent(new w.Event("change", { bubbles: true }));
    },
    submit = (s) =>
      $(s).dispatchEvent(
        new w.Event("submit", { bubbles: true, cancelable: true }),
      ),
    route = async (path) => {
      w.location.hash = "/" + path;
      await tick();
    },
    state = () => JSON.parse(w.localStorage.getItem("agency-explorer-v1"));
  return { dom, w, $, click, change, submit, route, state, errors, downloads };
}

test("discovery, source profiles, favorites, comparison, and team state survive a reload", async () => {
  const t = await boot();
  assert.equal(t.$(".agent-card h3").textContent, "Frontend Developer");
  t.change("#search", "React website");
  t.submit("#search-form");
  await tick();
  assert.match(t.w.location.hash, /React/);
  assert.equal(t.$(".agent-card h3").textContent, "Frontend Developer");
  t.click("[data-action=favorite]");
  await tick();
  assert.equal(t.state().favorites.length, 1);
  t.click("[data-action=profile]");
  await tick();
  assert.ok(t.$("#detail").open);
  assert.match(
    t.$(".source-preview").textContent,
    /Frontend Developer Agent Personality/,
  );
  t.click("[data-action=profile-add]");
  await tick();
  assert.equal(t.state().team.length, 1);
  t.click("[data-action=close]");
  t.click("[data-action=compare]");
  await tick();
  await t.route("compare");
  assert.match(t.$(".compare-table").textContent, /Frontend Developer/);
  const t2 = await boot(t.state());
  assert.equal(
    t2.$("[data-action=favorite]").getAttribute("aria-pressed"),
    "true",
  );
  assert.match(t2.$("#nav").textContent, /Team builder1/);
  assert.deepEqual(t.errors, []);
  assert.deepEqual(t2.errors, []);
  t.dom.window.close();
  t2.dom.window.close();
});

test("brief generation, saving a team, editing a brief, and workflow handoffs are usable end to end", async () => {
  const t = await boot();
  await t.route("team");
  t.change("[name=name]", "Clothing storefront");
  t.change("[name=goal]", "Build an ecommerce website for a clothing brand");
  t.change("[name=constraints]", "Keep existing checkout");
  t.submit("#brief-form");
  await tick();
  assert.equal(t.state().team.length, 4);
  t.click("[data-action=save-team]");
  assert.equal(t.state().savedTeams.length, 1);
  t.click("[data-action=generate-brief]");
  assert.match(t.$("#brief-editor").value, /Keep existing checkout/);
  t.$("#brief-editor").value += "\nReviewed by project owner.";
  t.click("[data-action=save-brief]");
  assert.match(t.state().briefs[0].content, /Reviewed by project owner/);
  t.click("[data-action=create-project]");
  await tick();
  assert.equal(t.$("h1").textContent, "Clothing storefront");
  t.change(".task-status", "done");
  assert.equal(t.state().projects[0].tasks[0].status, "done");
  t.change("#project-notes", "Design ready; verify checkout keyboard flow.");
  t.click("[data-action=save-notes]");
  assert.match(t.state().projects[0].notes, /keyboard/);
  t.change("#task-form [name=title]", "Review mobile checkout");
  t.change("#task-form [name=owner]", "QA");
  t.submit("#task-form");
  assert.equal(
    t.state().projects[0].tasks.at(-1).title,
    "Review mobile checkout",
  );
  await t.route("workspace");
  assert.match(t.$("main").textContent, /Clothing storefront/);
  assert.deepEqual(t.errors, []);
  t.dom.window.close();
});

test("runbooks create the selected groups, installation text updates per tool, and exports initiate", async () => {
  const t = await boot();
  await t.route("workflows");
  t.click("[data-action=runbook]");
  assert.ok(t.$("#runbook-form"));
  t.submit("#runbook-form");
  await tick();
  assert.equal(t.state().projects[0].tasks.length, 1);
  assert.equal(t.state().team.length, 9);
  t.click("[data-action=project-install]");
  assert.match(t.$("#install-code").textContent, /claude-code/);
  t.change("#tool", "cursor");
  assert.match(t.$("#install-code").textContent, /--tool cursor/);
  t.click("[data-action=download-roster]");
  assert.equal(t.downloads.length, 1);
  t.click("[data-action=close]");
  await t.route("workspace");
  t.click("[data-action=export-workspace]");
  assert.equal(t.downloads.length, 2);
  assert.deepEqual(t.errors, []);
  t.dom.window.close();
});

test("malformed saved state recovers and imported markup renders as text", async () => {
  const t = await boot({
    favorites: [{}, "engineering-frontend-developer"],
    projects: [{ id: "x", name: "<img src=x onerror=alert(1)>", tasks: [] }],
  });
  await t.route("workspace");
  assert.equal(t.$("main img"), null);
  assert.match(t.$("main").textContent, /<img src=x/);
  assert.deepEqual(t.errors, []);
  t.dom.window.close();
});

test("examples, review notes, and shareable skill filters work", async () => {
  const t = await boot();
  t.change("#skill", "React");
  await tick();
  assert.match(t.w.location.hash, /tag=React/);
  assert.ok(
    [...t.w.document.querySelectorAll(".agent-card")].every((el) =>
      el.textContent.includes("React"),
    ),
  );
  await t.route("examples");
  t.click("[data-action=use-example]");
  await tick();
  assert.equal(
    t.$("[name=name]").value,
    "A storefront that feels like your brand",
  );
  assert.equal(t.state().team.length, 4);
  await t.route("quality");
  t.change("#review-form [name=environment]", "Model X, local");
  t.change(
    "#review-form [name=notes]",
    "Checked source links; output requires review.",
  );
  t.submit("#review-form");
  assert.equal(t.state().reviews.length, 1);
  assert.match(t.$("main").textContent, /Model X, local/);
  assert.deepEqual(t.errors, []);
  t.dom.window.close();
});

test("workspace backups round-trip through the replacement confirmation and reject invalid imports", async () => {
  const t = await boot();
  t.click("[data-action=favorite]");
  await tick();
  await t.route("workspace");
  t.click("[data-action=export-workspace]");
  const exported = await new Promise((resolve, reject) => {
    const reader = new t.w.FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsText(t.downloads[0]);
  });
  const data = JSON.parse(exported);
  assert.equal(data.format, "agency-explorer-v1");
  data.favorites = [];
  data.savedTeams = [
    {
      id: "saved",
      name: "Imported team",
      agents: ["engineering-frontend-developer"],
    },
  ];
  const input = t.$("#import-workspace");
  Object.defineProperty(input, "files", {
    value: [{ size: 1000, text: async () => JSON.stringify(data) }],
    configurable: true,
  });
  input.dispatchEvent(new t.w.Event("change", { bubbles: true }));
  await tick();
  assert.equal(
    t.state().favorites.length,
    1,
    "import must not replace work before confirmation",
  );
  t.click("#confirm-import");
  assert.equal(t.state().favorites.length, 0);
  assert.equal(t.state().savedTeams[0].name, "Imported team");
  const invalid = t.$("#import-workspace");
  Object.defineProperty(invalid, "files", {
    value: [{ size: 20, text: async () => "{broken json" }],
    configurable: true,
  });
  invalid.dispatchEvent(new t.w.Event("change", { bubbles: true }));
  await tick();
  assert.equal(t.state().savedTeams.length, 1);
  assert.match(t.$("#toast").textContent, /Could not read/);
  assert.deepEqual(t.errors, []);
  t.dom.window.close();
});
