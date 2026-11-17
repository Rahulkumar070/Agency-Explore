export const useCases = [
  {
    id: "website",
    icon: "↗",
    name: "Build a website",
    hint: "From first sketch to launch",
    terms:
      "frontend backend ui ux web website accessibility performance wordpress ecommerce shopify",
    roles: [
      "frontend developer",
      "ui designer",
      "backend architect",
      "api tester",
    ],
  },
  {
    id: "product",
    icon: "◇",
    name: "Launch a product",
    hint: "Bring your next idea to life",
    terms: "product mvp prototype startup sprint research roadmap launch",
    roles: [
      "rapid prototyper",
      "sprint prioritizer",
      "ux researcher",
      "growth hacker",
    ],
  },
  {
    id: "marketing",
    icon: "◎",
    name: "Grow your audience",
    hint: "Make something people notice",
    terms: "marketing growth content social brand campaign seo audience",
    roles: [
      "content creator",
      "growth hacker",
      "brand guardian",
      "social media strategist",
    ],
  },
  {
    id: "performance",
    icon: "ϟ",
    name: "Improve performance",
    hint: "Faster, smoother, better",
    terms: "performance optimize slow speed database benchmark reliability",
    roles: [
      "frontend developer",
      "database optimizer",
      "performance benchmarker",
      "sre",
    ],
  },
  {
    id: "security",
    icon: "⌘",
    name: "Review security",
    hint: "Build confidence into your stack",
    terms: "security audit threat vulnerability privacy identity secure",
    roles: [
      "security engineer",
      "threat modeler",
      "code reviewer",
      "privacy engineer",
    ],
  },
  {
    id: "data",
    icon: "▥",
    name: "Understand your data",
    hint: "Turn information into decisions",
    terms: "data analytics analysis visualization reporting metrics pipeline",
    roles: [
      "data engineer",
      "data visualization engineer",
      "analytics reporter",
      "data scientist",
    ],
  },
];
const stop = new Set(
  "i a an the to for my our we want need help with and or of in on is it me build make create please".split(
    " ",
  ),
);
export function tokens(s) {
  return [...new Set(s.toLowerCase().match(/[\p{L}\p{N}+#]+/gu) || [])].filter(
    (w) => !stop.has(w) && w.length > 1,
  );
}
const intents = {
  website:
    "website frontend backend ecommerce storefront shopify wordpress web",
  product: "product mvp prototype startup roadmap",
  marketing: "marketing audience content campaign seo brand social",
  performance:
    "slow speed performance optimize optimisation optimization latency bottleneck",
  security: "security secure audit threat vulnerability privacy",
  data: "data analytics analysis analyze analyse visualization metrics reporting",
};
export function caseFor(goal) {
  const ts = tokens(goal);
  const ranked = useCases
    .map((c) => ({
      c,
      s: tokens(intents[c.id]).reduce(
        (s, t) =>
          s +
          (ts.includes(t)
            ? ["slow", "security", "performance", "analytics", "data"].includes(
                t,
              )
              ? 3
              : 1
            : 0),
        0,
      ),
    }))
    .sort((a, b) => b.s - a.s);
  return ranked[0].s ? ranked[0].c : null;
}
const indexes = new WeakMap();
function index(agent) {
  if (!indexes.has(agent))
    indexes.set(agent, {
      names: new Set(tokens(agent.name + " " + agent.id)),
      desc: new Set(tokens(agent.description)),
      tags: new Set(tokens(agent.tags.join(" "))),
      body: new Set(tokens(agent.search)),
    });
  return indexes.get(agent);
}
export function scoreAgent(agent, query, caseId = "") {
  const ts = tokens(query),
    name = (agent.name + " " + agent.id).toLowerCase(),
    { names, desc, tags, body } = index(agent);
  let score = ts.reduce(
    (s, t) =>
      s +
      (names.has(t) ? 8 : 0) +
      (desc.has(t) ? 4 : 0) +
      (tags.has(t) ? 3 : 0) +
      (body.has(t) ? 0.2 : 0),
    0,
  );
  if (query && name.includes(query.toLowerCase().trim())) score += 20;
  const intent = caseFor(query);
  if (intent && intent.roles.some((n) => agent.name.toLowerCase() === n))
    score += 4;
  if (!query && !caseId) {
    const featured = [
      "Frontend Developer",
      "UI Designer",
      "Backend Architect",
      "Content Creator",
      "UX Researcher",
      "Code Reviewer",
      "Growth Hacker",
      "Data Engineer",
      "Rapid Prototyper",
      "Application Security Engineer",
      "API Tester",
      "Brand Guardian",
    ];
    const i = featured.indexOf(agent.name);
    if (i >= 0) score += 20 - i;
  }
  const c = useCases.find((c) => c.id === caseId);
  if (c)
    score += tokens(c.terms).reduce(
      (s, t) => s + (names.has(t) ? 4 : 0) + (desc.has(t) ? 1 : 0),
      0,
    );
  return score;
}
export function searchAgents(
  agents,
  {
    q = "",
    division = "",
    tag = "",
    caseId = "",
    sort = "relevance",
    favorites = null,
  } = {},
) {
  return agents
    .filter(
      (a) =>
        (!division || a.division === division) &&
        (!tag || a.tags.includes(tag)) &&
        (!favorites || favorites.includes(a.id)),
    )
    .map((a) => ({ a, score: scoreAgent(a, q, caseId) }))
    .filter((r) => (!q && !caseId) || r.score > 0)
    .sort((a, b) =>
      sort === "name"
        ? a.a.name.localeCompare(b.a.name)
        : b.score - a.score || a.a.name.localeCompare(b.a.name),
    )
    .map((r) => r.a);
}
export function recommend(agents, goal, count = 4) {
  const c = caseFor(goal),
    ranked = searchAgents(agents, { q: goal, caseId: c?.id || "" });
  const preferred = (c?.roles || [])
    .map(
      (n) =>
        agents.find((a) => a.name.toLowerCase() === n) ||
        agents.find((a) =>
          a.name
            .toLowerCase()
            .replace(/[^a-z ]/g, "")
            .includes(n),
        ),
    )
    .filter(Boolean);
  const explicit = tokens(goal).filter((t) =>
    [
      "react",
      "vue",
      "angular",
      "svelte",
      "wordpress",
      "drupal",
      "shopify",
      "python",
      "rust",
      "unity",
      "unreal",
      "tiktok",
      "instagram",
    ].includes(t),
  );
  const specialist = explicit.length
    ? ranked.find((a) => explicit.some((t) => tokens(a.name).includes(t)))
    : null;
  const results = [
    ...(specialist ? [specialist] : []),
    ...preferred,
    ...ranked,
  ];
  return [...new Map(results.map((a) => [a.id, a])).values()].slice(0, count);
}
export function makeBrief({
  name,
  goal,
  stack = "",
  constraints = "",
  deliverables = "",
  team = [],
}) {
  return `# ${name || "Project brief"}\n\n## Goal\n${goal}\n\n## Context and technology\n${stack || "Confirm the current setup before starting."}\n\n## Constraints\n${constraints || "Confirm timeline, budget, scope, and available resources."}\n\n## Deliverables\n${deliverables || "Agree on concrete deliverables before implementation."}\n\n## Selected team\n${team.map((a, i) => `${i + 1}. ${a.name} — ${a.description}`).join("\n")}\n\n## Working instructions\nUse the supplied evidence. Ask about missing requirements. State assumptions. Do not claim access to tools or prior memory that are unavailable.\n\n## Acceptance criteria\n- Deliverables address the stated goal and constraints.\n- Important decisions have a clear explanation.\n- Validation results and remaining gaps are recorded.\n- Review the work before publishing or taking external actions.\n\n## First task\nReview this brief, identify missing information, and propose the smallest useful first milestone.\n`;
}
export function installCommand(tool, ids) {
  if (!ids.length) throw new Error("Choose at least one agent.");
  if (!/^[a-z0-9-]+$/.test(tool) || ids.some((id) => !/^[a-z0-9-]+$/.test(id)))
    throw new Error("Invalid installation identifier.");
  return `./scripts/convert.sh\n./scripts/install.sh --tool ${tool} --agent ${ids.join(",")}`;
}
export function escapeHtml(s) {
  return String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
}
