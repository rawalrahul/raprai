# Playbook: Take and Save a Screenshot
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.97
ENVIRONMENT: Windows 11

## Preconditions
- Target content visible on screen

## Steps
### Method A — Snipping Tool (recommended, precise)
1. Press Win+Shift+S to open snip overlay
2. Click and drag to select the region to capture
3. Snip copies to clipboard AND shows a notification
4. Click the notification to open Snipping Tool editor
5. In editor: File → Save As (or Ctrl+S), choose format (PNG preferred), set filename and destination, Save
6. Verify file exists at saved path

### Method B — Full screen (quick)
1. Press PrintScreen (or PrtScn) to capture full screen to clipboard
2. Open Paint: Win+R → mspaint → Enter
3. Ctrl+V to paste
4. Ctrl+S to save, choose PNG, set destination

### Method C — Win+PrintScreen (auto-save)
1. Press Win+PrtScn
2. Screenshot auto-saves to C:\Users\{user}\Pictures\Screenshots\
3. Verify file appears in that folder

## Fallback
- If Win+Shift+S doesn't work: try Snipping Tool via Start menu search
- If clipboard paste fails: retry the capture first

## Notes
- PNG format preferred (lossless, smaller than BMP)
- Win+Shift+S is the fastest for precise regions — learn this shortcut
- Auto-naming from Win+PrtScn uses timestamp — rename immediately if specific name needed
