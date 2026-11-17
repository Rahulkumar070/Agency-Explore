from dataclasses import dataclass


@dataclass(frozen=True)
class Agent:
    name: str
    title: str
    instructions: str
    output_format: str = "concise Markdown"


TEAM = (
    Agent("discovery", "Discovery notes",
          "Identify the business goal, audience, requested work and evidence. "
          "Separate known facts from assumptions. Ask up to five discovery questions "
          "that could change scope or price, and explain what each answer unlocks."),
    Agent("proposal", "Proposal draft",
          "Use the brief and discovery notes to draft a client-facing proposal. "
          "Define the outcome, deliverables, exclusions, acceptance criteria and a next step. "
          "Distinguish a client's spending limit from an agency quote. Mark fees, dates "
          "and revision counts as open unless the brief explicitly confirms them."),
    Agent("delivery", "Delivery handoff",
          "Use the brief, discovery notes and proposed scope to prepare an internal "
          "kickoff. For each milestone give a proposed owner role, required input, task "
          "and definition of done. Identify assets to request and decisions blocking work. "
          "Treat proposed work as pending client acceptance."),
)

SAMPLE = """Fictional client: Monsoon Roasters, a small coffee subscription business.
Our product page gets visits, but people keep messaging to ask how subscriptions work.
We want one product page that explains the plans and sends visitors to our existing checkout.
We can supply product photos. Our spending ceiling is ₹45,000. We have not agreed a fee,
launch date, revision count or analytics baseline."""

DEMO_DRAFTS = {
    "discovery": """**Goal.** Help visitors understand a subscription and reach checkout.

**Known.** The client requests one product page and can supply photos. The spending ceiling is ₹45,000.

**Ask on the call**
- Which plan differences drive the most questions? Use the answers to prioritize page copy.
- Who controls the existing checkout and approves copy? This affects scope and handoff.
- How many visitors currently start checkout? Record a baseline before measuring change.""",
    "proposal": """Monsoon Roasters wants customers to understand its plans before checkout.
We propose one product page with a plan comparison, answers to common questions and a link to the existing checkout.

**Acceptance.** The client confirms plan details and a visitor can select a plan and reach the intended checkout on mobile and desktop.

**Scope to confirm.** Checkout changes and analytics implementation are outside this draft. The ₹45,000 figure is a client budget ceiling. Fee, timing and revision rounds remain open.

**Next step.** Confirm plan details and ownership of the checkout link before preparing a quote.""",
    "delivery": """| Milestone | Proposed owner | Input | Done when |
|---|---|---|---|
| Content inventory | Client lead | Plan details, photos, common questions | Client verifies each plan description |
| Page draft | Designer | Approved content and checkout URL | Client reviews the mobile and desktop layouts |
| Handoff | Delivery lead | Approved layouts | Checkout links work and acceptance criteria are recorded |

**Before kickoff.** Confirm scope acceptance, fee, launch date and who signs off. Request original photos and the checkout URLs. Establish a conversion baseline if measurement is agreed.""",
}
