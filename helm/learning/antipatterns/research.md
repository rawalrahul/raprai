# Antipatterns: research tasks

Known failure modes to avoid when executing search, summarize, and fact-check tasks.

## AP-001: First Result Assumption
**Symptom:** Answer based on first search result without verifying against others
**Avoid:** Treating a single source as authoritative
**Do instead:** Cross-reference at least 2-3 sources for factual claims; note when sources disagree

## AP-002: Outdated Information
**Symptom:** Providing stale facts (prices, versions, dates, policies)
**Avoid:** Answering from memory on time-sensitive topics
**Do instead:** Search for current information; explicitly state information date when relevant

## AP-003: Hallucinating Missing Details
**Symptom:** Filling in plausible-sounding details that weren't in any source
**Avoid:** Synthesizing beyond what sources actually say to make answer seem complete
**Do instead:** State clearly what was found and what wasn't; say "not found" rather than guess

## AP-004: Summary Distortion
**Symptom:** Summary changes the meaning or emphasis of source material
**Avoid:** Paraphrasing without checking the paraphrase preserves the key claim
**Do instead:** Quote key claims directly; summarize structure, not just content

## AP-005: Ignoring User's Specific Question
**Symptom:** Research answers adjacent topic instead of the exact question asked
**Avoid:** Broad answers when user asked something specific
**Do instead:** Re-read the exact question before writing; answer the specific question first, then broader context

## AP-006: Over-long Research Loops
**Symptom:** Spending 10+ searches on a question that had a good answer after 2
**Avoid:** Diminishing-returns search loops driven by uncertainty
**Do instead:** If 3 searches haven't produced a clear answer, say so and present best available info
