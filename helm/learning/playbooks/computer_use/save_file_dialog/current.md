# Playbook: Handle Save File Dialog
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.92
ENVIRONMENT: Windows 11, any application

## Preconditions
- Save dialog is open (triggered by app's File → Save As or Ctrl+Shift+S)

## Steps
1. Take screenshot to verify dialog is open and identify current path shown
2. Navigate to destination:
   - If path is simple: click address bar in dialog (Alt+D), type full path, Enter
   - If navigating: use left panel shortcuts (Desktop, Documents, Downloads) or address bar
3. In filename field (at bottom): click to focus, Ctrl+A to select all, type desired filename
4. Check "Save as type" dropdown — change format if needed
5. Click Save button (or press Enter if Save button is focused)
6. Take screenshot to verify dialog closed (success) or check for error message

## Fallback
- If address bar in dialog is read-only: use the folder tree on the left panel
- If file already exists warning appears: decide overwrite or rename before proceeding
- If Save fails: check if destination folder requires admin permissions

## Notes
- Alt+D focuses address bar in most Windows file dialogs
- Do NOT close the parent application while dialog is open
- Extension is auto-added if filename has none — verify Save as type matches intent
