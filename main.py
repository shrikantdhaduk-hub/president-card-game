"""
main.py
=======
Application entry point for the President Card Game.

Run with:
    python main.py

Requirements:
    Python 3.8+   (tkinter is part of the standard library — no extra installs)

Project structure:
    main.py          ← you are here (app root, screen router)
    cards.py         ← Card, Suit, deck/deal helpers
    game_state.py    ← Player, GameState, all game rules
    ai_engine.py     ← Easy / Medium / Hard AI decision engine
    gui_widgets.py   ← Reusable Tkinter widgets & colour theme
    gui_screens.py   ← SetupScreen, GameScreen, TradeDialog, RulesScreen
"""

from __future__ import annotations
import tkinter as tk
from tkinter import messagebox
from typing import List, Optional

from cards import Card
from game_state import GameState, Player, Phase
from gui_screens import SetupScreen, GameScreen, RulesScreen
from gui_widgets import C, F, make_button, apply_theme


class App(tk.Tk):
    """
    Root window and screen router.
    Owns the GameState; passes it to child screens.
    """

    def __init__(self):
        super().__init__()
        self.title("President Card Game")
        self.configure(bg=C["bg"])
        self.geometry("1150x720")
        self.minsize(950, 620)
        apply_theme(self)

        self._state:          Optional[GameState] = None
        self._current_screen: Optional[tk.Widget] = None

        self._show_setup()

    # ── Screen switching ──────────────────────────────────────────────────────

    def _switch(self, screen: tk.Widget):
        if self._current_screen:
            self._current_screen.destroy()
        self._current_screen = screen
        screen.pack(fill="both", expand=True)

    def _show_setup(self):
        self._switch(SetupScreen(self, self._on_game_start))

    # ── Game start ────────────────────────────────────────────────────────────

    def _on_game_start(self, names: List[str], types: List[str],
                        difficulties: List[str], n_decks: int, demo: bool):
        """
        Called by SetupScreen when the user presses Start.

        Parameters
        ----------
        names        : player names in seat order
        types        : "Human" or "AI" per player
        difficulties : "Easy", "Medium", or "Hard" per player
        n_decks      : number of decks to use
        demo         : first game is a tutorial
        """
        state = GameState()
        state.n_decks   = n_decks
        state.demo_mode = demo

        for name, ptype, diff in zip(names, types, difficulties):
            state.players.append(Player(
                name       = name,
                is_human   = (ptype == "Human"),
                difficulty = diff,
            ))

        state.start_new_game()
        self._state = state

        if demo:
            messagebox.showinfo(
                "Demo Mode — How to play",
                "Welcome to the Demo game!\n\n"
                "Your hand is shown at the bottom of the screen.\n"
                "• Click a card (or multiple cards of the same rank) to SELECT it.\n"
                "• Press  ▶ Play Selected  to play your selection.\n"
                "• Press  ⏭ Pass Turn  if you cannot or don't want to play.\n"
                "• AI players take their turns automatically.\n\n"
                "The Game Log (right panel) shows every move.\n"
                "Check ☰ Menu → Rules for the full rulebook.\n\n"
                "Good luck! 🃏",
                parent=self,
            )

        game_screen = GameScreen(self, state, self._show_menu)
        self._switch(game_screen)

        # If the first turn belongs to an AI player, auto-play now
        if state.phase == Phase.PLAYING and not state.current_player.is_human:
            game_screen._run_ai_turns()
            game_screen.refresh()

    # ── In-game menu ──────────────────────────────────────────────────────────

    def _show_menu(self):
        menu = tk.Toplevel(self)
        menu.title("Menu")
        menu.configure(bg=C["bg"])
        menu.geometry("300x240")
        menu.resizable(False, False)
        menu.grab_set()

        tk.Label(menu, text="☰  Menu", font=F["heading"],
                 bg=C["bg"], fg=C["text"]).pack(pady=18)

        make_button(menu, "📖  Rules",
                    lambda: self._open_rules(menu),
                    color=C["button"]).pack(pady=5, fill="x", padx=30)

        make_button(menu, "🔄  New Game (Setup)",
                    lambda: [menu.destroy(), self._show_setup()],
                    color=C["btn_neutral"]).pack(pady=5, fill="x", padx=30)

        make_button(menu, "✕  Close Menu",
                    menu.destroy,
                    color=C["btn_neutral"]).pack(pady=5, fill="x", padx=30)

    def _open_rules(self, parent: tk.Widget = None):
        win = tk.Toplevel(parent or self)
        win.title("President — Rules")
        win.configure(bg=C["bg"])
        win.geometry("740x640")
        RulesScreen(win, win.destroy).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
