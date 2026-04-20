"""
gui_screens.py
==============
All GUI screens:
  SetupScreen   – player config, deck count, demo toggle
  GameScreen    – main playing area
  TradeInfoDialog – automatic trade summary before next round
  RulesScreen   – scrollable rules reference
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, List, Optional

from cards import Card, Suit, SUIT_COLOR
from game_state import GameState, Phase, AI_DIFFICULTY_LABELS
from ai_engine import choose_play
from gui_widgets import C, F, make_button, CardWidget, HandFrame, LogPanel, PlayerPanel


# ─────────────────────────────────────────────────────────────────────────────
# Setup Screen
# ─────────────────────────────────────────────────────────────────────────────

class SetupScreen(tk.Frame):
    """
    Lets users configure:
      • Number of decks (1–5)
      • Demo mode toggle
      • Each player: name, Human or AI, AI difficulty
    """

    def __init__(self, parent, on_start: Callable):
        super().__init__(parent, bg=C["bg"])
        self.on_start = on_start
        # Per-player vars: (name_var, type_var, diff_var)
        self._player_rows: List[dict] = []
        self._build()

    # ── Build ──

    def _build(self):
        # Title
        tk.Label(self, text="♠  President  ♥", font=F["title"],
                 bg=C["bg"], fg=C["text"]).pack(pady=(28, 4))
        tk.Label(self, text="The Classic Social Card Game",
                 font=F["body"], bg=C["bg"], fg=C["text_dim"]).pack()

        # ── Options panel ──
        opts = tk.Frame(self, bg=C["panel"], padx=24, pady=18)
        opts.pack(padx=60, pady=16, fill="x")

        # Decks
        tk.Label(opts, text="Number of Decks (1–5):", font=F["body"],
                 bg=C["panel"], fg=C["text"]).grid(row=0, column=0, sticky="w", pady=6)
        self._deck_var = tk.IntVar(value=1)
        tk.Spinbox(opts, from_=1, to=5, textvariable=self._deck_var,
                   width=4, font=F["body"],
                   bg=C["panel"], fg=C["text"],
                   buttonbackground=C["panel"]).grid(row=0, column=1, sticky="w", padx=8)

        # Demo
        self._demo_var = tk.BooleanVar(value=False)
        tk.Checkbutton(opts, text="First game as Demo (teach new players)",
                       variable=self._demo_var,
                       bg=C["panel"], fg=C["text"],
                       selectcolor=C["bg"],
                       activebackground=C["panel"],
                       activeforeground=C["text"],
                       font=F["small"]).grid(row=1, column=0, columnspan=3,
                                             sticky="w", pady=4)

        # ── Players section ──
        tk.Label(opts, text="Players  (4–10 recommended):",
                 font=F["body"], bg=C["panel"],
                 fg=C["text"]).grid(row=2, column=0, columnspan=3,
                                    sticky="w", pady=(14, 6))

        # Column headers
        hdr = tk.Frame(opts, bg=C["panel"])
        hdr.grid(row=3, column=0, columnspan=3, sticky="ew")
        for col, (txt, w) in enumerate([("#", 3), ("Name", 18),
                                         ("Type", 10), ("Difficulty", 10)]):
            tk.Label(hdr, text=txt, font=F["small"], bg=C["panel"],
                     fg=C["text_dim"], width=w, anchor="w").grid(row=0, column=col,
                                                                   padx=4)

        self._rows_frame = tk.Frame(opts, bg=C["panel"])
        self._rows_frame.grid(row=4, column=0, columnspan=3, sticky="ew")

        # Default 4 players: P1 = Human, rest = AI Medium
        self._add_row("Player 1", "Human",  "Medium")
        self._add_row("Player 2", "AI",     "Medium")
        self._add_row("Player 3", "AI",     "Medium")
        self._add_row("Player 4", "AI",     "Hard")

        # Add/Remove buttons
        btn_row = tk.Frame(opts, bg=C["panel"])
        btn_row.grid(row=5, column=0, columnspan=3, pady=10)
        make_button(btn_row, "+ Add Player",    self._add_player,
                    color=C["button"],   font=F["small"],
                    padx=10, pady=4).pack(side="left", padx=5)
        make_button(btn_row, "– Remove Player", self._remove_player,
                    color=C["btn_neutral"], font=F["small"],
                    padx=10, pady=4).pack(side="left", padx=5)

        # Start
        make_button(self, "▶   Start Game", self._start,
                    color=C["btn_success"],
                    font=F["heading"]).pack(pady=20)

    def _add_row(self, default_name: str = "", default_type: str = "AI",
                 default_diff: str = "Medium"):
        i   = len(self._player_rows)
        row = tk.Frame(self._rows_frame, bg=C["panel"])
        row.pack(fill="x", pady=2)

        name_var = tk.StringVar(value=default_name or f"Player {i+1}")
        type_var = tk.StringVar(value=default_type)
        diff_var = tk.StringVar(value=default_diff)

        tk.Label(row, text=f"{i+1}.", width=3, font=F["small"],
                 bg=C["panel"], fg=C["text_dim"]).pack(side="left")

        tk.Entry(row, textvariable=name_var, font=F["body"],
                 width=16, bg=C["bg"], fg=C["text"],
                 insertbackground=C["text"]).pack(side="left", padx=4)

        # Type toggle button
        type_btn = tk.Button(row, textvariable=type_var, width=8,
                             font=F["small"], relief="flat",
                             cursor="hand2")
        type_btn.pack(side="left", padx=4)
        self._style_type_btn(type_btn, type_var.get())

        def _toggle_type(btn=type_btn, tv=type_var, dv=diff_var):
            new = "AI" if tv.get() == "Human" else "Human"
            tv.set(new)
            self._style_type_btn(btn, new)
            # Disable difficulty for humans
            for w in btn.master.winfo_children():
                if isinstance(w, ttk.Combobox):
                    w.configure(state="disabled" if new == "Human" else "readonly")

        type_btn.configure(command=_toggle_type)

        # Difficulty combobox
        diff_cb = ttk.Combobox(row, textvariable=diff_var,
                               values=AI_DIFFICULTY_LABELS,
                               width=8, state="readonly" if default_type == "AI" else "disabled",
                               font=F["small"])
        diff_cb.pack(side="left", padx=4)

        self._player_rows.append({
            "name": name_var,
            "type": type_var,
            "diff": diff_var,
            "frame": row,
        })

    def _style_type_btn(self, btn: tk.Button, type_val: str):
        if type_val == "Human":
            btn.configure(bg=C["human"], fg="white",
                          activebackground=C["human"])
            btn.configure(text="👤 Human")
        else:
            btn.configure(bg=C["ai_medium"], fg="white",
                          activebackground=C["ai_medium"])
            btn.configure(text="🤖 AI")

    def _add_player(self):
        if len(self._player_rows) >= 12:
            messagebox.showinfo("Limit Reached", "Maximum 12 players supported.")
            return
        self._add_row()

    def _remove_player(self):
        if len(self._player_rows) <= 2:
            messagebox.showinfo("Minimum Players", "Need at least 2 players.")
            return
        last = self._player_rows.pop()
        last["frame"].destroy()

    def _start(self):
        names = [r["name"].get().strip() for r in self._player_rows]
        types = [r["type"].get()         for r in self._player_rows]
        diffs = [r["diff"].get()         for r in self._player_rows]

        # Validation
        names = [n for n in names if n]
        if len(names) < 2:
            messagebox.showerror("Error", "Enter at least 2 player names.")
            return
        if len(set(names)) != len(names):
            messagebox.showerror("Error", "Player names must be unique.")
            return

        self.on_start(names, types, diffs, self._deck_var.get(), self._demo_var.get())


# ─────────────────────────────────────────────────────────────────────────────
# Game Screen
# ─────────────────────────────────────────────────────────────────────────────

class GameScreen(tk.Frame):
    """
    Main game screen layout:
      Left   – player list sidebar
      Centre – table, action buttons, human hand
      Right  – game log
    """

    def __init__(self, parent, state: GameState, on_menu: Callable):
        super().__init__(parent, bg=C["bg"])
        self.state              = state
        self.on_menu            = on_menu
        self._hand_frame:       Optional[HandFrame] = None
        self._game_over_shown:  bool = False   # prevent double game-over dialog
        self._build()
        self.refresh()

    # ── Layout ──

    def _build(self):
        # ── Top bar ──
        top = tk.Frame(self, bg=C["panel"], pady=6)
        top.pack(fill="x")
        tk.Label(top, text="♠ President ♥", font=F["heading"],
                 bg=C["panel"], fg=C["text"]).pack(side="left", padx=14)
        self._status_lbl = tk.Label(top, text="", font=F["body"],
                                     bg=C["panel"], fg=C["gold"])
        self._status_lbl.pack(side="left", padx=20)
        make_button(top, "☰ Menu", self.on_menu,
                    color=C["btn_neutral"],
                    font=F["small"], padx=10, pady=4).pack(side="right", padx=10)

        # ── Main three-column area ──
        main = tk.Frame(self, bg=C["bg"])
        main.pack(fill="both", expand=True)

        # Left: player panel
        self._player_panel = PlayerPanel(main, width=175)
        self._player_panel.pack(side="left", fill="y", padx=(5, 0), pady=5)
        self._player_panel.pack_propagate(False)

        # Right: log
        self._log_panel = LogPanel(main, width=210)
        self._log_panel.pack(side="right", fill="y", padx=(0, 5), pady=5)
        self._log_panel.pack_propagate(False)

        # Centre
        centre = tk.Frame(main, bg=C["bg"])
        centre.pack(side="left", fill="both", expand=True, padx=6, pady=5)

        # Table (green felt)
        table_outer = tk.Frame(centre, bg=C["table"], padx=10, pady=8)
        table_outer.pack(fill="x")
        tk.Label(table_outer, text="Table", font=F["small"],
                 bg=C["table"], fg="#aaffaa").pack(anchor="w")
        self._table_cards_frame = tk.Frame(table_outer, bg=C["table"], height=106)
        self._table_cards_frame.pack(fill="x", pady=4)
        self._table_info_lbl = tk.Label(table_outer, text="",
                                         font=F["small"], bg=C["table"], fg="#ccffcc")
        self._table_info_lbl.pack()

        # Action buttons
        btn_bar = tk.Frame(centre, bg=C["bg"])
        btn_bar.pack(pady=8)
        self._play_btn = make_button(btn_bar, "▶  Play Selected",
                                     self._on_play, color=C["btn_success"])
        self._play_btn.pack(side="left", padx=5)
        self._pass_btn = make_button(btn_bar, "⏭  Pass Turn",
                                     self._on_pass, color=C["btn_neutral"])
        self._pass_btn.pack(side="left", padx=5)
        self._clear_btn = make_button(btn_bar, "✕  Clear",
                                      self._on_clear, color=C["btn_neutral"])
        self._clear_btn.pack(side="left", padx=5)

        self._nudge_btn = make_button(btn_bar, "⚡ Nudge AI",
                                      self._on_nudge, color="#7d3c98",
                                      font=F["small"], padx=10, pady=4)
        self._nudge_btn.pack(side="left", padx=10)

        # Hand area
        hand_hdr = tk.Frame(centre, bg=C["bg"])
        hand_hdr.pack(fill="x")
        self._hand_title = tk.Label(hand_hdr, text="", font=F["body"],
                                     bg=C["bg"], fg=C["text"])
        self._hand_title.pack(side="left")
        self._hand_count = tk.Label(hand_hdr, text="", font=F["small"],
                                     bg=C["bg"], fg=C["text_dim"])
        self._hand_count.pack(side="left", padx=8)

        self._hand_frame = HandFrame(centre, height=112)
        self._hand_frame.pack(fill="x", pady=(4, 0))
        self._hand_frame.set_on_change(self._on_selection_change)

    # ── Refresh ──

    def refresh(self):
        s = self.state
        self._refresh_table()
        self._refresh_hand()
        self._refresh_buttons()
        self._player_panel.refresh(s.players, s.current_idx, s.finished_order)
        self._log_panel.update(s.log_messages)
        self._refresh_status()

    def _refresh_status(self):
        s = self.state
        if s.phase == Phase.GAME_OVER:
            winner = s.players[s.finished_order[0]].name if s.finished_order else "?"
            self._status_lbl.config(text=f"🎉 Game Over!  👑 President: {winner}")
        else:
            p = s.current_player
            icon = "👤" if p.is_human else "🤖"
            self._status_lbl.config(
                text=f"{icon} {p.name}'s turn  —  Game #{s.game_number}"
            )

    def _refresh_table(self):
        for w in self._table_cards_frame.winfo_children():
            w.destroy()

        s = self.state
        if not s.table_pile:
            # last_played_by set but table empty → 7 was just played
            if s.last_played_by is not None:
                msg = "7️⃣  Table reset! Play any card (any value)"
                clr = "#ffe066"
            else:
                msg = "— empty table —"
                clr = "#555"
            tk.Label(self._table_cards_frame, text=msg,
                     bg=C["table"], fg=clr, font=F["body"]).pack(pady=24)
            self._table_info_lbl.config(text="")
            return

        # Show last 4 plays
        for play in s.table_pile[-4:]:
            pf = tk.Frame(self._table_cards_frame, bg=C["table"])
            pf.pack(side="left", padx=5)
            for card in sorted(play):
                CardWidget(pf, card).pack(side="left", padx=1)

        self._table_info_lbl.config(text=f"Required: {s.required_count} card(s)")

    def _refresh_hand(self):
        s = self.state
        # Find the first human player (assumed seat 0 by convention but
        # we search so it works even if the human is not seat 0)
        human_idx = self._human_seat()
        if human_idx is None:
            self._hand_title.config(text="No human player")
            return

        human = s.players[human_idx]
        is_your_turn = (s.current_idx == human_idx) and s.phase == Phase.PLAYING
        self._hand_title.config(
            text=f"{human.name}'s Hand",
            fg=C["gold"] if is_your_turn else C["text"]
        )
        self._hand_count.config(text=f"({len(human.hand)} cards)")
        self._hand_frame.load(human.hand, interactive=is_your_turn)

    def _refresh_buttons(self):
        s = self.state
        human_idx = self._human_seat()
        active = (s.current_idx == human_idx
                  and s.phase == Phase.PLAYING
                  and human_idx is not None)
        st = "normal" if active else "disabled"
        self._play_btn.config(state=st)
        self._pass_btn.config(state=st)
        self._clear_btn.config(state=st)

    def _human_seat(self) -> Optional[int]:
        for i, p in enumerate(self.state.players):
            if p.is_human:
                return i
        return None

    # ── User interactions ──

    def _on_selection_change(self):
        """Called whenever the player clicks a card."""
        pass  # Could update a "you selected X" label here

    def _on_play(self):
        cards = self._hand_frame.get_selected()
        if not cards:
            messagebox.showinfo("Nothing selected",
                                "Click cards in your hand to select them, then press Play.")
            return
        result = self.state.play_cards(cards)
        self._hand_frame.clear_selection()
        self._handle_result(result)

    def _on_pass(self):
        result = self.state.pass_turn()
        self._hand_frame.clear_selection()
        self._handle_result(result)

    def _on_clear(self):
        self._hand_frame.clear_selection()

    def _handle_result(self, result: str):
        if result == "game_over":
            self.refresh()
            self._show_game_over()
        elif result in ("ok", "queen_wins", "unbeatable", "round_end", "seven_played"):
            self._run_ai_turns()
            self.refresh()
            # After AI turns, re-check game over
            if self.state.phase == Phase.GAME_OVER:
                self._show_game_over()
        else:
            # result is an error message
            messagebox.showwarning("Invalid Play", result)
            self.refresh()

    # ── AI auto-play ──

    # ── AI turn execution ─────────────────────────────────────────────────────

    def _run_ai_turns(self):
        """
        Synchronous fallback used right after a human plays.
        Runs up to MAX consecutive AI steps; if it hits the limit it schedules
        _tick_ai() to continue asynchronously so the UI never hard-freezes.
        """
        s   = self.state
        MAX = 300          # steps before handing back to the event loop
        for _ in range(MAX):
            if s.phase != Phase.PLAYING:
                return
            if s.current_player.is_human:
                return
            if not self._do_one_ai_step():
                return     # game over

        # Limit reached — continue via after() to stay responsive
        self._schedule_ai()

    def _schedule_ai(self):
        """Schedule one AI step on the Tkinter event loop (non-blocking)."""
        self.after(60, self._tick_ai)

    def _tick_ai(self):
        """One AI move, then reschedule if more are needed."""
        s = self.state
        if s.phase != Phase.PLAYING or s.current_player.is_human:
            self.refresh()
            return
        alive = self._do_one_ai_step()
        self.refresh()
        if alive and s.phase == Phase.PLAYING and not s.current_player.is_human:
            self._schedule_ai()
        elif s.phase == Phase.GAME_OVER:
            self._show_game_over()

    def _do_one_ai_step(self) -> bool:
        """
        Execute exactly one AI action (play or pass).
        Returns False if the game ended, True otherwise.
        Detects stale turns: if the AI player is not in active_players and
        the table has no card to beat, force-ends the round to prevent loops.
        """
        s      = self.state
        player = s.current_player

        # Safety: if this AI is not in active_players, skip them gracefully
        if s.current_idx not in s.active_players:
            # Nowhere to go — force-end the round to unstick
            if s.last_played_by is not None:
                s._end_round()
            else:
                # Nobody has played yet; just advance
                if s.active_players:
                    s.current_idx = s.active_players[0]
                else:
                    return False
            return True

        cards_in_hands = [len(p.hand) for p in s.players]
        play = choose_play(
            hand           = player.hand,
            required_count = s.required_count if s.top_play is not None else 1,
            top_card       = s.top_card,
            difficulty     = player.difficulty,
            cards_in_hands = cards_in_hands,
            my_position    = s.current_idx,
        )

        result = s.play_cards(play) if play else s.pass_turn()

        if result == "game_over":
            return False   # caller (_run_ai_turns / _tick_ai) handles game-over
        return True

    def _on_nudge(self):
        """
        Force-advance a stuck AI turn.
        Safe to call at any time:
          • If it's an AI's turn, immediately execute one step then continue.
          • If it's the human's turn, show a friendly message.
          • If the game is over, do nothing.
        """
        s = self.state
        if s.phase != Phase.PLAYING:
            return
        if s.current_player.is_human:
            messagebox.showinfo("Nudge AI",
                                "It's your turn! Select cards and press Play.",
                                parent=self)
            return
        # Force one step then let the normal async chain take over
        alive = self._do_one_ai_step()
        self.refresh()
        if alive and s.phase == Phase.PLAYING and not s.current_player.is_human:
            self._schedule_ai()
        elif s.phase == Phase.GAME_OVER:
            self._show_game_over()

    # ── Game over / next game ──

    def _show_game_over(self):
        # Guard: only show once per completed game
        if self._game_over_shown:
            return
        self._game_over_shown = True

        s = self.state
        n = len(s.players)
        titles = {1: "👑 President", 2: "⭐ Vice-President"}
        lines  = ["━━ Final Rankings ━━\n"]
        for pos, idx in enumerate(s.finished_order, 1):
            p     = s.players[idx]
            title = titles.get(pos, f"#{pos}")
            if pos == n:
                title = "💀 Peasant"
            lines.append(f"  {title}: {p.name}")

        answer = messagebox.askquestion(
            "Game Over",
            "\n".join(lines) + "\n\nPlay another round?",
            icon="info"
        )
        if answer == "yes":
            self._start_next_game()

    def _start_next_game(self):
        """
        Transition to the next game.
        start_next_game_with_trade() handles everything in the correct order:
          deal fresh cards FIRST, then swap (so president's hand is never empty).
        """
        self._game_over_shown = False   # reset guard before anything else
        s      = self.state
        result = s.start_next_game_with_trade()

        if result is None:
            # Edge case: couldn't determine president/peasant — just refresh
            self._hand_frame.clear_selection()
            self.refresh()
            return

        pres_idx, peasant_idx, pres_gave, peasant_gave = result
        pres    = s.players[pres_idx]
        peasant = s.players[peasant_idx]

        # Show trade summary; _finish_next_game is called when it closes
        TradeInfoDialog(self, pres, peasant, pres_gave, peasant_gave,
                        self._finish_next_game)

    def _finish_next_game(self):
        """Called when the TradeInfoDialog closes. Game is already running."""
        self._hand_frame.clear_selection()
        self.refresh()
        # Kick off AI if AI goes first
        if self.state.phase == Phase.PLAYING and not self.state.current_player.is_human:
            self._run_ai_turns()
            self.refresh()


# ─────────────────────────────────────────────────────────────────────────────
# Trade Info Dialog  (replaces the old manual TradeDialog)
# ─────────────────────────────────────────────────────────────────────────────

class TradeInfoDialog(tk.Toplevel):
    """
    Read-only summary of the automatic card trade.
    Shows what each player gave/received, then auto-closes after 4 seconds
    (or immediately when the player clicks Continue).
    """

    AUTO_CLOSE_MS = 4000   # milliseconds before auto-proceeding

    def __init__(self, parent, pres: "Player", peasant: "Player",
                 pres_gave: Card, peasant_gave: Card,
                 on_done: Callable):
        super().__init__(parent)
        self.title("💱  Card Trade — Automatic")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.on_done    = on_done
        self._after_id  = None
        self._build(pres, peasant, pres_gave, peasant_gave)
        self._start_countdown()

    def _build(self, pres, peasant, pres_gave, peasant_gave):
        tk.Label(self, text="💱  Card Trade", font=F["heading"],
                 bg=C["bg"], fg=C["text"]).pack(pady=(14, 4))

        tk.Label(self,
                 text="Cards have been exchanged automatically.",
                 font=F["small"], bg=C["bg"], fg=C["text_dim"]).pack()

        # Trade summary box
        box = tk.Frame(self, bg=C["panel"], padx=20, pady=14)
        box.pack(padx=24, pady=12, fill="x")

        def trade_row(giver, receiver, card, row):
            tk.Label(box, text=f"{giver.icon} {giver.name}",
                     font=F["body"], bg=C["panel"],
                     fg=C["gold"], anchor="e", width=18).grid(
                     row=row, column=0, padx=6, pady=4)
            tk.Label(box, text="gave",
                     font=F["small"], bg=C["panel"],
                     fg=C["text_dim"]).grid(row=row, column=1, padx=4)
            # Mini card display
            card_lbl = tk.Label(box,
                text=card.label(),
                font=F["heading"],
                bg=C["card_bg"] if not card.is_queen_of_hearts else C["accent"],
                fg=SUIT_COLOR[card.suit],
                relief="groove", padx=8, pady=4, width=4)
            card_lbl.grid(row=row, column=2, padx=6)
            tk.Label(box, text="→  to",
                     font=F["small"], bg=C["panel"],
                     fg=C["text_dim"]).grid(row=row, column=3, padx=4)
            tk.Label(box, text=f"{receiver.icon} {receiver.name}",
                     font=F["body"], bg=C["panel"],
                     fg=C["text"], anchor="w", width=18).grid(
                     row=row, column=4, padx=6, pady=4)

        # Row 0: Peasant gave best → President
        trade_row(peasant, pres, peasant_gave, 0)
        # Row 1: President gave worst → Peasant
        trade_row(pres, peasant, pres_gave, 1)

        # Countdown label
        self._countdown_lbl = tk.Label(self,
            text="", font=F["small"], bg=C["bg"], fg=C["text_dim"])
        self._countdown_lbl.pack(pady=(0, 4))

        make_button(self, "▶  Continue to Next Game",
                    self._proceed, color=C["btn_success"],
                    font=F["body"]).pack(pady=(4, 16))

    def _start_countdown(self):
        self._remaining = self.AUTO_CLOSE_MS // 1000
        self._tick()

    def _tick(self):
        self._countdown_lbl.config(
            text=f"Starting automatically in {self._remaining}s …")
        if self._remaining <= 0:
            self._proceed()
            return
        self._remaining -= 1
        self._after_id = self.after(1000, self._tick)

    def _proceed(self):
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        self.destroy()
        self.on_done()


# ─────────────────────────────────────────────────────────────────────────────
# Rules Screen
# ─────────────────────────────────────────────────────────────────────────────

RULES_TEXT = """
PRESIDENT  —  Complete Rules
════════════════════════════════════════

PLAYERS & DECKS
• 4–10 players recommended (no hard limit).
• Choose 1–5 standard decks (no Jokers).

CARD VALUES  (lowest → highest)
  Suits:   ♣ Clubs  <  ♠ Spades  <  ♦ Diamonds  <  ♥ Hearts
  Ranks:   3 < 4 < 5 < 6 < 7 < 8 < 9 < 10 < J < Q < K < A < 2
  Trump:   Queen of Hearts (Q♥) beats EVERYTHING, including 2♥.

DEALING
• Cards are shuffled and dealt as evenly as possible.
• Each player sorts their hand from lowest to highest value.
• Do NOT show your hand to other players.

GAME START
• Game 1:  The player holding 3♣ goes first and MUST play it.
• Later games:  The previous Peasant goes first (regardless of 3♣).

HOW A ROUND WORKS
1. The starting player places card(s) face-up on the table.
2. Going clockwise, each player may place a HIGHER card (or combination).
3. If a player cannot or chooses not to play, they PASS for that round.
4. The round ends when every other player passes in succession.
5. The player who placed the last (highest) card WINS the round.
6. The round's cards are discarded. The winner starts the next round.

THE 7 RULE
• When any 7 is played, the NEXT player must play a LOWER value card.
• The direction stays "lower" until the round ends naturally.
• This gives holders of low cards a chance to play them!

MULTIPLES (doubles, triples, quads …)
• A player STARTING a round may play 2 or more cards of the SAME rank.
  Example: start with two 6s → all subsequent plays must also be pairs.
• The highest single card within the combination determines order.
  Example: 6♥ + 6♠ beats 6♦ + 6♣  (because 6♥ > 6♦ in suit rank).
• Q♥ (as a single) ALWAYS beats any combination when required count = 1.

ENDING A ROUND EARLY
• Playing a 2 in the "up" direction ends the round immediately
  (nothing can beat a 2 in normal play).
• Playing Q♥ ALWAYS ends the round instantly, regardless of direction.

FINISHING THE GAME
• The first player to empty their hand = 🏆  THE PRESIDENT
• The second out           = ⭐  Vice-President
• Middle players           = ranked by finish order
• The last player holding cards = 💀  THE PEASANT

BETWEEN GAMES  (Card Trade)
• The Peasant must give their BEST card to the President.
• The President gives ANY card of their choosing back to the Peasant.
• The Peasant then starts the new game.

SPECIAL RULES
• Demo Mode: The first game can be played as a tutorial round.
• AI players play automatically at Easy / Medium / Hard difficulty.
  – Easy:   Random valid plays; passes frequently.
  – Medium: Greedy (always plays lowest valid combo).
  – Hard:   Strategic (preserves high cards, plays aggressively near win).

SOCIAL RULES
• Players may join or leave between deals.
• If the President leaves, they may appoint any player except the Peasant
  as the new President.
• The Peasant may not leave until another player becomes the new Peasant,
  or the group agrees to restart or end the session.
"""


class RulesScreen(tk.Frame):

    def __init__(self, parent, on_back: Callable):
        super().__init__(parent, bg=C["bg"])
        self.on_back = on_back
        self._build()

    def _build(self):
        make_button(self, "← Back", self.on_back,
                    color=C["btn_neutral"],
                    font=F["small"], padx=10, pady=4).pack(anchor="w", padx=10, pady=10)

        frame = tk.Frame(self, bg=C["panel"], padx=20, pady=16)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        txt = tk.Text(frame, bg=C["panel"], fg=C["text"],
                      font=("Courier New", 11), wrap="word",
                      relief="flat", state="normal",
                      selectbackground=C["bg"])
        scr = ttk.Scrollbar(frame, command=txt.yview)
        txt.configure(yscrollcommand=scr.set)
        scr.pack(side="right", fill="y")
        txt.pack(fill="both", expand=True)
        txt.insert("end", RULES_TEXT)
        txt.configure(state="disabled")
