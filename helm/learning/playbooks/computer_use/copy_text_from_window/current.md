# Playbook: Copy Text From a Window
TASK_TYPE: computer_use
STATUS: active
SUCCESS_RATE: 0.91

## Steps
1. Take screenshot to identify the window containing the text
2. Click on the window to give it focus
3. If selectable text: Ctrl+A to select all, or click-drag to select specific range
4. Ctrl+C to copy
5. Verify: open Notepad (Win+R, notepad, Enter), Ctrl+V to paste, read pasted content
6. Close Notepad without saving (Alt+F4, N)

## Fallback
- If text not selectable (image/PDF): use OCR approach — take screenshot, extract text via vision AI
- If Ctrl+A selects too much: click at start, shift+click at end for precise selection

## Notes
- Always verify copy succeeded before reporting — paste to verify
