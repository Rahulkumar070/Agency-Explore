"""Surface source passages and possible scope conflicts for an operator to review."""
import re

# Keep words from the original brief, including amounts and negation.
TOPICS = {
    "Scope and existing systems": r"\b(existing|scope|include|exclude|only|link to)\b",
    "Budget and fees": r"\b(budget|ceiling|fees?|price|quote|pricing)\b|[₹$€£]\d",
    "Dates and commitments": r"\b(deadlines?|dates?|agreed|confirmed|commitments?)\b",
    "Client inputs and owners": r"\b(suppl(?:y|ies)|provides?|owns?|owner|assets?|photograph\w*)\b",
}


def passages(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+|\n\s*\n", text) if s.strip()]


def scope_notes(brief, draft):
    sentences = [" ".join(s.split()) for s in passages(brief)]
    sections = []
    for topic, pattern in TOPICS.items():
        matches = [s for s in sentences if re.search(pattern, s, re.I)]
        if matches:
            sections.append(f"{topic}\n" + "\n".join(f"- {s}" for s in matches))
    warnings = []
    normal_draft = " ".join(draft.lower().split())
    for source in sentences:
        if match := re.search(r"\b(?:can |will )?(?:supply|provide) (.+?)[.!?]?$", source, re.I):
            assets = re.split(r",|\band\b", match[1])
            absent = [asset.strip() for asset in assets
                      if re.sub(r"^(?:the|our|their) ", "", asset.strip().lower()) not in normal_draft]
            if absent:
                warnings.append(f"Verify the owner and coverage of these client inputs: {', '.join(absent)}. Source: {source}")
        if re.search(r"\b(budget|ceiling)\b", source, re.I):
            for amount in re.findall(r"[₹$€£]\s*[\d,]+(?:\.\d+)?", source):
                if re.sub(r"[,\s]", "", amount) not in re.sub(r"[,\s]", "", normal_draft):
                    warnings.append(f"Check the missing budget amount {amount}. Source: {source}")
                money = re.escape(amount)
                for line in draft.splitlines():
                    if re.search(rf"\b(?:agreed fee|fixed fee|our fee|total fee)\b(?:\s+is)?[\s:*–-]*{money}", line, re.I):
                        warnings.append(f"Verify fee agreement against the spending ceiling: {line.strip()}")

    for source in sentences:
        for match in re.finditer(r"\blink\s+to\s+(?:(?:our|an?|the|their|your)\s+)?existing\s+"
                                 r"((?:[\w-]+\s+){0,2}?(?:form|website|checkout|portal|calendar|system))\b",
                                 source, re.I):
            asset = re.escape(match[1])
            action = r"(?:build|rebuild|redesign|update|modify|replace|customi[sz]e|develop|integrate)"
            pattern = rf"\b{action}\b.{{0,45}}\b{asset}\b|\b{asset}\b.{{0,35}}\b(?:must|should|will) (?:include|support|collect|be changed)"
            pattern += rf"|\b{asset}(?:['’]s)?\s+features?\b.{{0,70}}\b(?:adjusted|finalized|revised|modified|discussion)\b"
            for line in draft.splitlines():
                if re.search(pattern, line, re.I):
                    warnings.append(f"Check added work on the {match[1]}: {line.strip()}")
    return sections, list(dict.fromkeys(warnings))
