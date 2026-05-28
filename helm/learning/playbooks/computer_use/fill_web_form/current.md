# Playbook: Fill a Web Form
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.88
ENVIRONMENT: Windows, any browser

## Preconditions
- Browser open with target form page loaded
- Form fields visible

## Steps
1. Take screenshot, identify all form fields before touching anything
2. Click first field (or Tab from any focused element to reach it)
3. Clear existing content first: Ctrl+A then type new value
4. Tab to next field (preferred over clicking — faster, more reliable)
5. Repeat for each field
6. For dropdowns: click to open, then type first letter of option or use arrow keys
7. For checkboxes: click once to toggle; take screenshot to verify checked state
8. For date fields: try typing directly first; if that fails, use the calendar picker
9. Before submitting: take screenshot and verify all fields filled correctly
10. Click Submit button or press Enter if submit button is focused

## Fallback
- If Tab order is wrong: click each field individually
- If field rejects typed input: try clicking the field first then typing slowly
- If submit fails: check for red validation indicators on fields, fix them first

## Anchors
- Submit button: usually at bottom, text like "Submit", "Save", "Send", "Continue"
- Required fields: often marked with asterisk (*) or red border when empty

## Notes
- Never click Submit without a verification screenshot first
- Watch for CAPTCHA after submit — do not attempt to solve programmatically
- If page refreshes unexpectedly: take screenshot to understand new state before acting
