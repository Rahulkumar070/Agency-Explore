"""Fixed demonstration material for one fictional engagement."""
import json

BRIEF = """Monsoon Roasters wants a subscription page and two Instagram posts.
Visitors ask about delivery frequency. Checkout already exists. Product photos are ready.
The client has a spending ceiling of ₹45,000. Fee and launch date are open.
Last month 240 visitors reached the page and 12 began checkout. The owner approves copy."""

SAMPLES = {
    "qualification": ("Fee and launch date are open.", "Prepare discovery questions.",
                      "Ask who the page serves, which delivery intervals exist, and when the owner can review. Confirm the decision process before quoting."),
    "pitch": ("Visitors ask about delivery frequency.", "Draft a call opener and follow-up.",
              "Call opener: Which delivery question comes up most often? Follow-up: We can draft one plan comparison. Could you confirm the intervals you offer?"),
    "scope": ("spending ceiling of ₹45,000", "Draft scope and identify open terms.",
              "Proposed scope: one subscription page and two Instagram posts. The ₹45,000 ceiling is a budget constraint. Agree a fee and revision count before kickoff."),
    "brand": ("Visitors ask about delivery frequency.", "Define a concrete message direction.",
              "Proposed direction: lead with how the subscription fits a customer's routine. Use plain language and publish delivery intervals after owner confirmation."),
    "copy": ("Checkout already exists.", "Draft the page headline and next action.",
             "Headline: Find your coffee routine. Body: Compare subscription options, then choose a plan at checkout. CTA: See subscription options."),
    "content": ("two Instagram posts", "Write two post concepts.",
                "Post 1, carousel: “How often would you like fresh coffee?” Pair the approved intervals with product photos. Post 2, walkthrough: “From plan to checkout in three steps.” End with a link to the subscription page."),
    "web": ("Checkout already exists.", "Map the page and checkout path.",
            "Place a plan comparison before the checkout link. Test keyboard navigation and mobile layout. The link passes if it reaches the intended existing checkout."),
    "production": ("Product photos are ready.", "Prepare the kickoff sequence.",
                   "Client owner supplies photos and verifies plan details. Designer drafts the page and two posts. Owner approves copy. Delivery lead checks the checkout path before handoff."),
    "qa": ("The owner approves copy.", "Write acceptance checks.",
           "Open the page at mobile width, navigate using a keyboard, and follow the primary link. Pass when the correct checkout opens, intervals match owner-approved text, and the two posts use approved photos."),
    "measurement": ("240 visitors reached the page and 12 began checkout", "Calculate the baseline and propose a reporting metric.",
                    "Checkout-start rate was 12 / 240 = 5%. Count page visitors and checkout starts over the same period. Purchases and revenue are unknown."),
    "accounts": ("The owner approves copy.", "Draft a client status update.",
                 "Photos are ready. Please confirm delivery intervals and choose who will verify the checkout destination. We will draft copy after that decision. Fee and launch date remain open."),
    "resourcing": ("Fee and launch date are open.", "Identify the capacity bottleneck.",
                   "Queue design after plan details are confirmed. Prepare the post layouts while the owner checks the page copy. Schedule launch once the owner approves the assets."),
}

SELECTION = {
    "agency": ("scope", "copy", "production", "measurement"),
    "sales": ("qualification", "pitch", "scope"),
    "studio": ("brand", "copy", "content"),
    "delivery": ("web", "production", "qa"),
    "operations": ("measurement", "accounts", "resourcing"),
}


def sample_response(agent, brief, context):
    if agent.name == "manager":
        names = SELECTION[context["desk"]]
        return json.dumps({"assignments": [
            {"role": name, "task": SAMPLES[name][1], "evidence": SAMPLES[name][0]} for name in names
        ]}, ensure_ascii=False)
    if agent.name == "reviewer":
        return ("Keep the ₹45,000 ceiling separate from fees. Delivery intervals, project "
                "dates and revenue are unconfirmed. Describe checkout starts as starts, not sales.")
    if agent.name == "editor":
        sections = [f"### {key.title()}\n\n{value}" for key, value in context["work"].items()]
        sections.append("**Next decision.** Ask the owner to confirm delivery intervals before finalizing copy, scope and timing.")
        return "\n\n".join(sections)
    return SAMPLES[agent.name][2]
