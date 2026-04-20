"""
gui_widgets.py
==============
Reusable Tkinter widgets and style constants.
No game-logic dependencies.
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional
from cards import Card, SUIT_SYMBOL, SUIT_COLOR, RANK_NAME, Suit


# ── Colour palette ────────────────────────────────────────────────────────────

C = {
    "bg":           "#0d1b2a",
    "panel":        "#16213e",
    "table":        "#145a32",
    "card_bg":      "#f5efe6",
    "card_sel":     "#ffe066",
    "card_hover":   "#fff3cd",
    "button":       "#1e6091",
    "btn_hover":    "#2980b9",
    "btn_danger":   "#922b21",
    "btn_success":  "#1e8449",
    "btn_neutral":  "#566573",
    "accent":       "#e74c3c",
    "gold":         "#f1c40f",
    "text":         "#ecf0f1",
    "text_dim":     "#7f8c8d",
    "text_dark":    "#2c3e50",
    "border":       "#2c3e50",
    "human":        "#2471a3",
    "ai_easy":      "#1e8449",
    "ai_medium":    "#d68910",
    "ai_hard":      "#922b21",
}

# ── Font definitions ──────────────────────────────────────────────────────────

F = {
    "title":   ("Segoe UI", 28, "bold"),
    "heading": ("Segoe UI", 14, "bold"),
    "body":    ("Segoe UI", 11),
    "small":   ("Segoe UI", 9),
    "card_lg": ("Segoe UI", 13, "bold"),
    "card_sm": ("Segoe UI", 9,  "bold"),
    "mono":    ("Courier New", 9),
}


# ── Styled button factory ─────────────────────────────────────────────────────

def make_button(parent, text: str, command: Callable,
                color: str = None, **kwargs) -> tk.Button:
    """
    Create a flat, styled button.
    Any tk.Button keyword can be overridden via **kwargs
    (including 'font', 'padx', 'pady').
    """
    opts = dict(
        bg=color or C["button"],
        fg="white",
        font=F["body"],
        relief="flat",
        padx=14, pady=7,
        activebackground=C["btn_hover"],
        activeforeground="white",
        cursor="hand2",
    )
    opts.update(kwargs)   # caller overrides win
    return tk.Button(parent, text=text, command=command, **opts)


# ── Card widget ───────────────────────────────────────────────────────────────

class CardWidget(tk.Canvas):
    """
    A single playing card drawn with Canvas primitives.
    Supports selected (golden highlight) and face-down (back) modes.
    """
    W, H = 62, 88

    def __init__(self, parent, card: Card,
                 on_click: Optional[Callable[[Card], None]] = None,
                 selected: bool = False,
                 face_down: bool = False,
                 **kwargs):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=C["panel"], highlightthickness=0, **kwargs)
        self.card      = card
        self.on_click  = on_click
        self._selected = selected
        self._face_down = face_down
        self._hover    = False
        self._draw()
        if on_click:
            self.bind("<Button-1>", self._clicked)
            self.bind("<Enter>",    lambda e: self._set_hover(True))
            self.bind("<Leave>",    lambda e: self._set_hover(False))

    # ── drawing ──

    def _draw(self):
        self.delete("all")
        W, H, r = self.W, self.H, 7

        if self._face_down:
            self._draw_back(W, H, r)
            return

        bg = C["card_sel"] if self._selected else (
             C["card_hover"] if self._hover else C["card_bg"])

        # Rounded rectangle (4 arcs + 3 rects)
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, 0, W, r*2, start=0, extent=90, fill=bg, outline=bg)
        self.create_arc(0, H-r*2, r*2, H, start=180, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, H-r*2, W, H, start=270, extent=90, fill=bg, outline=bg)
        self.create_rectangle(r, 0, W-r, H, fill=bg, outline=bg)
        self.create_rectangle(0, r, W, H-r, fill=bg, outline=bg)

        # Border
        border = "#f39c12" if self._selected else "#bbb"
        bw     = 2 if self._selected else 1
        self.create_rectangle(2, 2, W-2, H-2, outline=border, width=bw)

        color = SUIT_COLOR[self.card.suit]
        rank  = RANK_NAME[self.card.rank]
        sym   = SUIT_SYMBOL[self.card.suit]

        # Top-left pip
        self.create_text(5, 3,  anchor="nw", text=rank, font=F["card_sm"], fill=color)
        self.create_text(5, 14, anchor="nw", text=sym,  font=F["card_sm"], fill=color)

        # Centre
        self.create_text(W//2, H//2, text=f"{rank}\n{sym}",
                         font=F["card_lg"], fill=color, justify="center")

        # Bottom-right pip (rotated)
        self.create_text(W-5, H-3,  anchor="se", text=rank, font=F["card_sm"], fill=color)
        self.create_text(W-5, H-14, anchor="se", text=sym,  font=F["card_sm"], fill=color)

        # Queen of Hearts crown marker
        if self.card.is_queen_of_hearts:
            self.create_text(W//2, H-8, text="♛", font=("Segoe UI", 7), fill=C["accent"])

    def _draw_back(self, W, H, r):
        bg = "#1a5276"
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, 0, W, r*2, start=0, extent=90, fill=bg, outline=bg)
        self.create_arc(0, H-r*2, r*2, H, start=180, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, H-r*2, W, H, start=270, extent=90, fill=bg, outline=bg)
        self.create_rectangle(r, 0, W-r, H, fill=bg, outline=bg)
        self.create_rectangle(0, r, W, H-r, fill=bg, outline=bg)
        self.create_rectangle(2, 2, W-2, H-2, outline="#2980b9", width=2)
        self.create_text(W//2, H//2, text="🂠", font=("Segoe UI", 22), fill="#2980b9")

    # ── public API ──

    def set_selected(self, v: bool):
        self._selected = v
        self._draw()

    def set_face_down(self, v: bool):
        self._face_down = v
        self._draw()

    # ── events ──

    def _set_hover(self, v: bool):
        self._hover = v
        self._draw()
        self.configure(cursor="hand2" if v else "")

    def _clicked(self, _):
        if self.on_click:
            self.on_click(self.card)


# ── Scrollable hand frame ─────────────────────────────────────────────────────

class HandFrame(tk.Frame):
    """
    A horizontally-scrollable strip of CardWidgets.
    Cards can be toggled selected by clicking.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["bg"], **kwargs)
        self._canvas = tk.Canvas(self, bg=C["bg"], height=100, highlightthickness=0)
        self._scroll = ttk.Scrollbar(self, orient="horizontal",
                                     command=self._canvas.xview)
        self._canvas.configure(xscrollcommand=self._scroll.set)
        self._scroll.pack(side="bottom", fill="x")
        self._canvas.pack(fill="both", expand=True)
        self._inner = tk.Frame(self._canvas, bg=C["bg"])
        self._window = self._canvas.create_window(0, 0, anchor="nw", window=self._inner)
        self._inner.bind("<Configure>", lambda e: self._canvas.configure(
            scrollregion=self._canvas.bbox("all")))

        self._widgets: dict[Card, CardWidget] = {}
        self._selected: set[Card] = set()
        self._on_change: Optional[Callable] = None

    def set_on_change(self, cb: Callable):
        """Called whenever selection changes."""
        self._on_change = cb

    def load(self, cards: list[Card], interactive: bool = True):
        """Rebuild the hand display."""
        for w in self._inner.winfo_children():
            w.destroy()
        self._widgets.clear()
        self._selected.clear()

        for card in cards:
            sel = card in self._selected
            cw = CardWidget(
                self._inner, card,
                on_click=self._toggle if interactive else None,
                selected=sel,
            )
            cw.pack(side="left", padx=2, pady=6)
            self._widgets[card] = cw

    def _toggle(self, card: Card):
        if card in self._selected:
            self._selected.discard(card)
        else:
            self._selected.add(card)
        self._widgets[card].set_selected(card in self._selected)
        if self._on_change:
            self._on_change()

    def get_selected(self) -> list[Card]:
        return list(self._selected)

    def clear_selection(self):
        for card in list(self._selected):
            self._selected.discard(card)
            if card in self._widgets:
                self._widgets[card].set_selected(False)
        if self._on_change:
            self._on_change()


# ── Game log widget ───────────────────────────────────────────────────────────

class LogPanel(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["panel"], **kwargs)
        tk.Label(self, text="Game Log", font=F["heading"],
                 bg=C["panel"], fg=C["text"]).pack(pady=(8, 2))
        self._text = tk.Text(self, bg=C["bg"], fg="#aaffaa",
                             font=F["mono"], wrap="word",
                             state="disabled", relief="flat",
                             selectbackground=C["panel"])
        scr = ttk.Scrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y")
        self._text.pack(fill="both", expand=True, padx=4, pady=(0, 6))

    def update(self, messages: list[str]):
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("end", "\n".join(messages[-120:]))
        self._text.see("end")
        self._text.configure(state="disabled")


# ── Player info sidebar ───────────────────────────────────────────────────────

class PlayerPanel(tk.Frame):

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=C["panel"], **kwargs)
        tk.Label(self, text="Players", font=F["heading"],
                 bg=C["panel"], fg=C["text"]).pack(pady=(8, 4))
        self._rows: list[tk.Frame] = []

    def refresh(self, players, current_idx: int, finished_order: list[int]):
        for w in self.winfo_children()[1:]:
            w.destroy()

        titles = {0: "👑", 1: "⭐"}
        n = len(players)

        for i, p in enumerate(players):
            is_current = (i == current_idx)
            is_finished = (p.finish_rank is not None)

            bg = "#1e3a5f" if is_current else C["panel"]
            fg = C["gold"] if is_current else C["text"]
            if is_finished:
                fg = "#f39c12"

            row = tk.Frame(self, bg=bg, pady=3)
            row.pack(fill="x", padx=4, pady=1)

            # Title badge
            badge = ""
            if is_finished and p.finish_rank is not None:
                rank = p.finish_rank
                if rank == 1:       badge = "👑"
                elif rank == 2:     badge = "⭐"
                elif rank == n:     badge = "💀"
                else:               badge = f"#{rank}"

            prefix = "▶ " if is_current else "  "

            # Difficulty colour tag
            diff_color = C["text_dim"]
            if not p.is_human:
                diff_color = {"Easy": C["ai_easy"],
                              "Medium": C["ai_medium"],
                              "Hard": C["ai_hard"]}.get(p.difficulty, C["text_dim"])

            tk.Label(row, text=f"{prefix}{p.icon} {badge}",
                     bg=bg, fg=fg, font=F["small"], width=6,
                     anchor="w").pack(side="left")
            tk.Label(row, text=p.name, bg=bg, fg=fg,
                     font=F["small"], anchor="w").pack(side="left")
            if not is_finished:
                tag = p.difficulty_short
                tk.Label(row, text=tag, bg=bg, fg=diff_color,
                         font=F["small"]).pack(side="left", padx=2)
                tk.Label(row, text=f"[{len(p.hand)}]", bg=bg,
                         fg=C["text_dim"], font=F["small"]).pack(side="right", padx=4)


# ── TTK theme setup ───────────────────────────────────────────────────────────

def apply_theme(root: tk.Tk):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("TScrollbar",
                    background=C["panel"],
                    troughcolor=C["bg"],
                    bordercolor=C["bg"],
                    arrowcolor=C["text_dim"])
    style.configure("TCombobox",
                    fieldbackground=C["panel"],
                    background=C["panel"],
                    foreground=C["text"],
                    selectbackground=C["panel"],
                    selectforeground=C["text"])
