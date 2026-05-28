# Playbook: Close a Window Safely
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.96
ENVIRONMENT: Windows 11

## Preconditions
- Target window is visible or in taskbar

## Steps
1. Take screenshot to identify current state of the window
2. Check for unsaved changes indicators: asterisk in title bar, "modified" text, unsaved badge
3. If unsaved changes: save first (Ctrl+S), then verify save succeeded
4. Close the window:
   - Keyboard (preferred): Alt+F4 when window is focused
   - Menu: File → Close or File → Exit
   - Last resort: click X button in title bar
5. If "Save changes?" dialog appears: choose appropriate option (Save / Don't Save / Cancel)
6. Take screenshot to verify window is closed

## Fallback
- If Alt+F4 doesn't close (some apps intercept it): use File → Exit
- If app is frozen: right-click taskbar icon → Close window; or use Task Manager (Ctrl+Shift+Esc)
- NEVER use Task Manager kill unless app is unresponsive — data loss risk

## Notes
- CRITICAL: Never click X on taskbar icon to close — it minimizes, not closes
- Always check for unsaved changes BEFORE initiating close
- Some apps (browsers) close all tabs when closing — check tab count first
- Task Manager kill (End Task) loses unsaved data — only for frozen apps
