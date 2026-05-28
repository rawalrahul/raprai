# Antipatterns: code.write tasks

## AP-001: Writing Code Without Reading Existing Patterns
**Avoid:** Inventing new patterns when existing code already has conventions
**Do instead:** Read 2-3 adjacent files first to understand naming, structure, imports

## AP-002: Not Handling the Obvious Edge Cases
**Avoid:** Writing happy-path only without None/empty/error handling
**Do instead:** Consider: what if input is None? Empty? Wrong type?
