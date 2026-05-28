# Antipatterns: code.debug tasks

## AP-001: Fixing Without Reading Full Error
**Avoid:** Jumping to fix before reading the complete error message and traceback
**Do instead:** Read the full traceback bottom-up — the last frame is usually where the error is

## AP-002: Changing Multiple Things at Once
**Avoid:** Editing multiple suspects simultaneously — can't isolate root cause
**Do instead:** Change one thing, test, then change next

## AP-003: Ignoring the Actual Line Number
**Avoid:** Searching the whole codebase when the traceback gives exact line
**Do instead:** Go directly to the reported line number first
