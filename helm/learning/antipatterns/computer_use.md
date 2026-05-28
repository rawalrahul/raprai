# Antipatterns: computer_use tasks

Known failure modes to avoid when executing computer_use tasks.

## AP-001: Clicking Before Page/App Loads
**Symptom:** Clicks register on wrong element because UI shifted during load
**Avoid:** Taking action immediately after navigation or app launch
**Do instead:** Take a screenshot first, verify the expected state, then act

## AP-002: Absolute Pixel Coordinates
**Symptom:** Works on one resolution/DPI but fails on others
**Avoid:** Hardcoding x,y coordinates like click(1240, 89)
**Do instead:** Describe elements by visual anchor (address bar, Submit button, etc.)

## AP-003: Consecutive Screenshots with No Action
**Symptom:** Infinite loop of looking without doing — wastes time
**Avoid:** More than 2 consecutive screenshots with no tool action between them
**Do instead:** If uncertain after 2 screenshots, try a keyboard approach or ask user

## AP-004: Assuming App State
**Symptom:** Actions fail because app is in unexpected state
**Avoid:** Proceeding without verifying current state
**Do instead:** Always take a screenshot at start of task to confirm starting state

## AP-005: Ignoring Error Dialogs
**Symptom:** Subsequent actions fail because unhandled error dialog is blocking
**Avoid:** Acting on a window when an error dialog may be open
**Do instead:** After any potentially error-prone action, take screenshot and scan for dialog boxes

## AP-006: Typing Into Wrong Field
**Symptom:** Text entered in wrong input field
**Avoid:** Typing without confirming focus first
**Do instead:** Click the target field explicitly, verify it has focus (cursor visible), then type

## AP-007: Clicking Taskbar Icon to Close
**Symptom:** Window minimizes instead of closing — task appears complete but isn't
**Avoid:** Right-clicking or clicking the taskbar icon expecting it to close the app
**Do instead:** Use Alt+F4 or File → Exit from within the app window

## AP-008: Missing Ctrl+A Before Typing in Existing Field
**Symptom:** New text appended to existing text instead of replacing it
**Avoid:** Clicking a field and immediately typing when it may contain existing content
**Do instead:** Click field, press Ctrl+A to select all, then type replacement text

## AP-009: Acting on Stale Screenshot
**Symptom:** Clicking element that moved or disappeared since last screenshot
**Avoid:** Using coordinates or positions from a screenshot taken more than 1 action ago
**Do instead:** Take fresh screenshot before each click action; UI state changes

## AP-010: Submitting Form Without Verification
**Symptom:** Form submitted with wrong/missing data
**Avoid:** Clicking Submit immediately after filling fields
**Do instead:** Take screenshot after filling all fields, review all values, then submit

## AP-011: Excessive Retry on Element-Not-Found
**Symptom:** Infinite loop clicking approximately correct area hoping element appears
**Avoid:** More than 2 retries on same element click
**Do instead:** After 2 failures, take full screenshot and reorient — element may have moved or dialog may be blocking

## AP-012: Chrome Ctrl+T Focus Issue
**Symptom:** New tab opens but address bar focus doesn't transfer on slow systems
**Avoid:** Immediately typing after Ctrl+T on slow machines
**Do instead:** After Ctrl+T, press Ctrl+L explicitly to ensure address bar focus before typing
