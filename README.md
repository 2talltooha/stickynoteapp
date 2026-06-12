# Desktop Checklist Widget

A frameless, semi-transparent sticky-note checklist for Windows 11. It lives in
the top-right corner of your primary screen and is visible **only when the
Windows desktop is showing**. Focus any other app and it hides itself; return to
the desktop and it reappears.

Pure Python standard library — `tkinter` + `ctypes`. No installs, no pip.

---

## Requirements

- Windows 11 (or 10)
- Python 3 installed and on your PATH

---

## Running it

Double-click `checklist_widget.py`, or from a terminal:

```
python checklist_widget.py
```

To launch with **no console window**, use `pythonw`:

```
pythonw checklist_widget.py
```

---

## Using the widget

| Action            | How                                                      |
| ----------------- | ------------------------------------------------------- |
| Add a task        | Type in the box, press **Enter** (or click **+**)       |
| Mark done / undo  | Click the **○ / ✔** checkbox on the left of a task      |
| Delete a task     | Click the **✕** on the right of a task                  |
| Reorder (buttons) | Click **▲ / ▼** on a row to move it up / down one spot   |
| Reorder (drag)    | Press a task's text and drag it; drop on the blue line   |
| Move the widget   | Drag it by the **"Tasks"** header bar                   |
| Close the widget  | Click the **✕** in the header (top-right)               |

Completed tasks show as strikethrough + dimmed text. Every add, toggle, delete,
or reorder is saved to `tasks.json` immediately.

---

## Show / hide behavior

The widget appears **only** when the Windows desktop is the active window:

- Press **Win+D** (or click the wallpaper) → widget appears.
- Switch to any other app (Chrome, a game, anything) → widget hides.
- While you are clicking or typing **in the widget itself**, it stays visible.

This is automatic. It polls the foreground window ~4×/second. Fullscreen and
borderless-fullscreen games hide it completely — no overlay on top of gameplay.

---

## Saving

All tasks are saved to **`tasks.json`** in the same folder as the script, and
reloaded on startup. If that file is missing or corrupt, the widget simply
starts empty — it never crashes on a read/write error.

---

## Easy launch

Both methods use **`pythonw.exe`** (not `python.exe`) so **no console window**
appears. The exact command both shortcuts point at:

```
pythonw.exe "C:\Users\awsom\OneDrive\Documents\cooode\claudecode\projects\sticky note app\checklist_widget.py"
```

You can set up either or both.

### a) Desktop shortcut (double-click to open)

1. Right-click an empty spot on the **desktop** → **New ▸ Shortcut**.
2. In *"Type the location of the item"* paste the command above (with quotes
   around the `.py` path), then click **Next**.
3. Name it `Tasks` (or anything) and click **Finish**.
4. Right-click the new shortcut → **Properties**:
   - **Start in:** set to the script's folder:
     `C:\Users\awsom\OneDrive\Documents\cooode\claudecode\projects\sticky note app`
   - *(optional)* **Change Icon…** → pick a `.ico` or browse to one you like.
   - Click **OK**.

Double-click it anytime to launch the widget.

### b) Auto-start at Windows logon

1. Press **Win + R**, type `shell:startup`, press Enter — the Startup folder opens.
2. Either **copy** the desktop shortcut from (a) into this folder, **or** create a
   new shortcut here the same way, pointing at the same `pythonw.exe` command.

The widget now launches automatically every time you log in. Use (a), (b), or
both — they don't conflict.

---

## Tweaking appearance

Open `checklist_widget.py` and edit the constants near the top:

| Constant              | Controls                                  |
| --------------------- | ----------------------------------------- |
| `BG`, `FG`, `DIM`, …  | Colors (dark theme by default)            |
| `WIN_W`, `WIN_H`      | Window size                               |
| `MARGIN`              | Gap from the screen edges                 |
| `ALPHA`               | Transparency (0 = invisible, 1 = solid)   |
| `POLL_MS`             | How often it checks the foreground window |
| `FONT`                | Font family and size                      |
