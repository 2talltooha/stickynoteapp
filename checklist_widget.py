"""Desktop-only checklist widget for Windows 11.

Frameless, semi-transparent sticky note that lives in the top-right of the
primary screen and is visible ONLY while the Windows desktop is the foreground
window (or while you are interacting with the widget itself). Standard library
only: tkinter + ctypes. No pip installs.

Features: add / toggle / delete tasks, reorder via ▲ ▼ buttons or drag-to-drop,
dark theme, persists to tasks.json next to the script.

Auto-start at logon: press Win+R, type `shell:startup`, and drop a shortcut in
there whose target is:  pythonw.exe "<full path>\checklist_widget.py"
(pythonw = no console window). See README / note for exact steps.
"""

import ctypes
import json
import os
import tkinter as tk
import tkinter.font as tkfont

# --------------------------------------------------------------------------
# Tweakable constants  (palette + geometry — edit freely)
# --------------------------------------------------------------------------
BG = "#1b1d21"          # window background (behind everything)
SURFACE = "#24262b"     # task-area / card surface
ROW_BG = "#24262b"      # task row default background
ROW_HOVER = "#2e3138"   # task row background on hover
HEADER_BG = "#2d2f36"   # header bar background
INPUT_BG = "#2a2c32"    # entry background
ACCENT = "#5b8cff"      # checkbox-done / add button / drag indicator
ACCENT_HOVER = "#6f9bff"
FG = "#e7e9ee"          # normal text
DIM = "#71757f"         # completed / secondary text
DANGER = "#ff6b6b"      # delete hover
DIVIDER = "#34373f"     # hairline between rows

WIN_W = 300             # window width  (px)
WIN_H = 400             # window height (px)
MARGIN = 20             # gap from screen edges (px)

ALPHA = 0.94            # window opacity (0..1)
POLL_MS = 250           # foreground-window poll interval (ms)
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 10

# Window classes that count as "the shell" (i.e. you are looking at the desktop,
# not at a real app). Foreground in any of these -> widget stays visible.
SHELL_CLASSES = {
    "Progman",                 # desktop (Win+D / wallpaper)
    "WorkerW",                 # desktop behind icons
    "Shell_TrayWnd",           # primary taskbar
    "Shell_SecondaryTrayWnd",  # taskbar on secondary monitors
}

TASKS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "tasks.json"
)

# Win32 / ctypes
user32 = ctypes.windll.user32
GA_ROOT = 2  # GetAncestor flag -> top-level window of a child hwnd


def get_class_name(hwnd):
    """Return the Win32 class name of hwnd, or '' on failure."""
    try:
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value
    except Exception:
        return ""


# --------------------------------------------------------------------------
# Persistence (never crash on IO / JSON errors)
# --------------------------------------------------------------------------
def load_tasks():
    try:
        with open(TASKS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = []
        for item in data:
            out.append({"text": str(item["text"]), "done": bool(item["done"])})
        return out
    except Exception:
        return []


def save_tasks(tasks):
    try:
        with open(TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=2)
    except Exception:
        pass  # never crash on write failure


# --------------------------------------------------------------------------
# Widget
# --------------------------------------------------------------------------
class ChecklistWidget:
    def __init__(self):
        self.tasks = load_tasks()
        self._drag = (0, 0)            # header move drag anchor
        self._visible = True           # deiconify/withdraw state (anti-flicker)

        # row reorder drag state
        self.row_frames = []           # task row frames, in display order
        self.drag_src = None           # source index being dragged
        self.dragging = False          # motion seen since press

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", ALPHA)
        self.root.configure(bg=BG)

        x = self.root.winfo_screenwidth() - WIN_W - MARGIN
        y = MARGIN
        self.root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

        # Fonts
        self.font = tkfont.Font(family=FONT_FAMILY, size=FONT_SIZE)
        self.font_done = tkfont.Font(
            family=FONT_FAMILY, size=FONT_SIZE, overstrike=1
        )
        self.font_bold = tkfont.Font(
            family=FONT_FAMILY, size=FONT_SIZE + 1, weight="bold"
        )

        self._build_header()
        self._build_input()

        # Task list area (the "card" surface)
        self.tasks_outer = tk.Frame(self.root, bg=SURFACE)
        self.tasks_outer.pack(fill="both", expand=True, padx=10, pady=(2, 10))
        self.tasks_frame = tk.Frame(self.tasks_outer, bg=SURFACE)
        self.tasks_frame.pack(fill="both", expand=True, padx=4, pady=6)

        # Reusable drop indicator (placed only while dragging)
        self.indicator = tk.Frame(self.tasks_frame, bg=ACCENT, height=2)

        self.render_tasks()

        # Capture own top-level hwnd once the window is realized.
        self.root.update_idletasks()
        self.own_hwnd = user32.GetAncestor(self.root.winfo_id(), GA_ROOT)

        self.root.after(POLL_MS, self.poll_foreground)

    # -- UI construction ---------------------------------------------------
    def _build_header(self):
        header = tk.Frame(self.root, bg=HEADER_BG, height=40)
        header.pack(fill="x", padx=10, pady=(10, 6))
        header.pack_propagate(False)

        title = tk.Label(
            header, text="✓  Tasks", bg=HEADER_BG, fg=FG, font=self.font_bold
        )
        title.pack(side="left", padx=12)

        close = tk.Label(
            header, text="✕", bg=HEADER_BG, fg=DIM,
            font=(FONT_FAMILY, 12), cursor="hand2",
        )
        close.pack(side="right", padx=12)
        close.bind("<Button-1>", lambda e: self.on_close())
        close.bind("<Enter>", lambda e: close.configure(fg=DANGER))
        close.bind("<Leave>", lambda e: close.configure(fg=DIM))

        # Drag-to-move on the header bar + title label
        for w in (header, title):
            w.bind("<Button-1>", self.start_drag)
            w.bind("<B1-Motion>", self.do_drag)

    def _build_input(self):
        row = tk.Frame(self.root, bg=BG)
        row.pack(fill="x", padx=10, pady=(0, 6))

        wrap = tk.Frame(row, bg=INPUT_BG)
        wrap.pack(side="left", fill="x", expand=True)
        self.entry = tk.Entry(
            wrap, bg=INPUT_BG, fg=FG, insertbackground=ACCENT,
            relief="flat", font=self.font, highlightthickness=0, bd=0,
        )
        self.entry.pack(fill="x", expand=True, padx=10, pady=7)
        self.entry.bind("<Return>", lambda e: self.add_task())

        add = tk.Label(
            row, text="+", bg=ACCENT, fg="#ffffff",
            font=(FONT_FAMILY, 14, "bold"), width=3, cursor="hand2",
        )
        add.pack(side="left", fill="y", padx=(8, 0))
        add.bind("<Button-1>", lambda e: self.add_task())
        add.bind("<Enter>", lambda e: add.configure(bg=ACCENT_HOVER))
        add.bind("<Leave>", lambda e: add.configure(bg=ACCENT))

    # -- Task rendering ----------------------------------------------------
    def render_tasks(self):
        for child in self.tasks_frame.winfo_children():
            if child is not self.indicator:
                child.destroy()
        self.indicator.place_forget()
        self.row_frames = []

        for idx, task in enumerate(self.tasks):
            self._build_row(idx, task)

    def _build_row(self, idx, task):
        done = task["done"]

        row = tk.Frame(self.tasks_frame, bg=ROW_BG, height=34)
        row.pack(fill="x", pady=(0, 1))
        row.pack_propagate(False)
        self.row_frames.append(row)

        # checkbox
        box = tk.Label(
            row, text="✔" if done else "", bg=ROW_BG,
            fg=ACCENT if done else DIM, font=(FONT_FAMILY, 11, "bold"),
            width=2, cursor="hand2",
        )
        if not done:
            box.configure(text="○", fg=DIM, font=(FONT_FAMILY, 12))
        box.pack(side="left", padx=(8, 2))
        box.bind("<Button-1>", lambda e, i=idx: self.toggle_task(i))

        # text (also the drag handle)
        text = tk.Label(
            row, text=task["text"], bg=ROW_BG,
            fg=DIM if done else FG,
            font=self.font_done if done else self.font,
            anchor="w", justify="left", cursor="fleur",
        )
        text.pack(side="left", fill="x", expand=True, padx=2)
        text.bind("<Button-1>", lambda e, i=idx: self.drag_start(e, i))
        text.bind("<B1-Motion>", self.drag_motion)
        text.bind("<ButtonRelease-1>", self.drag_release)

        # right-side controls: ▲ ▼ ✕
        up = tk.Label(row, text="▲", bg=ROW_BG, fg=DIM,
                      font=(FONT_FAMILY, 8), cursor="hand2")
        up.pack(side="left", padx=(2, 0))
        up.bind("<Button-1>", lambda e, i=idx: self.move_task(i, -1))

        down = tk.Label(row, text="▼", bg=ROW_BG, fg=DIM,
                        font=(FONT_FAMILY, 8), cursor="hand2")
        down.pack(side="left", padx=(0, 2))
        down.bind("<Button-1>", lambda e, i=idx: self.move_task(i, 1))

        delete = tk.Label(row, text="✕", bg=ROW_BG, fg=DIM,
                          font=(FONT_FAMILY, 11), cursor="hand2")
        delete.pack(side="right", padx=(2, 8))
        delete.bind("<Button-1>", lambda e, i=idx: self.delete_task(i))

        kids = (row, box, text, up, down, delete)

        # hover highlight (whole row) — skip while a reorder drag is active
        def on_enter(_e, ws=kids):
            if not self.dragging:
                self._set_row_bg(ws, ROW_HOVER)
            delete.configure(fg=DANGER)

        def on_leave(_e, ws=kids):
            if not self.dragging:
                self._set_row_bg(ws, ROW_BG)
            delete.configure(fg=DIM)

        for w in kids:
            w.bind("<Enter>", on_enter, add="+")
            w.bind("<Leave>", on_leave, add="+")

    @staticmethod
    def _set_row_bg(widgets, color):
        for w in widgets:
            try:
                w.configure(bg=color)
            except Exception:
                pass

    # -- Task operations ---------------------------------------------------
    def add_task(self):
        text = self.entry.get().strip()
        if not text:
            return
        self.tasks.append({"text": text, "done": False})
        self.entry.delete(0, "end")
        save_tasks(self.tasks)
        self.render_tasks()

    def toggle_task(self, idx):
        self.tasks[idx]["done"] = not self.tasks[idx]["done"]
        save_tasks(self.tasks)
        self.render_tasks()

    def delete_task(self, idx):
        del self.tasks[idx]
        save_tasks(self.tasks)
        self.render_tasks()

    def move_task(self, idx, direction):
        """Move task up (direction=-1) or down (+1) by one position."""
        target = idx + direction
        if target < 0 or target >= len(self.tasks):
            return
        self.tasks[idx], self.tasks[target] = (
            self.tasks[target], self.tasks[idx]
        )
        save_tasks(self.tasks)
        self.render_tasks()

    def on_close(self):
        save_tasks(self.tasks)
        self.root.destroy()

    # -- Header move dragging ----------------------------------------------
    def start_drag(self, event):
        self._drag = (event.x_root, event.y_root)

    def do_drag(self, event):
        dx = event.x_root - self._drag[0]
        dy = event.y_root - self._drag[1]
        x = self.root.winfo_x() + dx
        y = self.root.winfo_y() + dy
        self.root.geometry(f"+{x}+{y}")
        self._drag = (event.x_root, event.y_root)

    # -- Row reorder dragging ----------------------------------------------
    def drag_start(self, event, idx):
        self.drag_src = idx
        self.dragging = False

    def _target_index(self, y_root):
        """Insertion index (0..len) for the current pointer y."""
        for i, rf in enumerate(self.row_frames):
            mid = rf.winfo_rooty() + rf.winfo_height() / 2
            if y_root < mid:
                return i
        return len(self.row_frames)

    def drag_motion(self, event):
        if self.drag_src is None:
            return
        self.dragging = True
        target = self._target_index(event.y_root)
        self._show_indicator(target)

    def _show_indicator(self, target):
        base = self.tasks_frame.winfo_rooty()
        if target < len(self.row_frames):
            rf = self.row_frames[target]
            y = rf.winfo_rooty() - base
        elif self.row_frames:
            last = self.row_frames[-1]
            y = last.winfo_rooty() + last.winfo_height() - base
        else:
            y = 0
        self.indicator.place(x=4, y=max(0, y - 1), relwidth=1.0, width=-8)
        self.indicator.lift()

    def drag_release(self, event):
        src = self.drag_src
        was_dragging = self.dragging
        self.drag_src = None
        self.dragging = False
        self.indicator.place_forget()

        if src is None or not was_dragging:
            return
        target = self._target_index(event.y_root)
        item = self.tasks.pop(src)
        if target > src:
            target -= 1
        target = max(0, min(target, len(self.tasks)))
        self.tasks.insert(target, item)
        save_tasks(self.tasks)
        self.render_tasks()

    # -- Desktop-only visibility -------------------------------------------
    def _should_show(self, fg):
        """Show whenever no genuine app window is in front.

        Visible when: no foreground window, the foreground IS the widget,
        the foreground is a shell window (desktop / taskbar), or the
        foreground window isn't actually visible. Hidden only when a real,
        visible, non-shell top-level app owns the foreground -- which still
        includes borderless/fullscreen games.
        """
        if not fg:
            return True                       # no active window -> desktop-ish
        if fg == self.own_hwnd:
            return True                       # interacting with the widget
        if get_class_name(fg) in SHELL_CLASSES:
            return True                       # desktop / taskbar in front
        try:
            if not user32.IsWindowVisible(fg):
                return True                   # phantom / hidden fg window
        except Exception:
            pass
        return False                          # a real app window -> hide

    def poll_foreground(self):
        try:
            fg = user32.GetForegroundWindow()
            should_show = self._should_show(fg)

            if should_show and not self._visible:
                self.root.deiconify()
                self.root.attributes("-topmost", True)  # re-assert after show
                self._visible = True
            elif not should_show and self._visible:
                self.root.withdraw()
                self._visible = False
        except Exception:
            pass  # never crash the poll loop
        finally:
            self.root.after(POLL_MS, self.poll_foreground)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    ChecklistWidget().run()
