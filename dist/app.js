import {
  useCases,
  searchAgents,
  recommend,
  makeBrief,
  installCommand,
  escapeHtml as e,
  tokens,
} from "./core.js";

const $ = (s, root = document) => root.querySelector(s);
const main = $("#main"),
  dialog = $("#detail");
const blank = {
  favorites: [],
  team: [],
  compare: [],
  recent: [],
  projects: [],
  savedTeams: [],
  briefs: [],
  reviews: [],
  draft: { name: "", goal: "", stack: "", constraints: "", deliverables: "" },
  tool: "claude-code",
};
let state,
  storageAvailable = true,
  catalog,
  agents,
  byId,
  params,
  page,
  toastTimer;
try {
  state = normalize(
    JSON.parse(localStorage.getItem("agency-explorer-v1") || "null") || blank,
  );
} catch {
  state = structuredClone(blank);
  storageAvailable = false;
}
function normalize(input) {
  if (!input || typeof input !== "object" || Array.isArray(input))
    throw Error("Invalid workspace");
  const out = structuredClone(blank);
  for (const k of ["favorites", "team", "compare", "recent"])
    out[k] = Array.isArray(input[k])
      ? input[k]
          .filter((s) => typeof s === "string" && /^[a-zA-Z0-9_-]+$/.test(s))
          .slice(0, k === "compare" ? 3 : 500)
      : [];
  for (const k of ["projects", "savedTeams", "briefs", "reviews"])
    out[k] = Array.isArray(input[k])
      ? input[k]
          .filter((x) => x && typeof x === "object" && !Array.isArray(x))
          .slice(0, 200)
      : [];
  if (input.draft && typeof input.draft === "object")
    for (const k of Object.keys(out.draft))
      out.draft[k] = String(input.draft[k] || "").slice(0, 20000);
  if (typeof input.tool === "string" && /^[a-z0-9-]+$/.test(input.tool))
    out.tool = input.tool;
  out.projects = out.projects
    .filter(
      (p) =>
        typeof p.id === "string" &&
        typeof p.name === "string" &&
        Array.isArray(p.tasks),
    )
    .map((p) => ({
      ...p,
      tasks: p.tasks
        .filter(
          (t) => t && typeof t.id === "string" && typeof t.title === "string",
        )
        .map((t) => ({
          ...t,
          status: ["todo", "doing", "done"].includes(t.status)
            ? t.status
            : "todo",
        })),
    }));
  out.savedTeams = out.savedTeams.filter(
    (t) =>
      typeof t.id === "string" &&
      typeof t.name === "string" &&
      Array.isArray(t.agents),
  );
  out.briefs = out.briefs.filter(
    (b) =>
      typeof b.id === "string" &&
      typeof b.name === "string" &&
      typeof b.content === "string",
  );
  out.reviews = out.reviews.filter(
    (r) => typeof r.agent === "string" && typeof r.notes === "string",
  );
  return out;
}
function persist() {
  try {
    localStorage.setItem("agency-explorer-v1", JSON.stringify(state));
  } catch {
    storageAvailable = false;
    toast("Storage unavailable. Export your workspace to keep changes.");
  }
  nav();
}
function toast(s) {
  $("#toast").textContent = s;
  $("#toast").classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => $("#toast").classList.remove("visible"), 3200);
}
function download(name, content, type = "text/plain") {
  const u = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = u;
  a.download = name;
  a.click();
  setTimeout(() => URL.revokeObjectURL(u), 1000);
}
async function copy(s) {
  try {
    await navigator.clipboard.writeText(s);
    toast("Copied to clipboard");
  } catch {
    download("agency-copy.txt", s);
    toast("Clipboard unavailable. Downloaded the text.");
  }
}
const uid = () => globalThis.crypto.randomUUID();
const getTeam = () => state.team.map((i) => byId.get(i)).filter(Boolean);
const divName = (id) => catalog.divisions[id]?.label || id;
function tint(a) {
  return `${catalog.divisions[a.division]?.color || "#7a9d4c"}12`;
}
function go(route, query = {}) {
  const p = new URLSearchParams(query);
  location.hash = `/${route}${p.size ? "?" + p : ""}`;
}
function currentParams() {
  return Object.fromEntries(params);
}
function setFilter(key, value) {
  const obj = currentParams();
  if (value) obj[key] = value;
  else delete obj[key];
  delete obj.p;
  go("discover", obj);
}
const navItems = [
  ["discover", "⌕", "Discover"],
  ["workflows", "◇", "Workflows"],
  ["team", "♧", "Team builder"],
  ["workspace", "▦", "My workspace"],
  ["examples", "▤", "Examples"],
  ["quality", "◉", "Quality & sources"],
];
function nav() {
  if (!catalog) return;
  $("#nav").innerHTML =
    navItems
      .map(
        ([id, icon, label]) =>
          `<a class="nav-link ${page === id ? "active" : ""}" href="#/${id}" ${page === id ? 'aria-current="page"' : ""}><span class="nav-icon">${icon}</span>${label}${id === "team" && state.team.length ? `<span class="nav-count">${state.team.length}</span>` : ""}${id === "workspace" && state.favorites.length ? `<span class="nav-count">${state.favorites.length}</span>` : ""}</a>`,
      )
      .join("") +
    '<a class="nav-link ' +
    (page === "guide" ? "active" : "") +
    '" href="#/guide"><span class="nav-icon">↗</span>Getting started</a>';
  dock();
}
function dock() {
  let old = $(".compare-dock");
  if (old) old.remove();
  if (state.compare.length && page !== "compare") {
    let d = document.createElement("div");
    d.className = "compare-dock";
    d.innerHTML = `<span>${state.compare.length} of 3 agents selected</span><a href="#/compare">Compare agents ↗</a><button class="icon-button" data-action="clear-compare" aria-label="Clear comparison" style="color:white">×</button>`;
    document.body.append(d);
  }
}
function head(kicker, title, desc) {
  return `<div class="page-head"><div class="eyebrow">${kicker}</div><h1>${title}</h1><p class="intro">${desc}</p></div>`;
}
function empty(title, desc, link = "", label = "Explore agents") {
  return `<div class="empty"><h3>${title}</h3><p>${desc}</p>${link ? `<a class="button primary" href="${link}">${label} ↗</a>` : ""}</div>`;
}
function card(a) {
  let saved = state.favorites.includes(a.id),
    comp = state.compare.includes(a.id),
    added = state.team.includes(a.id);
  return `<article class="agent-card"><div class="card-head"><span class="agent-avatar" style="--tint:${tint(a)}">${e(a.emoji)}</span><button class="icon-button ${saved ? "saved" : ""}" data-action="favorite" data-id="${e(a.id)}" aria-label="${saved ? "Unsave" : "Save"} ${e(a.name)}" aria-pressed="${saved}">${saved ? "★" : "☆"}</button></div><div class="division-label">${e(divName(a.division))}</div><h3><button class="title-button" data-action="profile" data-id="${e(a.id)}">${e(a.name)}</button></h3><p class="agent-desc">${e(a.vibe || a.description)}</p><div class="tags">${a.tags
    .slice(0, 3)
    .map(
      (t) =>
        `<button class="tag" style="cursor:pointer" data-action="tag" data-tag="${e(t)}">${e(t)}</button>`,
    )
    .join(
      "",
    )}</div><div class="card-footer"><button data-action="compare" data-id="${e(a.id)}" aria-pressed="${comp}">${comp ? "☑" : "⊞"} &nbsp; Compare</button><button data-action="add" data-id="${e(a.id)}" aria-label="${added ? "Remove" : "Add"} ${e(a.name)} ${added ? "from" : "to"} team">${added ? "✓ In team" : "+ Add to team"}</button></div></article>`;
}
function discover() {
  const q = params.get("q") || "",
    division = params.get("division") || "",
    tag = params.get("tag") || "",
    caseId = params.get("case") || "",
    sort = params.get("sort") || "relevance";
  const results = searchAgents(agents, { q, division, tag, caseId, sort }),
    totalPages = Math.max(1, Math.ceil(results.length / 12));
  let n = Math.max(1, Math.min(totalPages, parseInt(params.get("p")) || 1));
  const topDivs = [
    "engineering",
    "design",
    "marketing",
    "product",
    "testing",
    "security",
  ];
  main.innerHTML = `<section class="hero"><div><div class="eyebrow">GOOD IDEAS DESERVE GREAT TEAMS</div><h1>Find your people.<br>Build <em>something great.</em></h1><p class="intro">A world of AI specialists, one place to find them. Discover the right<br class="desktop-break"> expertise for whatever you’re working on.</p><div class="stats"><span><strong>${agents.length}</strong> specialists</span><span><strong>${Object.keys(catalog.divisions).length}</strong> divisions</span><span><strong>∞</strong> possibilities</span></div></div><div class="hero-art" aria-hidden="true"><div class="orbit"></div><div class="orbit"></div><div class="orbit"></div><div class="art-center">✳</div><span class="orb one">⌘</span><span class="orb two">↗</span><span class="orb three">◇</span></div></section><form id="search-form" class="search-wrap" role="search"><span class="search-icon" aria-hidden="true">⌕</span><input id="search" name="q" aria-label="Search agents by name, skill, or goal" value="${e(q)}" placeholder="What do you want to build? Try ‘React website’ or ‘content strategy’"><kbd class="keycap">/</kbd><button class="button primary" type="submit">Find agents ↗</button></form><div class="section-heading"><h2>Start with what you want to do</h2><p>A little direction goes a long way.</p></div><div class="use-cases">${useCases.map((c) => `<button class="use-case ${caseId === c.id ? "selected" : ""}" data-action="use-case" data-id="${c.id}" aria-pressed="${caseId === c.id}"><span class="use-case-icon">${c.icon}</span><span><strong>${c.name}</strong><small>${c.hint}</small></span><span class="arrow">↗</span></button>`).join("")}</div><section id="directory"><div class="directory-top"><h2>Meet the specialists <span>${results.length}</span></h2><div class="directory-tools"><select id="division" aria-label="Filter by division"><option value="">All divisions</option>${Object.entries(
    catalog.divisions,
  )
    .map(
      ([id, d]) =>
        `<option value="${id}" ${division === id ? "selected" : ""}>${e(d.label)}</option>`,
    )
    .join(
      "",
    )}</select><select id="skill" aria-label="Filter by skill"><option value="">All skills</option>${[
    ...new Set(agents.flatMap((a) => a.tags)),
  ]
    .sort()
    .map(
      (t) =>
        `<option value="${e(t)}" ${tag === t ? "selected" : ""}>${e(t)}</option>`,
    )
    .join(
      "",
    )}</select><select id="sort" aria-label="Sort agents"><option value="relevance" ${sort === "relevance" ? "selected" : ""}>Most relevant</option><option value="name" ${sort === "name" ? "selected" : ""}>Name A–Z</option></select></div></div><div class="chips"><button class="chip ${!division ? "active" : ""}" data-action="division" data-id="">All specialists</button>${topDivs.map((id) => `<button class="chip ${division === id ? "active" : ""}" data-action="division" data-id="${id}">${e(divName(id))}</button>`).join("")}${tag ? `<button class="chip active" data-action="clear-tag">${e(tag)} ×</button>` : ""}${q || division || tag || caseId ? '<button class="text-button" data-action="reset-filters">Reset filters</button>' : ""}</div><div class="results-label"><span>${results.length ? `${(n - 1) * 12 + 1}–${Math.min(n * 12, results.length)} of ${results.length} specialists` : "No matching specialists"}${caseId ? " · " + e(useCases.find((c) => c.id === caseId)?.name || "") : ""}</span><button class="text-button" data-action="share-search">Copy search link ↗</button></div><div class="agent-grid">${
    results
      .slice((n - 1) * 12, n * 12)
      .map(card)
      .join("") ||
    empty(
      "Let’s try another direction",
      "Try a broader skill or reset the filters to see every specialist.",
    )
  } </div>${totalPages > 1 ? `<div class="pagination"><button class="button small" data-action="page" data-page="${n - 1}" ${n === 1 ? "disabled" : ""}>← Previous</button><span>Page ${n} of ${totalPages}</span><button class="button small" data-action="page" data-page="${n + 1}" ${n === totalPages ? "disabled" : ""}>Next →</button></div>` : ""}</section><div class="banner"><div><h3>One idea. The right team.</h3><p>Tell us what you’re working on. We’ll help you put the pieces together.</p></div><a class="button primary" href="#/team">Build my team ↗</a></div>`;
}
function member(a) {
  return `<div class="team-member"><span class="agent-avatar" style="--tint:${tint(a)}">${e(a.emoji)}</span><div><h3><button class="title-button" data-action="profile" data-id="${e(a.id)}">${e(a.name)}</button></h3><p>${e(divName(a.division))}</p></div><button class="icon-button" data-action="add" data-id="${e(a.id)}" aria-label="Remove ${e(a.name)} from team">×</button></div>`;
}
function toolSelect() {
  return `<label class="field">Your AI tool<select id="tool">${Object.entries(
    catalog.tools,
  )
    .map(
      ([id, t]) =>
        `<option value="${id}" ${state.tool === id ? "selected" : ""}>${e(t.label)}</option>`,
    )
    .join("")}</select></label>`;
}
function team() {
  let team = getTeam();
  main.innerHTML =
    head(
      "A SMALL TEAM. A BIG START.",
      "Your next idea, assembled.",
      "Describe your goal, get a suggested starting team, and give every specialist a useful brief.",
    ) +
    `<div class="two-col"><form id="brief-form" class="panel form-grid"><h2>What are we working on?</h2><label class="field">Project name<input name="name" value="${e(state.draft.name)}" placeholder="The next big thing" maxlength="150"></label><label class="field">What do you want to achieve? *<textarea name="goal" required placeholder="I want to launch an ecommerce website for my clothing brand…">${e(state.draft.goal)}</textarea><small>Suggestions use catalog keywords and curated role mappings. You can change every selection.</small></label><label class="field">Current setup / technology<input name="stack" value="${e(state.draft.stack)}" placeholder="e.g. Shopify, existing brand assets, small internal team"></label><label class="field">Constraints<textarea name="constraints" placeholder="Budget, timeline, scope, things to preserve…">${e(state.draft.constraints)}</textarea></label><label class="field">Expected deliverables<textarea name="deliverables" placeholder="A page design, implementation plan, launch checklist…">${e(state.draft.deliverables)}</textarea></label><button type="submit" class="button primary">Suggest a starting team ↗</button></form><div class="stack"><section class="panel"><div class="row spread"><h2>Your team <span class="muted">(${team.length})</span></h2><a class="text-button" href="#/discover">Find more +</a></div><div class="stack spacer">${team.map(member).join("") || '<p class="muted">Your team starts here. Describe your goal or add specialists from Discover.</p>'}</div>${team.length ? `<p class="note spacer">${e(state.draft.goal ? "Suggested for: " + state.draft.goal.slice(0, 160) : "A team you assembled from the catalog.")} Review the roles against your project before starting.</p><div class="actions"><button class="button" data-action="save-team">Save team</button><button class="button" data-action="export-team">Export team</button><button class="button" data-action="team-install">Installation guide ↗</button></div>` : ""}</section><section class="panel"><h2>A brief worth starting with.</h2><p class="muted">Generate a structured brief from your inputs and selected roles. Edit it before handing it to your assistant.</p><div class="actions"><button class="button primary" data-action="generate-brief" ${!team.length ? "disabled" : ""}>Generate brief ↗</button><button class="button" data-action="create-project" ${!team.length ? "disabled" : ""}>Create project board</button></div></section><p class="storage-status">${storageAvailable ? "◉ Saved in this browser. Export to move between devices." : "Storage unavailable. Export your work before closing."}</p></div></div>`;
}
const sourceCache = new Map();
let profileRequest = 0;
async function getSource(a) {
  if (!sourceCache.has(a.id)) {
    const r = await fetch("/agents/" + encodeURIComponent(a.id) + ".md");
    if (!r.ok) throw Error("Source unavailable");
    sourceCache.set(a.id, await r.text());
  }
  return sourceCache.get(a.id);
}
async function profile(id) {
  const a = byId.get(id);
  if (!a) return;
  const request = ++profileRequest;
  let content;
  try {
    content = await getSource(a);
  } catch {
    toast("Source could not load. Try again.");
    return;
  }
  if (request !== profileRequest) return;
  state.recent = [id, ...state.recent.filter((x) => x !== id)].slice(0, 12);
  persist();
  const related = searchAgents(agents, {
    division: a.division,
    q: a.tags.slice(0, 2).join(" "),
  })
    .filter((x) => x.id !== id)
    .slice(0, 3);
  dialog.innerHTML = `<div class="dialog-head"><div><div class="division-label">${e(divName(a.division))} · ${e(a.emoji)}</div><h2 id="detail-title">${e(a.name)}</h2></div><button class="icon-button" data-action="close" aria-label="Close profile">×</button></div><div class="dialog-body"><p>${e(a.description)}</p><div class="tags">${a.tags.map((t) => `<span class="tag">${e(t)}</span>`).join("")}</div><div class="actions"><button class="button primary" data-action="profile-add" data-id="${e(id)}">${state.team.includes(id) ? "Remove from team" : "Add to team +"}</button><button class="button" data-action="share-profile" data-id="${e(id)}">Share profile</button><button class="button" data-action="copy-prompt" data-id="${e(id)}">Copy source prompt</button><button class="button" data-action="install" data-id="${e(id)}">Install guide ↗</button><a class="button" href="${catalog.repository}/blob/${catalog.revision}/${encodeURI(a.source)}" target="_blank" rel="noopener noreferrer">Source ↗</a></div><h3>When to use this specialist</h3>${a.missions.length ? `<ul>${a.missions.map((x) => `<li>${e(x)}</li>`).join("")}</ul>` : `<p>${e(a.vibe || a.description)}</p>`}<h3>Bring to the task</h3><p>Your goal, relevant files or evidence, current setup, constraints, and a definition of success. Confirm any tools the role needs are available in your host.</p><h3>Expected work</h3>${a.deliverables.length ? `<ul>${a.deliverables.map((x) => `<li>${e(x)}</li>`).join("")}</ul>` : "<p>The source does not provide a separate deliverables list. Agree on the output format in your brief.</p>"}<h3>Capability notes</h3><p class="note">This is a role instruction file. The model, tools, permissions, and memory come from the environment you use it in. Quality has not been independently evaluated here.</p>${a.warnings.map((w) => `<p class="note warning">${e(w)}</p>`).join("")}<h3>A first task to try</h3><div class="example-output">“Act as ${e(a.name)}. Review my project brief, identify missing information, and propose a first deliverable with acceptance criteria. Use only the evidence and tools available.”</div><h3>Related specialists</h3><div class="actions">${related.map((r) => `<button class="button small" data-action="profile" data-id="${e(r.id)}">${e(r.name)} ↗</button>`).join("")}</div><details><summary>Inspect the complete source instructions</summary><pre class="source-preview">${e(content)}</pre></details><p class="muted">Imported ${new Date(catalog.importedAt).toLocaleDateString()} · SHA-256 ${e(a.sourceHash.slice(0, 12))}… · <a class="link" href="/UPSTREAM-LICENSE.txt" target="_blank">MIT license</a></p></div>`;
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
}
function showDialog(title, body) {
  dialog.innerHTML = `<div class="dialog-head"><h2 id="detail-title">${title}</h2><button class="icon-button" data-action="close" aria-label="Close dialog">×</button></div><div class="dialog-body">${body}</div>`;
  if (!dialog.open) dialog.showModal();
  dialog.scrollTop = 0;
}
let installIds = [];
function install(ids) {
  installIds = ids.filter((i) => byId.has(i));
  if (!installIds.length) return toast("Add an agent first");
  showDialog(
    "Take your team with you.",
    `<p>Install ${installIds.length} selected specialist${installIds.length > 1 ? "s" : ""} using the upstream repository’s scripts.</p>${toolSelect()}<h3>1. Get the upstream repository</h3><pre class="install-code">git clone https://github.com/msitarzewski/agency-agents.git
cd agency-agents</pre><h3>2. Convert and install your selection</h3><pre id="install-code" class="install-code">${e(installCommand(state.tool, installIds))}</pre><div class="actions"><button class="button primary" data-action="copy-install">Copy commands</button><button class="button" data-action="download-roster">Download agent IDs</button></div><p class="note">These commands run on your computer. This website does not install files or launch agents. Review the upstream scripts and your tool’s setup instructions.</p><p id="tool-scope" class="muted">${scopeText()}</p>`,
  );
}
function scopeText() {
  const t = catalog.tools[state.tool];
  return t
    ? `${t.label}: ${t.scope.user ? "user scope supported" : "no user scope"} · ${t.scope.project ? "project scope supported" : "no project scope"}. Compatibility metadata is from upstream; it is not a live installation check.`
    : "";
}
function compare() {
  let list = state.compare.map((i) => byId.get(i)).filter(Boolean);
  main.innerHTML =
    head(
      "MAKE A CLEAR CHOICE",
      "Same goal. Different strengths.",
      "Compare up to three specialists. Look at what each role emphasizes and what your task actually needs.",
    ) +
    (list.length
      ? `<div class="table-wrap"><table class="compare-table"><thead><tr><th>Role</th>${list.map((a) => `<th>${e(a.emoji)} ${e(a.name)}<div class="actions"><button class="button small" data-action="compare" data-id="${e(a.id)}">Remove</button><button class="button small" data-action="profile" data-id="${e(a.id)}">Profile ↗</button></div></th>`).join("")}</tr></thead><tbody>${[
          ["Focus", (a) => e(a.description)],
          ["Division", (a) => e(divName(a.division))],
          [
            "Core work",
            (a) => a.missions.map(e).join("<br>") || "See source instructions",
          ],
          [
            "Deliverables",
            (a) => a.deliverables.map(e).join("<br>") || "Agree in your brief",
          ],
          ["Skills", (a) => a.tags.map(e).join(", ")],
          [
            "Inputs needed",
            () => "Brief, relevant evidence, constraints, acceptance criteria",
          ],
          ["Evaluation", () => "Not independently evaluated"],
          [
            "Add to your team",
            (a) =>
              `<button class="button primary small" data-action="add" data-id="${e(a.id)}">${state.team.includes(a.id) ? "✓ In team" : "+ Add to team"}</button>`,
          ],
        ]
          .map(
            ([label, fn]) =>
              `<tr><td>${label}</td>${list.map((a) => `<td>${fn(a)}</td>`).join("")}</tr>`,
          )
          .join(
            "",
          )}</tbody></table></div><div class="actions"><a class="button" href="#/discover">Find another specialist +</a><a class="button primary" href="#/team">Open team builder ↗</a></div>`
      : empty(
          "A little comparison helps.",
          "Select Compare on two or three agent cards to inspect their strengths side by side.",
          "#/discover",
        ));
}
function workflows() {
  main.innerHTML =
    head(
      "FROM IDEA TO A PLAN",
      "There’s a path for that.",
      "Start with an upstream runbook. Inspect the team, understand the stages, then create your own editable project board.",
    ) +
    `<div class="workflow-grid">${catalog.runbooks.map((r, i) => `<article class="panel workflow-card"><div class="workflow-number">PLAYBOOK / 0${i + 1}</div><h2>${e(r.title)}</h2><p>${e(r.summary)}</p><div class="workflow-meta"><span>◷ ${e(r.duration)}</span><span>♧ ${new Set(r.roster.flatMap((g) => g.agents)).size} roles</span></div><div class="pills">${r.roster.map((g) => `<span>${e(g.group)}</span>`).join("")}</div><div class="actions"><button class="button primary" data-action="runbook" data-id="${e(r.slug)}">Explore workflow ↗</button><a class="button" href="${catalog.repository}/blob/${catalog.revision}/${r.doc}" target="_blank" rel="noopener noreferrer">Read source ↗</a></div></article>`).join("")}</div><div class="banner"><div><h3>A plan you can make your own.</h3><p>Suggested durations come from upstream runbooks. Your scope, tools, and review needs determine the actual effort.</p></div><a class="button" href="#/team">Create a custom team ↗</a></div>`;
}
function runbook(id) {
  const r = catalog.runbooks.find((r) => r.slug === id);
  if (!r) return;
  showDialog(
    e(r.title),
    `<p>${e(r.summary)}</p><form id="runbook-form" data-id="${e(r.slug)}"><label class="field">Project name<input name="name" required value="${e(r.title)}" maxlength="150"></label><h3>Select the groups you need</h3>${r.roster.map((g, i) => `<section class="spacer"><label class="checkbox"><input name="group" type="checkbox" value="${i}" ${i === 0 ? "checked" : ""}>${e(g.group)} · ${e(g.activation)}</label><p>${g.agents.map((i) => e(byId.get(i)?.name || i)).join(" · ")}</p></section>`).join("")}<button class="button primary spacer" type="submit">Create team & project board ↗</button></form><details><summary>Read the full upstream runbook</summary><pre class="source-preview">${e(r.content)}</pre></details>`,
  );
}
function workspace() {
  let favorites = state.favorites.map((i) => byId.get(i)).filter(Boolean);
  main.innerHTML =
    head(
      "YOUR LITTLE CORNER OF POSSIBILITY",
      "Pick up where you left off.",
      "Saved specialists, teams, briefs, and project boards. Your workspace stays in this browser; export a backup whenever you need one.",
    ) +
    `<div class="row spread"><span class="storage-status">${storageAvailable ? "◉ Browser storage active" : "Storage unavailable — export your work"}</span><div class="actions" style="margin:0"><button class="button" data-action="export-workspace">Export workspace</button><label class="button" style="cursor:pointer">Import workspace<input id="import-workspace" type="file" accept="application/json,.json" hidden></label></div></div><div class="metrics-grid"><div class="metric"><strong>${favorites.length}</strong><span>Saved specialists</span></div><div class="metric"><strong>${state.savedTeams.length}</strong><span>Saved teams</span></div><div class="metric"><strong>${state.projects.length}</strong><span>Projects in motion</span></div></div><h2 class="subheading">Your projects</h2><div class="workflow-grid">${state.projects.map((p) => `<article class="panel"><div class="workflow-number">${p.tasks.filter((t) => t.status === "done").length} / ${p.tasks.length} TASKS COMPLETE</div><h3>${e(p.name)}</h3><p class="muted">${e(p.goal || "A team and a plan, ready for your next step.")}</p><div class="actions"><button class="button primary small" data-action="open-project" data-id="${e(p.id)}">Open board ↗</button><button class="button small" data-action="export-project" data-id="${e(p.id)}">Export</button><button class="button small" data-action="delete-project" data-id="${e(p.id)}">Delete</button></div></article>`).join("") || empty("Make room for your next idea.", "Create a project from a workflow or your custom team.", "#/workflows", "Explore workflows")}</div><h2 class="subheading">Saved teams</h2><div class="workflow-grid">${state.savedTeams.map((t) => `<article class="panel"><h3>${e(t.name)}</h3><p class="muted">${t.agents.length} specialists · ${t.agents.map((id) => e(byId.get(id)?.name || id)).join(", ")}</p><div class="actions"><button class="button small" data-action="load-team" data-id="${e(t.id)}">Open in builder ↗</button><button class="button small" data-action="delete-team" data-id="${e(t.id)}">Delete</button></div></article>`).join("") || '<p class="muted">Save a team in the builder to return to it here.</p>'}</div><h2 class="subheading">Your briefs</h2><div class="workflow-grid">${state.briefs.map((b) => `<article class="panel"><h3>${e(b.name)}</h3><p class="muted">${new Date(b.created).toLocaleDateString()}</p><div class="actions"><button class="button small" data-action="open-brief" data-id="${e(b.id)}">Read brief ↗</button><button class="button small" data-action="download-brief" data-id="${e(b.id)}">Download .md</button><button class="button small" data-action="delete-brief" data-id="${e(b.id)}">Delete</button></div></article>`).join("") || '<p class="muted">Generated briefs appear here after you save them.</p>'}</div><h2 class="subheading">Saved specialists</h2><div class="agent-grid">${favorites.map(card).join("") || empty("Good people are worth keeping.", "Use the star on any specialist to save it here.", "#/discover")}</div>${
      state.recent.length
        ? `<h2 class="subheading">Recently explored</h2><div class="actions">${state.recent
            .slice(0, 6)
            .map((id) => byId.get(id))
            .filter(Boolean)
            .map(
              (a) =>
                `<button class="button small" data-action="profile" data-id="${e(a.id)}">${e(a.name)} ↗</button>`,
            )
            .join("")}</div>`
        : ""
    }`;
}
function projectView(id) {
  const p = state.projects.find((p) => p.id === id);
  if (!p) {
    go("workspace");
    return;
  }
  main.innerHTML =
    head(
      "ONE STEP AT A TIME",
      e(p.name),
      e(p.goal || "Keep assignments, handoffs, and review evidence together."),
    ) +
    `<div class="actions"><a class="button" href="#/workspace">← Workspace</a><button class="button" data-action="export-project" data-id="${e(p.id)}">Export project</button><button class="button" data-action="project-install" data-id="${e(p.id)}">Team install guide ↗</button></div><p class="note spacer">This board tracks work you do in your own assistant or tools. Changing a status records your progress; it does not execute an agent.</p><div class="board spacer">${[
      ["todo", "To do"],
      ["doing", "In progress"],
      ["done", "Done"],
    ]
      .map(
        ([status, label]) =>
          `<section class="board-col"><h3>${label} · ${p.tasks.filter((t) => t.status === status).length}</h3>${p.tasks
            .filter((t) => t.status === status)
            .map(
              (t) =>
                `<article class="task"><strong>${e(t.title)}</strong><p class="muted">${e(t.owner || "Your team")}</p><select aria-label="Status for ${e(t.title)}" class="task-status" data-project="${e(p.id)}" data-task="${e(t.id)}">${[
                  ["todo", "To do"],
                  ["doing", "In progress"],
                  ["done", "Done"],
                ]
                  .map(
                    ([v, l]) =>
                      `<option value="${v}" ${status === v ? "selected" : ""}>${l}</option>`,
                  )
                  .join("")}</select></article>`,
            )
            .join("")}</section>`,
      )
      .join(
        "",
      )}</div><section class="panel spacer"><h2>Outputs & handoff notes</h2><p class="muted">Record deliverable links, review results, open questions, and what the next specialist needs.</p><label class="field">Project notes<textarea id="project-notes" data-id="${e(p.id)}" rows="7" placeholder="Output links, acceptance checks, handoff context…">${e(p.notes || "")}</textarea></label><button class="button primary spacer" data-action="save-notes" data-id="${e(p.id)}">Save notes</button><form id="task-form" class="spacer form-grid" data-id="${e(p.id)}"><label class="field">Add a milestone<input name="title" required maxlength="250" placeholder="e.g. Review the mobile checkout"></label><label class="field">Owner<input name="owner" maxlength="150" placeholder="Specialist or person responsible"></label><button class="button" type="submit">Add task +</button></form></section>`;
}
const examples = [
  {
    title: "A storefront that feels like your brand",
    type: "Website",
    case: "website",
    goal: "Build an ecommerce website for a clothing brand using Shopify. Focus on accessible product pages and a clear checkout journey.",
    input:
      "We have brand assets and 12 products. We need a product page concept and an implementation checklist. Keep the existing checkout.",
    output:
      "1. Audit existing assets and product data.\n2. Define product page hierarchy, size selection, and error states.\n3. Produce a responsive implementation plan.\n4. Verify keyboard navigation and document unresolved requirements.",
  },
  {
    title: "Give your next launch a clear voice",
    type: "Marketing",
    case: "marketing",
    goal: "Create a content strategy and launch campaign for a new coffee subscription. We need landing page copy and a four-week content calendar.",
    input:
      "The audience is busy coffee enthusiasts. The goal is to explain the subscription clearly. We have no validated conversion claims.",
    output:
      "1. Draft a message hierarchy with claims tied to supplied facts.\n2. Outline landing page sections and a primary CTA.\n3. Map four weeks of content to launch milestones.\n4. Define measurement questions without inventing results.",
  },
  {
    title: "Find out why your app feels slow",
    type: "Performance",
    case: "performance",
    goal: "Improve performance of a React website with slow database queries. Establish measurements before making changes.",
    input:
      "We see slow page transitions and API responses. We can supply traces, query plans, and browser performance recordings.",
    output:
      "1. Establish baseline timings and a reproducible scenario.\n2. Separate browser, network, and database bottlenecks.\n3. Prioritize changes by evidence and expected impact.\n4. Repeat the same measurements and record trade-offs.",
  },
];
function exampleView() {
  main.innerHTML =
    head(
      "SEE A POSSIBLE START",
      "From a blank page to a direction.",
      "Illustrative briefs and output outlines, written for this explorer. These are examples of structure, not measured agent results.",
    ) +
    `<div class="stack">${examples
      .map(
        (x, i) =>
          `<article class="panel"><div class="division-label">${x.type} / EXAMPLE 0${i + 1}</div><h2>${x.title}</h2><div class="two-col spacer"><div><h3>The brief</h3><p class="muted">${x.input}</p><div class="pills">${recommend(
            agents,
            x.goal,
            3,
          )
            .map((a) => `<span>${e(a.name)}</span>`)
            .join(
              "",
            )}</div></div><div><h3>A possible output outline</h3><p class="example-output" style="white-space:pre-line">${x.output}</p></div></div><div class="actions"><button class="button primary" data-action="use-example" data-id="${i}">Use this starting point ↗</button><a class="button" href="#/discover?case=${x.case}">Find specialists</a></div></article>`,
      )
      .join("")}</div>`;
}
function quality() {
  const warnings = agents.filter((a) => a.warnings.length);
  main.innerHTML =
    head(
      "KNOW WHAT YOU’RE WORKING WITH",
      "Good decisions start with evidence.",
      "Inspect the catalog’s provenance and structural checks. Keep your own review notes without confusing them with independent benchmarks.",
    ) +
    `<div class="metrics-grid"><div class="metric"><strong>${agents.length}</strong><span>Imported source profiles</span></div><div class="metric"><strong>${catalog.runbooks.length}</strong><span>Runbooks with resolved rosters</span></div><div class="metric"><strong>0</strong><span>Independent evaluations here</span></div></div><div class="two-col"><section class="panel"><h2>Catalog provenance</h2><p class="muted">Snapshot imported ${new Date(catalog.importedAt).toLocaleString()}. Search runs on this bundled snapshot; it is not continuously synchronized.</p><ul class="check-list"><li>Unique source file identifiers checked at import.</li><li>Every runbook agent reference resolved at import.</li><li>Each source profile has a SHA-256 content hash.</li><li>Tags and summaries are derived from source text.</li></ul><p class="note">These are catalog integrity checks. They do not establish output quality, security, or installation compatibility.</p><div class="actions"><a class="button" href="${catalog.repository}" target="_blank" rel="noopener noreferrer">Upstream repository ↗</a><a class="button" href="/UPSTREAM-LICENSE.txt" target="_blank">License</a></div><h3 class="spacer">Capability notes to review</h3><p class="muted">${warnings.length} profiles have a detected memory phrase or potentially unbundled script reference. Detection is a text heuristic; inspect the source for context.</p><div class="stack">${warnings
      .slice(0, 8)
      .map(
        (a) =>
          `<button class="button" data-action="profile" data-id="${e(a.id)}">${e(a.name)} ↗</button>`,
      )
      .join(
        "",
      )}</div></section><section class="panel"><h2>Your review notebook</h2><p class="muted">Record the model, task, evidence, and limitations of your own trial. Notes stay local and do not create a public quality score.</p><form id="review-form" class="form-grid"><label class="field">Specialist<select name="agent">${agents.map((a) => `<option value="${e(a.id)}">${e(a.name)}</option>`).join("")}</select></label><label class="field">Model and environment<input name="environment" required placeholder="Model version, tool, configuration" maxlength="500"></label><label class="field">Task, observations, and evidence<textarea name="notes" required placeholder="What did you test? What worked? Link the outputs and record any gaps." maxlength="10000"></textarea></label><button class="button primary" type="submit">Save review note</button></form><div class="stack spacer">${state.reviews.map((r, i) => `<article class="note"><strong>${e(byId.get(r.agent)?.name || r.agent)}</strong><br>${e(r.environment || "")}<p>${e(r.notes)}</p><button class="text-button" data-action="delete-review" data-id="${i}">Delete note</button></article>`).join("")}</div></section></div>`;
}
function guide() {
  main.innerHTML =
    head(
      "A LITTLE GUIDANCE GOES A LONG WAY",
      "Your first useful task starts here.",
      "Choose a specialist, give it context, and review the result. You can use the explorer without an account or an API key.",
    ) +
    `<div class="two-col"><section class="panel guide-steps">${[
      [
        "Find a role for your goal",
        "Search by a task or choose a use case. Open a profile to understand its focus, source instructions, and capability notes.",
      ],
      [
        "Assemble a small team",
        "Compare overlapping specialists, then add only the roles your project needs. The builder can suggest a starting point.",
      ],
      [
        "Give the team a concrete brief",
        "State your goal, setup, constraints, deliverables, and acceptance criteria. Generate and edit a brief in the builder.",
      ],
      [
        "Use your own assistant or development tool",
        "Copy an agent’s instructions into your assistant or follow the upstream installation guide. Your host provides the model and tools.",
      ],
      [
        "Review, record, and hand off",
        "Check outputs against your brief. Keep links and open questions on a project board. Record your own evaluation evidence in Quality & sources.",
      ],
    ]
      .map(
        ([t, d]) =>
          `<article class="guide-step"><div><h3>${t}</h3><p>${d}</p></div></article>`,
      )
      .join(
        "",
      )}</section><div class="stack"><section class="panel"><h2>Start with a real goal.</h2><p class="muted">“Review our product page for accessibility” is easier to act on than “make our website better.”</p><a class="button primary" href="#/team">Write your first brief ↗</a></section><section class="panel"><h2>Your work, in your browser.</h2><p class="muted">Favorites, teams, project notes, briefs, and reviews use local browser storage. They are not synchronized between devices. Clearing browser data removes them. Export and import a workspace backup to move your work.</p><a class="button" href="#/workspace">Open workspace ↗</a></section><section class="panel"><h2>What’s connected?</h2><p class="muted">This version provides catalog discovery, planning, and portable exports. It has no model execution service or independent evaluation backend. Source links open GitHub; installation commands run in your terminal.</p><a class="link" href="${catalog.repository}" target="_blank" rel="noopener noreferrer">Read upstream documentation ↗</a></section></div></div>`;
}
function route() {
  const raw = location.hash.slice(2) || "discover";
  const [path, q = ""] = raw.split("?");
  page = path.split("/")[0];
  params = new URLSearchParams(q);
  if (dialog.open) dialog.close();
  $("#breadcrumb").textContent =
    {
      discover: "The talent directory",
      team: "Your team, your way",
      workspace: "Your personal workspace",
      workflows: "A path from idea to done",
      examples: "A little inspiration",
      quality: "Evidence & provenance",
      guide: "A useful first step",
      compare: "Compare specialists",
      project: "Your project board",
    }[page] || "Agency Explorer";
  nav();
  (
    ({
      discover,
      team,
      workspace,
      workflows,
      examples: exampleView,
      quality,
      guide,
      compare,
      project: () => projectView(decodeURIComponent(path.split("/")[1] || "")),
    })[page] || discover
  )();
  if (params.get("agent")) profile(params.get("agent"));
  $("#menu").setAttribute("aria-expanded", "false");
  $(".sidebar").classList.remove("open");
}
function addProject(name, goal, ids, groups) {
  const id = uid();
  let tasks = groups
    ? groups.map((g) => ({
        id: uid(),
        title: g.group,
        owner: g.agents.map((i) => byId.get(i)?.name || i).join(", "),
        status: "todo",
      }))
    : [
        {
          id: uid(),
          title: "Confirm brief and acceptance criteria",
          owner: "Project owner",
          status: "todo",
        },
        ...ids.map((i) => ({
          id: uid(),
          title: `Prepare ${byId.get(i)?.name || i} deliverable`,
          owner: byId.get(i)?.name || i,
          status: "todo",
        })),
        {
          id: uid(),
          title: "Review outputs and record remaining gaps",
          owner: "Project owner",
          status: "todo",
        },
      ];
  state.projects.unshift({
    id,
    name,
    goal,
    agents: ids,
    tasks,
    notes: "",
    created: new Date().toISOString(),
  });
  persist();
  go("project/" + id);
}
function saveForm() {
  const f = $("#brief-form");
  if (f) for (const [k, v] of new FormData(f)) state.draft[k] = v;
  persist();
}
let generatedBrief = "";
function briefDialog(content, name = "Project brief", canSave = false) {
  generatedBrief = content;
  showDialog(
    e(name),
    `${canSave ? "<p>This draft is assembled from your inputs and selected roles. Edit it before saving or sharing.</p>" : ""}<label class="field">Brief text<textarea id="brief-editor" rows="17">${e(content)}</textarea></label><div class="actions"><button class="button primary" data-action="copy-brief">Copy brief</button><button class="button" data-action="download-current-brief">Download .md</button>${canSave ? '<button class="button" data-action="save-brief">Save to workspace</button>' : ""}</div>`,
  );
}
document.addEventListener("click", async (event) => {
  const b = event.target.closest("[data-action]");
  if (!b) return;
  const a = b.dataset.action,
    id = b.dataset.id;
  switch (a) {
    case "profile":
      profile(id);
      break;
    case "close":
      dialog.close();
      break;
    case "favorite":
      state.favorites = state.favorites.includes(id)
        ? state.favorites.filter((i) => i !== id)
        : [...state.favorites, id];
      persist();
      route();
      break;
    case "add":
    case "profile-add": {
      if (!byId.has(id)) break;
      const has = state.team.includes(id);
      state.team = has
        ? state.team.filter((i) => i !== id)
        : [...state.team, id];
      persist();
      toast(has ? "Removed from your team" : "Added to your team");
      if (a === "profile-add") profile(id);
      else if (!dialog.open) route();
      break;
    }
    case "compare":
      if (state.compare.includes(id))
        state.compare = state.compare.filter((i) => i !== id);
      else if (state.compare.length < 3) state.compare.push(id);
      else {
        toast("Compare up to three agents. Remove one to add another.");
        break;
      }
      persist();
      route();
      break;
    case "clear-compare":
      state.compare = [];
      persist();
      route();
      break;
    case "tag":
      go("discover", { tag: b.dataset.tag });
      break;
    case "clear-tag":
      setFilter("tag", "");
      break;
    case "division":
      setFilter("division", id);
      break;
    case "use-case":
      setFilter("case", params.get("case") === id ? "" : id);
      break;
    case "reset-filters":
      go("discover");
      break;
    case "page": {
      let obj = currentParams();
      obj.p = b.dataset.page;
      go("discover", obj);
      setTimeout(() => $("#directory")?.scrollIntoView({ block: "start" }), 0);
      break;
    }
    case "share-search":
      await copy(location.href);
      break;
    case "share-profile":
      await copy(
        location.origin + "/#/discover?agent=" + encodeURIComponent(id),
      );
      break;
    case "copy-prompt":
      try {
        await copy(await getSource(byId.get(id)));
      } catch {
        toast("Could not load source instructions. Try again.");
      }
      break;
    case "install":
      install([id]);
      break;
    case "team-install":
      saveForm();
      install(state.team);
      break;
    case "copy-install":
      await copy(
        "git clone https://github.com/msitarzewski/agency-agents.git\ncd agency-agents\n" +
          installCommand(state.tool, installIds),
      );
      break;
    case "download-roster":
      download("team.txt", installIds.join("\n") + "\n");
      break;
    case "save-team":
      saveForm();
      state.savedTeams.unshift({
        id: uid(),
        name: state.draft.name || "My specialist team",
        agents: [...state.team],
        draft: { ...state.draft },
        created: new Date().toISOString(),
      });
      persist();
      toast("Team saved to your workspace");
      break;
    case "export-team":
      saveForm();
      download(
        "agency-team.json",
        JSON.stringify(
          {
            name: state.draft.name || "My team",
            agents: state.team.map((id) => ({
              id,
              name: byId.get(id)?.name,
              source: byId.get(id)?.source,
            })),
            brief: state.draft,
          },
          null,
          2,
        ),
        "application/json",
      );
      break;
    case "generate-brief":
      saveForm();
      if (!state.draft.goal.trim()) {
        toast("Add your project goal first");
        $("#brief-form [name=goal]").focus();
        break;
      }
      briefDialog(
        makeBrief({ ...state.draft, team: getTeam() }),
        state.draft.name || "Your project brief",
        true,
      );
      break;
    case "copy-brief":
      await copy($("#brief-editor").value);
      break;
    case "download-current-brief":
      download("project-brief.md", $("#brief-editor").value);
      break;
    case "save-brief":
      state.briefs.unshift({
        id: uid(),
        name: state.draft.name || "Project brief",
        content: $("#brief-editor").value,
        created: new Date().toISOString(),
      });
      persist();
      dialog.close();
      toast("Brief saved to your workspace");
      break;
    case "create-project":
      saveForm();
      if (!state.draft.goal.trim()) {
        toast("Add your project goal first");
        break;
      }
      addProject(state.draft.name || "My new project", state.draft.goal, [
        ...state.team,
      ]);
      break;
    case "runbook":
      runbook(id);
      break;
    case "open-project":
      go("project/" + id);
      break;
    case "export-project":
      download(
        "agency-project.json",
        JSON.stringify(
          state.projects.find((p) => p.id === id),
          null,
          2,
        ),
        "application/json",
      );
      break;
    case "delete-project":
      showDialog(
        "Delete this project?",
        `<p>This removes its board and notes from this browser. Export a backup first if you need it.</p><button class="button primary" data-action="confirm-delete-project" data-id="${e(id)}">Delete project</button>`,
      );
      break;
    case "confirm-delete-project":
      state.projects = state.projects.filter((p) => p.id !== id);
      persist();
      dialog.close();
      route();
      toast("Project deleted");
      break;
    case "save-notes": {
      const p = state.projects.find((p) => p.id === id);
      p.notes = $("#project-notes").value;
      persist();
      toast("Handoff notes saved");
      break;
    }
    case "project-install":
      install(state.projects.find((p) => p.id === id).agents || []);
      break;
    case "load-team": {
      let t = state.savedTeams.find((t) => t.id === id);
      state.team = t.agents.filter((i) => byId.has(i));
      if (t.draft) state.draft = normalize({ draft: t.draft }).draft;
      persist();
      go("team");
      break;
    }
    case "delete-team":
      state.savedTeams = state.savedTeams.filter((t) => t.id !== id);
      persist();
      workspace();
      break;
    case "open-brief": {
      let b = state.briefs.find((b) => b.id === id);
      briefDialog(b.content, b.name);
      break;
    }
    case "download-brief":
      download(
        "project-brief.md",
        state.briefs.find((b) => b.id === id).content,
      );
      break;
    case "delete-brief":
      state.briefs = state.briefs.filter((b) => b.id !== id);
      persist();
      workspace();
      break;
    case "export-workspace":
      download(
        "agency-workspace.json",
        JSON.stringify(
          {
            format: "agency-explorer-v1",
            exportedAt: new Date().toISOString(),
            ...state,
          },
          null,
          2,
        ),
        "application/json",
      );
      break;
    case "use-example": {
      const x = examples[Number(id)];
      state.draft = { ...blank.draft, name: x.title, goal: x.goal };
      state.team = recommend(agents, x.goal).map((a) => a.id);
      persist();
      go("team");
      break;
    }
    case "delete-review":
      state.reviews.splice(Number(id), 1);
      persist();
      quality();
      break;
  }
});
document.addEventListener("submit", (event) => {
  event.preventDefault();
  let f = event.target;
  if (f.id === "search-form") {
    setFilter("q", new FormData(f).get("q").trim());
  } else if (f.id === "brief-form") {
    saveForm();
    state.team = recommend(
      agents,
      state.draft.goal + " " + state.draft.stack,
    ).map((a) => a.id);
    persist();
    team();
    toast("Starting team suggested. Review and adjust the roles.");
  } else if (f.id === "runbook-form") {
    const r = catalog.runbooks.find((r) => r.slug === f.dataset.id);
    const d = new FormData(f),
      groups = d.getAll("group").map((i) => r.roster[Number(i)]);
    if (!groups.length) return toast("Select at least one group");
    const ids = [...new Set(groups.flatMap((g) => g.agents))].filter((i) =>
      byId.has(i),
    );
    state.team = ids;
    state.draft = {
      ...blank.draft,
      name: String(d.get("name")),
      goal: r.summary,
    };
    dialog.close();
    addProject(String(d.get("name")), r.summary, ids, groups);
  } else if (f.id === "task-form") {
    const p = state.projects.find((p) => p.id === f.dataset.id),
      d = new FormData(f);
    p.tasks.push({
      id: uid(),
      title: String(d.get("title")),
      owner: String(d.get("owner")),
      status: "todo",
    });
    persist();
    projectView(p.id);
  } else if (f.id === "review-form") {
    const d = new FormData(f);
    state.reviews.unshift({
      agent: String(d.get("agent")),
      environment: String(d.get("environment")),
      notes: String(d.get("notes")),
      created: new Date().toISOString(),
    });
    persist();
    quality();
    toast("Review note saved");
  }
});
document.addEventListener("change", async (event) => {
  const el = event.target;
  if (el.id === "division") setFilter("division", el.value);
  if (el.id === "skill") setFilter("tag", el.value);
  if (el.id === "sort") setFilter("sort", el.value);
  if (el.closest("#brief-form")) saveForm();
  if (el.id === "tool") {
    state.tool = el.value;
    persist();
    if ($("#install-code"))
      $("#install-code").textContent = installCommand(state.tool, installIds);
    if ($("#tool-scope")) $("#tool-scope").textContent = scopeText();
  }
  if (el.classList.contains("task-status")) {
    const p = state.projects.find((p) => p.id === el.dataset.project),
      t = p.tasks.find((t) => t.id === el.dataset.task);
    t.status = el.value;
    persist();
    projectView(p.id);
  }
  if (el.id === "import-workspace") {
    const file = el.files[0];
    if (!file) return;
    if (file.size > 5_000_000)
      return toast("Choose a workspace backup smaller than 5 MB");
    try {
      const data = JSON.parse(await file.text());
      if (data.format !== "agency-explorer-v1")
        throw Error("Not a workspace backup");
      const next = normalize(data);
      for (const k of ["team", "favorites", "compare", "recent"])
        next[k] = next[k].filter((i) => byId.has(i));
      storePendingImport(next);
      showDialog(
        "Import this workspace?",
        `<p>This replaces your current browser workspace with ${next.favorites.length} favorites, ${next.savedTeams.length} teams, and ${next.projects.length} projects. Export your current workspace first if you need a backup.</p><div class="actions"><button class="button" data-action="export-workspace">Export current workspace</button><button id="confirm-import" class="button primary">Replace with imported workspace</button></div>`,
      );
    } catch {
      toast(
        "Could not read that workspace backup. Your current work is unchanged.",
      );
    }
  }
});
let pendingImport;
function storePendingImport(s) {
  pendingImport = s;
}
document.addEventListener("click", (ev) => {
  if (ev.target.id === "confirm-import" && pendingImport) {
    state = pendingImport;
    pendingImport = null;
    persist();
    dialog.close();
    workspace();
    toast("Workspace imported");
  }
});
$(".skip").addEventListener("click", (ev) => {
  ev.preventDefault();
  main.focus();
});
$("#menu").addEventListener("click", () => {
  const open = $(".sidebar").classList.toggle("open");
  $("#menu").setAttribute("aria-expanded", String(open));
});
document.addEventListener("keydown", (ev) => {
  if (
    ev.key === "/" &&
    !/INPUT|TEXTAREA|SELECT/.test(ev.target.tagName) &&
    !dialog.open
  ) {
    ev.preventDefault();
    if (page !== "discover") {
      go("discover");
      setTimeout(() => $("#search")?.focus(), 0);
    } else $("#search")?.focus();
  }
});
window.addEventListener("hashchange", () => {
  route();
  window.scrollTo(0, 0);
});
dialog.addEventListener("click", (ev) => {
  if (ev.target === dialog) {
    const r = dialog.getBoundingClientRect();
    if (
      ev.clientX < r.left ||
      ev.clientX > r.right ||
      ev.clientY < r.top ||
      ev.clientY > r.bottom
    )
      dialog.close();
  }
});
try {
  const r = await fetch("/catalog.json");
  if (!r.ok) throw Error("Catalog unavailable");
  catalog = await r.json();
  agents = catalog.agents;
  byId = new Map(agents.map((a) => [a.id, a]));
  for (const k of ["team", "favorites", "compare", "recent"])
    state[k] = state[k].filter((id) => byId.has(id));
  if (!catalog.tools[state.tool]) state.tool = "claude-code";
  route();
} catch (err) {
  main.innerHTML = empty(
    "The catalog could not load.",
    "Check your connection and reload this page. Your saved workspace is still in this browser.",
  );
  console.error(err);
}
