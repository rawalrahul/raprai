# Playbook: Open Browser and Navigate to URL
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.94
ENVIRONMENT: Windows, Chrome/Edge/Firefox

## Preconditions
- Browser installed
- Network accessible

## Steps
1. Check if browser already running: use tasklist or check window titles via screenshot
2. If not running: use keyboard shortcut Win+R, type browser name, Enter — OR find in Start menu
3. Wait for browser window (take screenshot, verify address bar visible)
4. Press Ctrl+L to focus address bar (keyboard preferred over clicking — DPI-independent)
5. Type the URL
6. Press Enter
7. Wait for page load: take screenshot, verify page title or expected content visible

## Fallback
- If Ctrl+L fails: take screenshot, locate address bar by visual search, click it
- If browser won't open: try alternative browser

## Anchors (resolution-independent)
- Address bar: horizontal bar near top, contains current URL text
- Tab strip: row of tabs above address bar

## Notes
- Always use keyboard shortcuts over pixel clicks when possible
- Verify navigation succeeded before proceeding to next step
