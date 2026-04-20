"""
President Card Game
===================
A full implementation of the "President" card game with a modern Tkinter GUI.

HOW TO RUN:
    python president_card_game.py

REQUIREMENTS:
    Python 3.8+  (tkinter is included in the standard library)
    Pillow (optional, for card images):  pip install pillow
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import random
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import IntEnum
import itertools


# ─────────────────────────────────────────────
# 1. DOMAIN: Cards, Deck, Hand
# ─────────────────────────────────────────────

class Suit(IntEnum):
    CLUBS    = 0   # lowest
    SPADES   = 1
    DIAMONDS = 2
    HEARTS   = 3   # highest

SUIT_SYMBOLS = {Suit.CLUBS: "♣", Suit.SPADES: "♠", Suit.DIAMONDS: "♦", Suit.HEARTS: "♥"}
SUIT_COLORS  = {Suit.CLUBS: "#1a1a2e", Suit.SPADES: "#1a1a2e",
                Suit.DIAMONDS: "#c0392b", Suit.HEARTS: "#c0392b"}

# Rank order: 3 lowest … Ace … 2 … Queen of Hearts (trump) is handled separately
RANK_ORDER = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 2]   # 11=J 12=Q 13=K 14=A
RANK_NAMES = {3:"3",4:"4",5:"5",6:"6",7:"7",8:"8",9:"9",10:"10",
              11:"J",12:"Q",13:"K",14:"A",2:"2"}


@dataclass(frozen=True)
class Card:
    rank: int   # 2-14  (11=J, 12=Q, 13=K, 14=A)
    suit: Suit

    def __post_init__(self):
        if self.rank not in RANK_ORDER:
            raise ValueError(f"Invalid rank {self.rank}")

    @property
    def is_queen_of_hearts(self) -> bool:
        return self.rank == 12 and self.suit == Suit.HEARTS

    @property
    def is_seven(self) -> bool:
        return self.rank == 7

    def sort_key(self) -> Tuple[int, int]:
        """Lower numbers = lower value card."""
        if self.is_queen_of_hearts:
            return (99, 99)          # absolute highest
        return (RANK_ORDER.index(self.rank), int(self.suit))

    def display_name(self) -> str:
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def __lt__(self, other: "Card") -> bool:
        return self.sort_key() < other.sort_key()

    def __le__(self, other: "Card") -> bool:
        return self.sort_key() <= other.sort_key()

    def __gt__(self, other: "Card") -> bool:
        return self.sort_key() > other.sort_key()

    def __ge__(self, other: "Card") -> bool:
        return self.sort_key() >= other.sort_key()


def make_deck(n_decks: int = 1) -> List[Card]:
    """Return a shuffled deck (no Jokers)."""
    single = [Card(rank, suit) for suit in Suit for rank in RANK_ORDER]
    deck = single * n_decks
    random.shuffle(deck)
    return deck


def deal_cards(deck: List[Card], n_players: int) -> List[List[Card]]:
    """Deal all cards as evenly as possible."""
    hands: List[List[Card]] = [[] for _ in range(n_players)]
    for i, card in enumerate(deck):
        hands[i % n_players].append(card)
    for hand in hands:
        hand.sort()
    return hands


# ─────────────────────────────────────────────
# 2. GAME LOGIC
# ─────────────────────────────────────────────

class GamePhase:
    SETUP        = "setup"
    PLAYING      = "playing"
    ROUND_END    = "round_end"
    GAME_OVER    = "game_over"
    CARD_TRADE   = "card_trade"


@dataclass
class Player:
    name: str
    hand: List[Card] = field(default_factory=list)
    finished_rank: Optional[int] = None   # 1=President, 2=Vice President, etc.
    is_human: bool = True

    def sort_hand(self):
        self.hand.sort()

    def remove_cards(self, cards: List[Card]):
        for c in cards:
            self.hand.remove(c)

    @property
    def has_cards(self) -> bool:
        return len(self.hand) > 0


class GameState:
    """All mutable game state lives here."""

    def __init__(self):
        self.players: List[Player] = []
        self.n_decks: int = 1
        self.phase: str = GamePhase.SETUP
        self.current_idx: int = 0           # whose turn
        self.table_pile: List[List[Card]] = []  # list of plays in this round
        self.active_players: List[int] = [] # indices still in this round
        self.finished_order: List[int] = [] # player indices by finish order
        self.demo_mode: bool = False
        self.game_number: int = 1
        self.required_count: int = 1        # singles / doubles / triples this round
        self.last_played_by: Optional[int] = None
        self.round_direction: str = "up"    # "up" or "down" (after a 7)
        self.log_messages: List[str] = []

    # ── helpers ──

    def log(self, msg: str):
        self.log_messages.append(msg)
        if len(self.log_messages) > 200:
            self.log_messages = self.log_messages[-200:]

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    @property
    def top_play(self) -> Optional[List[Card]]:
        return self.table_pile[-1] if self.table_pile else None

    @property
    def top_card(self) -> Optional[Card]:
        """Highest card in the current top play."""
        if not self.top_play:
            return None
        return max(self.top_play, key=lambda c: c.sort_key())

    def start_new_game(self):
        deck = make_deck(self.n_decks)
        hands = deal_cards(deck, len(self.players))
        for i, p in enumerate(self.players):
            p.hand = hands[i]
            p.finished_rank = None
        self.finished_order = []
        self.phase = GamePhase.PLAYING
        self._start_first_round()

    def _start_first_round(self):
        """Determine who goes first (holder of 3♣ or Peasant in later games)."""
        self.table_pile = []
        self.required_count = 1
        self.round_direction = "up"
        self.active_players = [i for i, p in enumerate(self.players) if p.has_cards]

        # Find starter
        three_clubs = Card(3, Suit.CLUBS)
        starter = None
        for i, p in enumerate(self.players):
            if three_clubs in p.hand:
                starter = i
                break

        # In subsequent games the peasant starts
        if self.game_number > 1:
            peasant_idx = self._peasant_idx()
            if peasant_idx is not None:
                starter = peasant_idx

        self.current_idx = starter if starter is not None else self.active_players[0]
        self.last_played_by = None
        self.log(f"--- Game {self.game_number} Round starts. {self.players[self.current_idx].name} goes first ---")

    def _president_idx(self) -> Optional[int]:
        return self.finished_order[0] if self.finished_order else None

    def _peasant_idx(self) -> Optional[int]:
        return self.finished_order[-1] if len(self.finished_order) == len(self.players) else None

    # ── play validation ──

    def can_play(self, cards: List[Card]) -> Tuple[bool, str]:
        """Return (valid, reason). Cards must all be same rank, correct count, higher value."""
        if not cards:
            return False, "No cards selected."

        # All same rank
        ranks = {c.rank for c in cards}
        if len(ranks) > 1 and not any(c.is_queen_of_hearts for c in cards):
            return False, "All cards must be the same rank (or Queen of Hearts)."

        count = len(cards)

        if self.top_play is None:
            # Starting a round — any single or multiple is fine
            self.required_count = count
            return True, ""

        # Must match required count
        if count != self.required_count:
            return False, f"Must play exactly {self.required_count} card(s)."

        top = self.top_card

        # Queen of Hearts always wins
        if any(c.is_queen_of_hearts for c in cards):
            return True, ""

        # Must be strictly higher
        played_high = max(cards, key=lambda c: c.sort_key())
        if self.round_direction == "up":
            if played_high <= top:
                return False, "Must play a higher card."
        else:  # after a 7 was played — next player plays lower
            if played_high >= top:
                return False, "Must play a lower card (7 rule active)."

        # Special: can't play remaining 6s if 6♥ already played (example from rules)
        # In general: if all copies of a rank at that count have been "used up" in a way
        # that the remaining combination isn't strictly higher, it's blocked naturally
        # by the sort_key comparison above. No special case needed.

        return True, ""

    def play_cards(self, cards: List[Card]) -> str:
        """Execute a play. Returns a status message."""
        valid, reason = self.can_play(cards)
        if not valid:
            return reason

        player = self.current_player
        player.remove_cards(cards)
        self.table_pile.append(list(cards))
        self.last_played_by = self.current_idx
        played_str = " ".join(c.display_name() for c in cards)
        self.log(f"{player.name} plays: {played_str}")

        # Check Queen of Hearts → instant round win
        if any(c.is_queen_of_hearts for c in cards):
            self.log(f"♛ Queen of Hearts! {player.name} wins the round instantly!")
            self._end_round()
            return "queen_of_hearts"

        # Check if player finished
        if not player.has_cards:
            rank = len(self.finished_order) + 1
            player.finished_rank = rank
            self.finished_order.append(self.current_idx)
            titles = {1:"🏆 The President!", 2:"Vice President", 3:"Senator"}
            title = titles.get(rank, f"#{rank}")
            self.log(f"🎉 {player.name} is out! — {title}")
            self.active_players.remove(self.current_idx)

        # Check 7 rule: flip direction for NEXT player
        if any(c.is_seven for c in cards):
            self.round_direction = "down"
            self.log("7 played! Next player must play a lower card.")

        # Check if play is unbeatable (2 or Q♥ exhausts the round)
        top = max(cards, key=lambda c: c.sort_key())
        if top.rank == 2 or top.is_queen_of_hearts:
            self._end_round()
            return "unbeatable"

        # Check if game is over
        if self._check_game_over():
            return "game_over"

        # Advance turn
        self._advance_turn()
        return "ok"

    def pass_turn(self) -> str:
        player = self.current_player
        self.log(f"{player.name} passes.")
        if self.current_idx in self.active_players:
            self.active_players.remove(self.current_idx)

        # If only the last player who played is left (everyone else passed) → end round
        remaining = [i for i in self.active_players]
        if len(remaining) == 0 or (len(remaining) == 1 and remaining[0] == self.last_played_by):
            self._end_round()
            return "round_end"

        self._advance_turn()
        return "ok"

    def _advance_turn(self):
        """Move to next active player."""
        if not self.active_players:
            self._end_round()
            return
        # Cycle through active players
        all_indices = sorted(self.active_players)
        current_pos = None
        for pos, idx in enumerate(all_indices):
            if idx == self.current_idx:
                current_pos = pos
                break
        if current_pos is None:
            # current player already removed (finished/passed)
            current_pos = -1
        next_pos = (current_pos + 1) % len(all_indices)
        self.current_idx = all_indices[next_pos]

    def _end_round(self):
        winner_idx = self.last_played_by
        if winner_idx is not None:
            winner = self.players[winner_idx]
            self.log(f"Round won by {winner.name}. Cards discarded.")
            self.table_pile = []
            self.required_count = 1
            self.round_direction = "up"

            # Remaining players for next round = those who still have cards
            self.active_players = [i for i, p in enumerate(self.players) if p.has_cards]

            if self._check_game_over():
                return

            # Winner starts next round
            self.current_idx = winner_idx
            if winner_idx not in self.active_players:
                # winner finished — find next active
                if self.active_players:
                    self.current_idx = self.active_players[0]
            self.last_played_by = None
            self.log(f"{self.players[self.current_idx].name} starts the next round.")

    def _check_game_over(self) -> bool:
        """Game ends when only one player has cards left."""
        players_with_cards = [p for p in self.players if p.has_cards]
        if len(players_with_cards) <= 1:
            # Record last player(s) as finished
            for i, p in enumerate(self.players):
                if p.has_cards and i not in self.finished_order:
                    p.finished_rank = len(self.finished_order) + 1
                    self.finished_order.append(i)
                    self.log(f"💀 {p.name} is the Peasant!")
            self.phase = GamePhase.GAME_OVER
            return True
        return False

    def do_card_trade(self, president_gives: Card, peasant_gives: Card):
        """President gives worst card, Peasant gives best card."""
        pres_idx = self._president_idx()
        peasant_idx = self._peasant_idx()
        if pres_idx is None or peasant_idx is None:
            return
        pres = self.players[pres_idx]
        peasant = self.players[peasant_idx]
        pres.hand.remove(president_gives)
        peasant.hand.append(president_gives)
        peasant.hand.remove(peasant_gives)
        pres.hand.append(peasant_gives)
        pres.sort_hand()
        peasant.sort_hand()
        self.log(f"Trade: {pres.name} gave {president_gives.display_name()} to {peasant.name}")
        self.log(f"Trade: {peasant.name} gave {peasant_gives.display_name()} to {pres.name}")


# ─────────────────────────────────────────────
# 3. GUI
# ─────────────────────────────────────────────

COLORS = {
    "bg":          "#0d1b2a",   # dark navy
    "card_bg":     "#f0e6d3",   # warm parchment
    "card_sel":    "#ffe066",   # golden selected
    "button":      "#1e6091",   # blue
    "button_hover":"#2980b9",
    "accent":      "#e74c3c",   # red accent
    "green":       "#27ae60",
    "text":        "#ecf0f1",
    "text_dark":   "#2c3e50",
    "panel":       "#16213e",
    "table":       "#145a32",   # green felt
    "border":      "#2c3e50",
}

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_LARGE  = ("Segoe UI", 14, "bold")
FONT_MEDIUM = ("Segoe UI", 11)
FONT_SMALL  = ("Segoe UI", 9)
FONT_CARD   = ("Segoe UI", 13, "bold")
FONT_CARD_S = ("Segoe UI", 10, "bold")


class CardWidget(tk.Canvas):
    """A clickable card widget drawn entirely with Canvas primitives."""

    W, H = 60, 84   # card dimensions

    def __init__(self, parent, card: Card, on_click=None, selected=False, **kwargs):
        super().__init__(parent, width=self.W, height=self.H,
                         bg=COLORS["panel"], highlightthickness=0, **kwargs)
        self.card = card
        self.on_click = on_click
        self._selected = selected
        self._draw()
        self.bind("<Button-1>", self._clicked)
        self.bind("<Enter>", lambda e: self._set_hover(True))
        self.bind("<Leave>", lambda e: self._set_hover(False))
        self._hover = False

    def _draw(self):
        self.delete("all")
        bg = COLORS["card_sel"] if self._selected else COLORS["card_bg"]
        r = 6
        W, H = self.W, self.H
        # Rounded rect
        self.create_arc(0, 0, r*2, r*2, start=90, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, 0, W, r*2, start=0, extent=90, fill=bg, outline=bg)
        self.create_arc(0, H-r*2, r*2, H, start=180, extent=90, fill=bg, outline=bg)
        self.create_arc(W-r*2, H-r*2, W, H, start=270, extent=90, fill=bg, outline=bg)
        self.create_rectangle(r, 0, W-r, H, fill=bg, outline=bg)
        self.create_rectangle(0, r, W, H-r, fill=bg, outline=bg)
        # Border
        border_color = "#f39c12" if self._selected else "#aaa"
        self.create_rectangle(2, 2, W-2, H-2, outline=border_color,
                               width=2 if self._selected else 1)
        # Text
        color = SUIT_COLORS[self.card.suit]
        rank  = RANK_NAMES[self.card.rank]
        sym   = SUIT_SYMBOLS[self.card.suit]
        self.create_text(6, 4, anchor="nw", text=rank,
                         font=FONT_CARD_S, fill=color)
        self.create_text(6, 15, anchor="nw", text=sym,
                         font=FONT_CARD_S, fill=color)
        self.create_text(W//2, H//2, text=f"{rank}\n{sym}",
                         font=FONT_CARD, fill=color, justify="center")
        # QH crown marker
        if self.card.is_queen_of_hearts:
            self.create_text(W//2, H-8, text="♛", font=("Segoe UI", 8), fill="#e74c3c")

    def set_selected(self, v: bool):
        self._selected = v
        self._draw()

    def _set_hover(self, v: bool):
        self._hover = v
        self._draw()
        if v and not self._selected:
            self.configure(cursor="hand2")

    def _clicked(self, _event):
        if self.on_click:
            self.on_click(self.card)


def styled_button(parent, text, command, color=None, **kwargs) -> tk.Button:
    c = color or COLORS["button"]
    btn = tk.Button(parent, text=text, command=command,
                    bg=c, fg="white", font=FONT_MEDIUM,
                    relief="flat", padx=12, pady=6,
                    activebackground=COLORS["button_hover"],
                    activeforeground="white",
                    cursor="hand2", **kwargs)
    return btn


class SetupScreen(tk.Frame):
    """Player setup screen."""

    def __init__(self, parent, on_start):
        super().__init__(parent, bg=COLORS["bg"])
        self.on_start = on_start
        self.player_entries: List[tk.StringVar] = []
        self._build()

    def _build(self):
        tk.Label(self, text="♠ President ♥", font=("Segoe UI", 32, "bold"),
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=(30, 5))
        tk.Label(self, text="The Classic Card Game",
                 font=FONT_MEDIUM, bg=COLORS["bg"], fg="#aaa").pack(pady=(0, 20))

        form = tk.Frame(self, bg=COLORS["panel"], padx=20, pady=20)
        form.pack(padx=40, pady=10, fill="x")

        # Number of decks
        tk.Label(form, text="Number of Decks (1–5):", font=FONT_MEDIUM,
                 bg=COLORS["panel"], fg=COLORS["text"]).grid(row=0, column=0, sticky="w", pady=5)
        self.deck_var = tk.IntVar(value=1)
        deck_spin = tk.Spinbox(form, from_=1, to=5, textvariable=self.deck_var,
                               width=5, font=FONT_MEDIUM)
        deck_spin.grid(row=0, column=1, sticky="w", padx=10)

        # Demo mode
        self.demo_var = tk.BooleanVar(value=False)
        tk.Checkbutton(form, text="First game as Demo (explains rules)",
                       variable=self.demo_var, bg=COLORS["panel"],
                       fg=COLORS["text"], selectcolor=COLORS["bg"],
                       font=FONT_SMALL, activebackground=COLORS["panel"],
                       activeforeground=COLORS["text"]).grid(row=1, column=0,
                       columnspan=2, sticky="w", pady=5)

        # Players
        tk.Label(form, text="Players (4–10 recommended):", font=FONT_MEDIUM,
                 bg=COLORS["panel"], fg=COLORS["text"]).grid(row=2, column=0,
                 sticky="w", pady=(15, 5))

        self.players_frame = tk.Frame(form, bg=COLORS["panel"])
        self.players_frame.grid(row=3, column=0, columnspan=2, sticky="ew")

        for i in range(4):
            self._add_player_row(f"Player {i+1}")

        btn_row = tk.Frame(form, bg=COLORS["panel"])
        btn_row.grid(row=4, column=0, columnspan=2, pady=10)
        styled_button(btn_row, "+ Add Player", self._add_player).pack(side="left", padx=5)
        styled_button(btn_row, "– Remove Player", self._remove_player,
                      color="#7f8c8d").pack(side="left", padx=5)

        styled_button(self, "▶  Start Game", self._start,
                      color=COLORS["green"], font=FONT_LARGE).pack(pady=20)

    def _add_player_row(self, default=""):
        i = len(self.player_entries)
        var = tk.StringVar(value=default)
        self.player_entries.append(var)
        row = tk.Frame(self.players_frame, bg=COLORS["panel"])
        row.pack(fill="x", pady=2)
        tk.Label(row, text=f"P{i+1}:", width=3, bg=COLORS["panel"],
                 fg=COLORS["text"], font=FONT_SMALL).pack(side="left")
        tk.Entry(row, textvariable=var, font=FONT_MEDIUM, width=20).pack(side="left", padx=4)

    def _add_player(self):
        if len(self.player_entries) >= 12:
            messagebox.showinfo("Limit", "Maximum 12 players.")
            return
        self._add_player_row(f"Player {len(self.player_entries)+1}")

    def _remove_player(self):
        if len(self.player_entries) <= 2:
            messagebox.showinfo("Minimum", "Need at least 2 players.")
            return
        self.player_entries.pop()
        for widget in self.players_frame.winfo_children()[-1:]:
            widget.destroy()

    def _start(self):
        names = [v.get().strip() for v in self.player_entries if v.get().strip()]
        if len(names) < 2:
            messagebox.showerror("Error", "Enter at least 2 player names.")
            return
        if len(set(names)) != len(names):
            messagebox.showerror("Error", "Player names must be unique.")
            return
        self.on_start(names, self.deck_var.get(), self.demo_var.get())


class GameScreen(tk.Frame):
    """Main game screen."""

    def __init__(self, parent, state: GameState, on_menu):
        super().__init__(parent, bg=COLORS["bg"])
        self.state = state
        self.on_menu = on_menu
        self.selected_cards: List[Card] = []
        self.card_widgets: dict[Card, CardWidget] = {}
        self._build()
        self.refresh()

    def _build(self):
        # Top bar
        top = tk.Frame(self, bg=COLORS["panel"], pady=6)
        top.pack(fill="x")
        tk.Label(top, text="♠ President ♥", font=FONT_LARGE,
                 bg=COLORS["panel"], fg=COLORS["text"]).pack(side="left", padx=15)
        self.status_lbl = tk.Label(top, text="", font=FONT_MEDIUM,
                                    bg=COLORS["panel"], fg="#f1c40f")
        self.status_lbl.pack(side="left", padx=20)
        styled_button(top, "☰ Menu", self.on_menu,
                      color="#7f8c8d", font=FONT_SMALL).pack(side="right", padx=10)

        # Main area (table + players)
        main = tk.Frame(self, bg=COLORS["bg"])
        main.pack(fill="both", expand=True)

        # Left: other players
        self.players_frame = tk.Frame(main, bg=COLORS["panel"], width=160)
        self.players_frame.pack(side="left", fill="y", padx=5, pady=5)
        self.players_frame.pack_propagate(False)
        tk.Label(self.players_frame, text="Players", font=FONT_MEDIUM,
                 bg=COLORS["panel"], fg=COLORS["text"]).pack(pady=(8,4))
        self.player_labels: List[tk.Label] = []

        # Center: table
        center = tk.Frame(main, bg=COLORS["bg"])
        center.pack(side="left", fill="both", expand=True)

        # Table (green felt)
        table_frame = tk.Frame(center, bg=COLORS["table"], padx=10, pady=10)
        table_frame.pack(fill="x", padx=10, pady=(5, 0))
        tk.Label(table_frame, text="Table", font=FONT_SMALL,
                 bg=COLORS["table"], fg="#aaffaa").pack(anchor="w")
        self.table_display = tk.Frame(table_frame, bg=COLORS["table"], height=100)
        self.table_display.pack(fill="x", pady=5)
        self.table_info = tk.Label(table_frame, text="", font=FONT_SMALL,
                                    bg=COLORS["table"], fg="#ccffcc")
        self.table_info.pack()

        # Action buttons
        btn_frame = tk.Frame(center, bg=COLORS["bg"])
        btn_frame.pack(pady=8)
        self.play_btn = styled_button(btn_frame, "▶ Play Selected",
                                       self._play, color=COLORS["green"])
        self.play_btn.pack(side="left", padx=6)
        self.pass_btn = styled_button(btn_frame, "⏭ Pass Turn",
                                       self._pass, color="#7f8c8d")
        self.pass_btn.pack(side="left", padx=6)
        self.clear_btn = styled_button(btn_frame, "✕ Clear",
                                        self._clear_selection, color="#7f8c8d")
        self.clear_btn.pack(side="left", padx=6)

        # Human hand
        hand_title = tk.Frame(center, bg=COLORS["bg"])
        hand_title.pack(fill="x", padx=10)
        self.hand_title_lbl = tk.Label(hand_title, text="Your Hand",
                                        font=FONT_MEDIUM, bg=COLORS["bg"],
                                        fg=COLORS["text"])
        self.hand_title_lbl.pack(side="left")
        self.hand_count_lbl = tk.Label(hand_title, text="",
                                        font=FONT_SMALL, bg=COLORS["bg"], fg="#aaa")
        self.hand_count_lbl.pack(side="left", padx=8)

        self.hand_scroll_frame = tk.Frame(center, bg=COLORS["bg"])
        self.hand_scroll_frame.pack(fill="x", padx=10, pady=(4, 0))

        self.hand_canvas = tk.Canvas(self.hand_scroll_frame, bg=COLORS["bg"],
                                      height=100, highlightthickness=0)
        hscroll = ttk.Scrollbar(self.hand_scroll_frame, orient="horizontal",
                                 command=self.hand_canvas.xview)
        self.hand_canvas.configure(xscrollcommand=hscroll.set)
        hscroll.pack(side="bottom", fill="x")
        self.hand_canvas.pack(fill="both", expand=True)
        self.hand_inner = tk.Frame(self.hand_canvas, bg=COLORS["bg"])
        self.hand_canvas.create_window(0, 0, anchor="nw", window=self.hand_inner)
        self.hand_inner.bind("<Configure>",
                              lambda e: self.hand_canvas.configure(
                                  scrollregion=self.hand_canvas.bbox("all")))

        # Right: log
        right = tk.Frame(main, bg=COLORS["panel"], width=200)
        right.pack(side="right", fill="y", padx=5, pady=5)
        right.pack_propagate(False)
        tk.Label(right, text="Game Log", font=FONT_MEDIUM,
                 bg=COLORS["panel"], fg=COLORS["text"]).pack(pady=(8, 4))
        self.log_text = tk.Text(right, bg=COLORS["bg"], fg="#aaffaa",
                                 font=("Courier New", 8), wrap="word",
                                 state="disabled", relief="flat")
        log_scroll = ttk.Scrollbar(right, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log_text.pack(fill="both", expand=True, padx=4, pady=4)

    # ── refresh ──

    def refresh(self):
        self._refresh_players()
        self._refresh_table()
        self._refresh_hand()
        self._refresh_status()
        self._refresh_log()
        self._refresh_buttons()

    def _refresh_players(self):
        for w in self.players_frame.winfo_children()[1:]:
            w.destroy()

        s = self.state
        for i, p in enumerate(s.players):
            is_current = (i == s.current_idx)
            finished = p.finished_rank is not None
            bg = COLORS["panel"]
            fg = COLORS["text"]
            prefix = ""
            if is_current:
                bg = "#1e3a5f"
                prefix = "▶ "
            if finished:
                fg = "#f39c12"
                rank = p.finished_rank
                titles = {1:"👑", 2:"⭐", len(s.players):"💀"}
                prefix = titles.get(rank, f"#{rank}") + " "

            frame = tk.Frame(self.players_frame, bg=bg, pady=2)
            frame.pack(fill="x", padx=4, pady=1)
            name_text = f"{prefix}{p.name}"
            tk.Label(frame, text=name_text, font=FONT_SMALL,
                     bg=bg, fg=fg, anchor="w").pack(side="left", padx=6)
            if not finished:
                tk.Label(frame, text=f"[{len(p.hand)}]", font=FONT_SMALL,
                         bg=bg, fg="#7f8c8d").pack(side="right", padx=4)

    def _refresh_table(self):
        for w in self.table_display.winfo_children():
            w.destroy()

        s = self.state
        if not s.table_pile:
            tk.Label(self.table_display, text="— empty table —",
                     bg=COLORS["table"], fg="#666", font=FONT_MEDIUM).pack(pady=20)
            self.table_info.config(text="")
            return

        # Show last 3 plays
        plays = s.table_pile[-3:]
        for play in plays:
            pf = tk.Frame(self.table_display, bg=COLORS["table"])
            pf.pack(side="left", padx=4)
            for c in sorted(play):
                cw = CardWidget(pf, c)
                cw.pack(side="left", padx=1)

        info_parts = [f"Required: {s.required_count} card(s)"]
        if s.round_direction == "down":
            info_parts.append("↓ Play LOWER (7 active)")
        self.table_info.config(text="   ".join(info_parts))

    def _refresh_hand(self):
        for w in self.hand_inner.winfo_children():
            w.destroy()
        self.card_widgets.clear()

        s = self.state
        # Find human player (index 0 is always the human in this setup)
        human_idx = 0
        human = s.players[human_idx]
        is_your_turn = (s.current_idx == human_idx)

        self.hand_title_lbl.config(
            text=f"{human.name}'s Hand",
            fg="#f1c40f" if is_your_turn else COLORS["text"]
        )
        self.hand_count_lbl.config(text=f"({len(human.hand)} cards)")

        for card in human.hand:
            selected = card in self.selected_cards
            cw = CardWidget(self.hand_inner, card,
                            on_click=self._toggle_card if is_your_turn else None,
                            selected=selected)
            cw.pack(side="left", padx=2, pady=8)
            self.card_widgets[card] = cw

    def _refresh_status(self):
        s = self.state
        p = s.current_player
        if s.phase == GamePhase.GAME_OVER:
            president = s.players[s.finished_order[0]].name if s.finished_order else "?"
            self.status_lbl.config(text=f"🎉 Game Over! President: {president}")
        else:
            turn_text = f"Turn: {p.name}  (Game #{s.game_number})"
            self.status_lbl.config(text=turn_text)

    def _refresh_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.insert("end", "\n".join(self.state.log_messages[-80:]))
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _refresh_buttons(self):
        s = self.state
        is_human_turn = (s.current_idx == 0)
        state = "normal" if is_human_turn and s.phase == GamePhase.PLAYING else "disabled"
        self.play_btn.config(state=state)
        self.pass_btn.config(state=state)
        self.clear_btn.config(state=state)

    # ── interactions ──

    def _toggle_card(self, card: Card):
        if card in self.selected_cards:
            self.selected_cards.remove(card)
        else:
            self.selected_cards.append(card)
        self.card_widgets[card].set_selected(card in self.selected_cards)

    def _clear_selection(self):
        self.selected_cards.clear()
        self._refresh_hand()

    def _play(self):
        if not self.selected_cards:
            messagebox.showinfo("No selection", "Click cards in your hand to select them, then press Play.")
            return
        result = self.state.play_cards(list(self.selected_cards))
        self.selected_cards.clear()

        if result == "ok":
            # Check if AI players should auto-play
            self._maybe_ai_turns()
        elif result in ("queen_of_hearts", "unbeatable", "round_end"):
            self._maybe_ai_turns()
        elif result == "game_over":
            self.refresh()
            self._show_game_over()
            return
        else:
            messagebox.showwarning("Invalid Play", result)
        self.refresh()

    def _pass(self):
        result = self.state.pass_turn()
        self.selected_cards.clear()
        if result == "game_over":
            self.refresh()
            self._show_game_over()
            return
        self._maybe_ai_turns()
        self.refresh()

    def _maybe_ai_turns(self):
        """Auto-play for non-human players (simple AI)."""
        s = self.state
        MAX_ITER = 1000
        i = 0
        while s.phase == GamePhase.PLAYING and s.current_idx != 0 and i < MAX_ITER:
            i += 1
            player = s.current_player
            play = self._ai_choose(player)
            if play:
                result = s.play_cards(play)
                if result == "game_over":
                    return
            else:
                result = s.pass_turn()
                if result == "game_over":
                    return

    def _ai_choose(self, player: Player) -> Optional[List[Card]]:
        """Simple greedy AI: play the lowest valid combination."""
        s = self.state
        req = s.required_count

        if s.top_play is None:
            # Starting round: pick lowest single (or group if req changes)
            groups = self._group_by_rank(player.hand)
            for rank_cards in groups:
                if len(rank_cards) >= req:
                    combo = sorted(rank_cards)[:req]
                    return combo
            return None

        candidates = []
        groups = self._group_by_rank(player.hand)
        for rank_cards in groups:
            if len(rank_cards) >= req:
                combos = list(itertools.combinations(sorted(rank_cards), req))
                for combo in combos:
                    valid, _ = s.can_play(list(combo))
                    if valid:
                        candidates.append(list(combo))

        # Also consider Queen of Hearts (always valid if in hand)
        qh = Card(12, Suit.HEARTS)
        if qh in player.hand:
            # Only play QH if nothing else works
            if not candidates:
                return [qh]

        if not candidates:
            return None

        # Play the lowest valid combo
        candidates.sort(key=lambda combo: max(c.sort_key() for c in combo))
        return candidates[0]

    def _group_by_rank(self, hand: List[Card]) -> List[List[Card]]:
        groups = {}
        for c in hand:
            groups.setdefault(c.rank, []).append(c)
        return sorted(groups.values(), key=lambda g: min(c.sort_key() for c in g))

    def _show_game_over(self):
        s = self.state
        lines = ["Game Over!\n"]
        titles = {1:"👑 President", 2:"⭐ Vice President"}
        for rank_pos, idx in enumerate(s.finished_order, 1):
            p = s.players[idx]
            title = titles.get(rank_pos, f"#{rank_pos}")
            if rank_pos == len(s.players):
                title = "💀 Peasant"
            lines.append(f"{title}: {p.name}")

        result = messagebox.askquestion(
            "Game Over",
            "\n".join(lines) + "\n\nPlay another round?",
            icon="info"
        )
        if result == "yes":
            self._start_next_game()

    def _start_next_game(self):
        s = self.state
        s.game_number += 1
        pres_idx = s.finished_order[0]
        peasant_idx = s.finished_order[-1]

        # Card trade dialog
        pres = s.players[pres_idx]
        peasant = s.players[peasant_idx]

        # President must give their worst card; peasant gives their best
        # For human as president: let them choose
        if pres_idx == 0:
            TradeDialog(self, s, pres_idx, peasant_idx, self._complete_next_game)
        else:
            # Auto trade: president gives worst, peasant gives best
            pres_worst = sorted(pres.hand)[0]       # lowest
            peasant_best = sorted(peasant.hand)[-1]  # highest
            s.do_card_trade(pres_worst, peasant_best)
            self._complete_next_game()

    def _complete_next_game(self):
        self.state.start_new_game()
        self.selected_cards.clear()
        self.refresh()


class TradeDialog(tk.Toplevel):
    """President chooses which card to give Peasant, and sees Peasant's best card."""

    def __init__(self, parent, state: GameState, pres_idx: int, peasant_idx: int, on_done):
        super().__init__(parent)
        self.title("Card Trade — President's Choice")
        self.configure(bg=COLORS["bg"])
        self.resizable(False, False)
        self.grab_set()
        self.state = state
        self.pres_idx = pres_idx
        self.peasant_idx = peasant_idx
        self.on_done = on_done
        self.selected_give: Optional[Card] = None
        self._build()

    def _build(self):
        pres = self.state.players[self.pres_idx]
        peasant = self.state.players[self.peasant_idx]
        peasant_best = sorted(peasant.hand)[-1]

        tk.Label(self, text="Card Trade", font=FONT_LARGE,
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=10)
        tk.Label(self,
                 text=f"{peasant.name} (Peasant) gives you: {peasant_best.display_name()}\n"
                      f"You must give {peasant.name} one of your cards.\n"
                      f"Select the card you wish to give away:",
                 font=FONT_MEDIUM, bg=COLORS["bg"], fg=COLORS["text"],
                 justify="center").pack(pady=8)

        hand_frame = tk.Frame(self, bg=COLORS["bg"])
        hand_frame.pack(pady=8)
        self.card_widgets: dict[Card, CardWidget] = {}
        for card in pres.hand:
            cw = CardWidget(hand_frame, card, on_click=self._select)
            cw.pack(side="left", padx=3)
            self.card_widgets[card] = cw

        self.confirm_btn = styled_button(self, "Confirm Trade", self._confirm,
                                          color=COLORS["green"])
        self.confirm_btn.pack(pady=12)

    def _select(self, card: Card):
        self.selected_give = card
        for c, w in self.card_widgets.items():
            w.set_selected(c == card)

    def _confirm(self):
        if not self.selected_give:
            messagebox.showwarning("Select a card", "Please select a card to give.", parent=self)
            return
        peasant = self.state.players[self.peasant_idx]
        peasant_best = sorted(peasant.hand)[-1]
        self.state.do_card_trade(self.selected_give, peasant_best)
        self.destroy()
        self.on_done()


class RulesScreen(tk.Frame):
    """Display game rules."""

    RULES = """
PRESIDENT — Game Rules
══════════════════════

SETUP
• 4–10 players recommended (no hard limit).
• Choose 1–5 decks of standard cards (no Jokers).

CARD VALUES (lowest → highest)
• Suits: Clubs < Spades < Diamonds < Hearts
• Ranks: 3 < 4 < 5 … < K < A < 2
• Queen of Hearts (Q♥) is the absolute trump — beats everything, including 2♥.

HOW TO PLAY
1. Cards are shuffled and dealt evenly.
2. The player with 3♣ goes first and MUST play it.
3. Each player in turn plays a HIGHER card (or combination).
4. If you can't or choose not to play, PASS.
5. The round ends when no one can beat the top card.
   The player who placed the top card WINS the round.
6. Winner discards the round's cards and starts fresh.

7 RULE
• If a 7 is played, the NEXT player must play a LOWER card.
  The round continues downward until it can't.

MULTIPLES
• A player starting a round may play 2, 3, or more cards
  of the same rank (doubles, triples, etc.).
• All players must then match that count.
• Among same-rank multiples, the highest single card
  determines the winner (e.g., 6♥ beats 6♦+6♣).

FINISHING
• First to run out of cards = 🏆 THE PRESIDENT
• Last with cards = 💀 THE PEASANT

NEXT GAME
• The Peasant starts the new game (regardless of 3♣).
• The President takes the Peasant's best card and gives
  back any card of the President's choosing.

SPECIAL NOTES
• Queen of Hearts (Q♥) wins any round instantly.
• Players may join/leave between deals.
• If the President leaves, they may appoint anyone
  (except the Peasant) as the new President.
• The Peasant may not leave until another player
  becomes Peasant, or the group decides to restart.

"""

    def __init__(self, parent, on_back):
        super().__init__(parent, bg=COLORS["bg"])
        self.on_back = on_back
        self._build()

    def _build(self):
        styled_button(self, "← Back", self.on_back,
                      color="#7f8c8d").pack(anchor="w", padx=10, pady=10)
        frame = tk.Frame(self, bg=COLORS["panel"], padx=20, pady=20)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        text = tk.Text(frame, bg=COLORS["panel"], fg=COLORS["text"],
                       font=("Courier New", 11), wrap="word",
                       relief="flat", state="normal")
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        text.insert("end", self.RULES)
        text.configure(state="disabled")


# ─────────────────────────────────────────────
# 4. APPLICATION ROOT
# ─────────────────────────────────────────────

class App(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("President Card Game")
        self.configure(bg=COLORS["bg"])
        self.geometry("1100x700")
        self.minsize(900, 600)
        self._apply_theme()
        self.state: Optional[GameState] = None
        self._current_screen: Optional[tk.Widget] = None
        self.show_setup()

    def _apply_theme(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TScrollbar", background=COLORS["panel"],
                        troughcolor=COLORS["bg"], bordercolor=COLORS["bg"])

    def _switch(self, screen: tk.Widget):
        if self._current_screen:
            self._current_screen.destroy()
        self._current_screen = screen
        screen.pack(fill="both", expand=True)

    def show_setup(self):
        self._switch(SetupScreen(self, self._on_game_start))

    def _on_game_start(self, names: List[str], n_decks: int, demo: bool):
        self.state = GameState()
        self.state.n_decks = n_decks
        self.state.demo_mode = demo
        self.state.players = [Player(name=n) for n in names]
        self.state.start_new_game()
        if demo:
            messagebox.showinfo(
                "Demo Mode",
                "This is a demonstration game.\n\n"
                "You are Player 1 (human). All others are AI.\n"
                "Click cards in your hand to select them, then press ▶ Play.\n"
                "Press ⏭ Pass if you cannot play.\n\n"
                "The game log on the right tracks all moves.",
                parent=self
            )
        self._switch(GameScreen(self, self.state, self._show_menu))

    def _show_menu(self):
        menu = tk.Toplevel(self)
        menu.title("Menu")
        menu.configure(bg=COLORS["bg"])
        menu.geometry("300x220")
        menu.grab_set()
        tk.Label(menu, text="Game Menu", font=FONT_LARGE,
                 bg=COLORS["bg"], fg=COLORS["text"]).pack(pady=20)
        styled_button(menu, "📖 Rules", lambda: self._show_rules(menu),
                      color=COLORS["button"]).pack(pady=5, fill="x", padx=30)
        styled_button(menu, "🔄 New Game (Setup)", lambda: [menu.destroy(), self.show_setup()],
                      color="#7f8c8d").pack(pady=5, fill="x", padx=30)
        styled_button(menu, "✕ Close Menu", menu.destroy,
                      color="#7f8c8d").pack(pady=5, fill="x", padx=30)

    def _show_rules(self, parent=None):
        win = tk.Toplevel(parent or self)
        win.title("Rules")
        win.configure(bg=COLORS["bg"])
        win.geometry("700x600")
        RulesScreen(win, win.destroy).pack(fill="both", expand=True)


if __name__ == "__main__":
    App().mainloop()
