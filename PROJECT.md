# Desktop Checklist Widget — Project Notes

A frameless, semi-transparent sticky-note checklist for Windows 11 that is
visible **only when you are looking at the desktop** (no real app window in
front). Pure Python standard library — `tkinter` + `ctypes`. No pip, no installs.

This file is the single place to look back on what was built, why, and where to
edit things.

---

## Files in this folder

| File                  | What it is                                                    |
| --------------------- | ------------------------------------------------------------- |
| `checklist_widget.py` | The entire application (single file).                         |
| `tasks.json`          | Auto-created saved tasks. Safe to delete (starts empty).      |
| `Open Checklist.bat`  | Double-click launcher, no console window.                     |
| `README.md`           | End-user usage guide.                                         |
| `PROJECT.md`          | This file — design notes + change history.                    |

---

## What it does (current behavior)

- **Frameless top-right widget**, dark theme, semi-transparent (`ALPHA`).
- **Add** a task: type in the box, Enter or click **+**.
- **Toggle done**: click the **○ / ✔** checkbox → strikethrough + dimmed.
- **Delete**: click **✕** on the right of a row.
- **Reorder** two ways:
  - **▲ / ▼** buttons move a row one slot.
  - **Drag-to-drop**: press a task's text, drag, drop on the blue insertion line.
- **Move the whole widget**: drag the **"Tasks"** header bar.
- **Persistence**: every change writes `tasks.json` next to the script. Loads on
  startup. Never crashes on a bad/missing/corrupt file (load → `[]`, save → silent).
- **Desktop-only visibility**: appears whenever no genuine app window is in front;
  hides the moment a real app (incl. fullscreen/borderless games) takes focus.

---

## How it works (the tricky parts)

### Desktop-only visibility — `poll_foreground` + `_should_show`
- Polls every `POLL_MS` (250ms) via `root.after`.
- `user32.GetForegroundWindow()` → foreground hwnd; `GetClassNameW` → its class.
- `_should_show(fg)` returns **show** when:
  - `fg` is null/0 (no active window), **or**
  - `fg` is the widget's **own hwnd** (so it stays up while you type/drag in it), **or**
  - `fg` class is in `SHELL_CLASSES` (`Progman`, `WorkerW`, `Shell_TrayWnd`,
    `Shell_SecondaryTrayWnd` = desktop + taskbars), **or**
  - `fg` is **not** `IsWindowVisible` (phantom window).
  - Otherwise → **hide** (a real visible non-shell app, which is also how
    fullscreen games get hidden).
- **Own hwnd** captured once via `GetAncestor(root.winfo_id(), GA_ROOT)` after the
  window is realized.
- **Anti-flicker**: `_visible` flag; only call `deiconify`/`withdraw` when state
  actually changes. After `deiconify`, re-assert `-topmost`.

### Reorder drag
- Task **text label** is the drag handle (`fleur` cursor).
- `drag_start` records source index; `drag_motion` sets `dragging=True` and shows
  the blue `indicator` line; `_target_index(y_root)` picks the drop slot by
  comparing the pointer to each row's vertical midpoint.
- `drag_release` does `pop(src)` then `insert(target)` (with an index-shift
  correction when `target > src`), saves, re-renders.
- Hover highlight is suppressed while `dragging` so the row colors stay stable.

### Window chrome
- `overrideredirect(True)` = frameless; `-topmost` + `-alpha ALPHA` = floating,
  see-through. Header drag uses `start_drag`/`do_drag` to reposition via
  `geometry("+x+y")`.

---

## Where to edit things

All knobs are constants at the **top of `checklist_widget.py`**:

| Constant                         | Controls                                       |
| -------------------------------- | ---------------------------------------------- |
| `BG`, `SURFACE`, `ROW_BG`, `ROW_HOVER`, `HEADER_BG`, `INPUT_BG` | Backgrounds (layered dark theme) |
| `ACCENT`, `ACCENT_HOVER`         | Checkbox-done / + button / drag line color     |
| `FG`, `DIM`, `DANGER`, `DIVIDER` | Text + delete-hover + hairline colors          |
| `WIN_W`, `WIN_H`                 | Window size                                    |
| `MARGIN`                         | Gap from screen edges (top-right placement)    |
| `ALPHA`                          | Transparency (0 = invisible … 1 = solid)       |
| `POLL_MS`                        | Foreground-window poll interval (ms)           |
| `FONT_FAMILY`, `FONT_SIZE`       | Font stack (Segoe UI)                          |
| `SHELL_CLASSES`                  | Which window classes count as "the desktop"    |

Common edits:
- **Move to a different corner** → change the `x`/`y` math in `__init__`
  (`geometry(...)`).
- **More/less transparent** → `ALPHA`.
- **Faster/slower show-hide reaction** → `POLL_MS`.
- **A game/app still shows the widget on top** → add its window class to a HIDE
  rule, or confirm it's `IsWindowVisible`; if a shell-like window wrongly hides it,
  add that class to `SHELL_CLASSES`.

---

## How to launch

- **Double-click** `Open Checklist.bat` (runs `start "" pythonw.exe "%~dp0checklist_widget.py"`,
  with a `py -w` fallback). No console window, portable with the folder.
- **Manual**: `pythonw checklist_widget.py` (no console) or `python checklist_widget.py`.
- **Desktop shortcut**: right-click desktop → New ▸ Shortcut → target
  `pythonw.exe "C:\...\checklist_widget.py"` → set **Start in** to the script
  folder. If `pythonw` isn't found, use the full path to `pythonw.exe` (next to
  `python.exe` in your Python install dir) or the `py` launcher: `py -w "C:\...\checklist_widget.py"`.
- **Auto-start at logon**: Win+R → `shell:startup` → drop a copy of the shortcut
  (or the `.bat`) into that folder.

---

## Change history

1. **Initial build** — frameless top-right widget, add/toggle/delete, `tasks.json`
   persistence (crash-safe), desktop-only visibility via foreground-class polling
   (`Progman`/`WorkerW`) + own-hwnd exception, dark theme, constants up top.
2. **Docs** — `README.md` usage guide; `shell:startup` auto-start note.
3. **Reorder + polish** — ▲▼ buttons and drag-to-drop with insertion indicator;
   refreshed dark theme (layered surfaces, accent color, row hover, fixed row
   height for vertical rhythm, refined done style).
4. **Easy launch + smarter visibility** —
   - `Open Checklist.bat` double-click launcher (no console, `%~dp0` portable).
   - Broadened visibility: show whenever **no real app window** is in front
     (null fg, own hwnd, shell classes incl. taskbars, or non-visible fg) instead
     of requiring an actual desktop click; still hides for genuine apps and
     fullscreen games. Kept 250ms poll, own-hwnd check, and `_visible` anti-flicker.

---

## Known limits / notes

- **Windows-only** — relies on `user32` window-class semantics.
- A game that briefly drops foreground (loading screens, exclusive→borderless
  flips) may blink the widget in for ≤ one poll (250ms). Harmless; raise `POLL_MS`
  or add a debounce if it bothers you.
- `tkinter` can't truly round corners; the "rounded feel" is padding + a colored
  header bar, not real radii.
- Single primary-monitor placement (top-right of the primary screen).
