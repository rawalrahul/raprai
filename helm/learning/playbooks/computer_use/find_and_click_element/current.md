# Playbook: Find and Click a UI Element
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.85
ENVIRONMENT: Windows 11, any application or browser

## Preconditions
- Application window is open and visible

## Steps
1. Take screenshot to see current state
2. Identify the target element by description (button text, label, icon type)
3. Scan screenshot systematically: top toolbar → left panel → main content → bottom bar
4. If element found: estimate its center coordinates relative to known landmarks (NOT absolute pixels)
5. Click the element
6. Take screenshot immediately after click to verify state changed as expected

## If element not immediately visible:
- Scroll down (Page Down or scroll wheel) and take new screenshot
- Check if element is in a different tab or panel
- Try Ctrl+F (in browsers/some apps) to search for text within the page

## Fallback
- If element position seems off: take a new screenshot (don't rely on previous positions)
- If clicking fails: try keyboard navigation (Tab to cycle through focusable elements, Enter to activate)
- If still not found: describe element to confirm correct window/app is in focus

## Anchors strategy
- Identify landmarks first: title bar text, top-left logo, distinctive panel borders
- Describe element position relative to anchor: "button to the right of the search box"
- Never hardcode absolute pixel positions — they change with resolution/DPI/window size

## Notes
- Two consecutive screenshots with no state change = element click didn't register — reassess
- DPI scaling means visual position ≠ click target on high-DPI screens — use keyboard when possible
- After any click, always verify with screenshot before next action
