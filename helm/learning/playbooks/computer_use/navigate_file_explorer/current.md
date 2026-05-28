# Playbook: Navigate File Explorer to Path
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.91
ENVIRONMENT: Windows 11, File Explorer

## Preconditions
- Windows File Explorer available

## Steps
1. Open File Explorer: Win+E (keyboard preferred over clicking taskbar icon)
2. Take screenshot, verify Explorer window visible (address bar shows current path)
3. Press Ctrl+L or click address bar to focus it
4. Type the full path directly (e.g. C:\Users\<you>\Documents)
5. Press Enter
6. Take screenshot, verify path changed and folder contents visible

## Fallback
- If Ctrl+L fails: Alt+D also focuses address bar in Explorer
- If path doesn't exist: check spelling, try parent directory first
- If Explorer won't open: try Start menu → "File Explorer" or run `explorer.exe`

## Anchors (resolution-independent)
- Address bar: horizontal bar at top showing current folder path
- Navigation buttons (Back/Forward): arrows on left of address bar
- Folder contents pane: large central area showing files/folders

## Notes
- Typing full path directly is faster than clicking through folder tree
- Always verify arrival at correct path before acting on contents
- For paths with spaces: type as-is (no quotes needed in Explorer address bar)
