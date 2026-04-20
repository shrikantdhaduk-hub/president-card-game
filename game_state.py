"""
game_state.py
=============
All game logic: Player, GameState, validation, round/game lifecycle.
No GUI dependencies.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from cards import Card, Suit, make_deck, deal_cards


# ── Constants ──────────────────────────────────────────────────────────────────

class Phase:
    SETUP      = "setup"
    PLAYING    = "playing"
    GAME_OVER  = "game_over"


AI_DIFFICULTY_LABELS = ["Easy", "Medium", "Hard"]


# ── Player ────────────────────────────────────────────────────────────────────

@dataclass
class Player:
    name: str
    is_human:    bool = True
    difficulty:  str  = "Medium"   # "Easy" | "Medium" | "Hard"  (ignored for humans)
    hand:        List[Card] = field(default_factory=list)
    finish_rank: Optional[int] = None  # 1 = President, last = Peasant

    def sort_hand(self):
        self.hand.sort()

    def remove_cards(self, cards: List[Card]):
        for c in cards:
            self.hand.remove(c)

    @property
    def has_cards(self) -> bool:
        return bool(self.hand)

    @property
    def icon(self) -> str:
        return "👤" if self.is_human else "🤖"

    @property
    def difficulty_short(self) -> str:
        return "" if self.is_human else f"[{self.difficulty[0]}]"


# ── GameState ─────────────────────────────────────────────────────────────────

class GameState:
    """
    Single source of truth for all game data.
    The GUI reads this and calls its public methods to mutate it.
    """

    def __init__(self):
        self.players:        List[Player]       = []
        self.n_decks:        int                = 1
        self.phase:          str                = Phase.SETUP
        self.game_number:    int                = 1
        self.demo_mode:      bool               = False

        # Round state
        self.current_idx:    int                = 0
        self.table_pile:     List[List[Card]]   = []   # each entry = one play
        self.active_players: List[int]          = []   # still in this round
        self.finished_order: List[int]          = []   # by finish position
        self.required_count: int                = 1    # singles / doubles / triples
        self.last_played_by: Optional[int]      = None

        self.log_messages:   List[str]          = []

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def current_player(self) -> Player:
        return self.players[self.current_idx]

    @property
    def top_play(self) -> Optional[List[Card]]:
        return self.table_pile[-1] if self.table_pile else None

    @property
    def top_card(self) -> Optional[Card]:
        if not self.top_play:
            return None
        return max(self.top_play, key=lambda c: c.sort_key())

    def president_idx(self) -> Optional[int]:
        return self.finished_order[0] if self.finished_order else None

    def peasant_idx(self) -> Optional[int]:
        return self.finished_order[-1] if len(self.finished_order) == len(self.players) else None

    # ── Logging ───────────────────────────────────────────────────────────────

    def log(self, msg: str):
        self.log_messages.append(msg)
        if len(self.log_messages) > 300:
            self.log_messages = self.log_messages[-300:]

    # ── Game lifecycle ────────────────────────────────────────────────────────

    def start_new_game(self):
        deck  = make_deck(self.n_decks)
        hands = deal_cards(deck, len(self.players))
        for i, p in enumerate(self.players):
            p.hand        = hands[i]
            p.finish_rank = None
        self.finished_order = []
        self.phase          = Phase.PLAYING
        self._begin_first_round()

    def _begin_first_round(self):
        self.table_pile      = []
        self.required_count  = 1
        self.active_players  = [i for i, p in enumerate(self.players) if p.has_cards]
        self.last_played_by  = None

        # Game 1: holder of 3♣ starts; subsequent games: last peasant starts
        three_clubs = Card(3, Suit.CLUBS)
        starter = None
        if self.game_number == 1:
            for i, p in enumerate(self.players):
                if three_clubs in p.hand:
                    starter = i
                    break
        else:
            # The peasant of the previous game starts
            # (finished_order was reset above, so we stored peasant separately)
            if hasattr(self, "_last_peasant_idx"):
                starter = self._last_peasant_idx

        self.current_idx = starter if starter is not None else self.active_players[0]
        self.log(f"══ Game {self.game_number} ══  {self.players[self.current_idx].name} goes first")

    # ── Play validation ───────────────────────────────────────────────────────

    def can_play(self, cards: List[Card]) -> Tuple[bool, str]:
        """
        Validate a proposed play.
        Returns (True, "") on success or (False, reason) on failure.
        NOTE: This does NOT mutate state – call play_cards() to execute.
        """
        if not cards:
            return False, "No cards selected."

        # All cards must share the same rank
        ranks = {c.rank for c in cards}
        if len(ranks) > 1:
            return False, "All cards must share the same rank."

        count = len(cards)

        # No card on table yet — any count is valid.
        # (After a 7 reset, required_count is always 1 so the next player
        # is free to play any card or combination they choose.)
        if self.top_play is None:
            return True, ""

        # Must match the count established when this round started
        if count != self.required_count:
            return False, f"Must play exactly {self.required_count} card(s) this round."

        top = self.top_card
        played_high = max(cards, key=lambda c: c.sort_key())

        # Q♥ is absolute trump – always valid if count matches
        if played_high.is_queen_of_hearts:
            return True, ""

        # A 7 always triggers a reset regardless of the current top card
        if played_high.is_seven:
            return True, ""

        # Must be strictly higher than the current top card
        if played_high <= top:
            return False, "Must play a strictly higher card."

        return True, ""

    # ── Play execution ────────────────────────────────────────────────────────

    def play_cards(self, cards: List[Card]) -> str:
        """
        Execute a validated play.
        Returns a status string:
            "ok"             – normal play, turn advances
            "queen_wins"     – Q♥ played, round ends instantly
            "unbeatable"     – 2 or Q♥ placed; no one can beat it, round ends
            "round_end"      – normal round conclusion
            "game_over"      – final player(s) finished
            "<error msg>"    – validation failed (caller should show to user)
        """
        valid, reason = self.can_play(cards)
        if not valid:
            return reason

        player = self.current_player

        # Lock in the count for this round on the very first play
        # (table is empty = fresh start, whether new round or after a 7 reset).
        if self.top_play is None:
            self.required_count = len(cards)

        player.remove_cards(cards)
        self.table_pile.append(list(cards))
        self.last_played_by = self.current_idx

        played_str = " ".join(c.label() for c in cards)
        self.log(f"  {player.icon} {player.name}: {played_str}")

        # ── Queen of Hearts – instant round win ──
        played_high = max(cards, key=lambda c: c.sort_key())
        if played_high.is_queen_of_hearts:
            self.log(f"    ♛ Q♥ trump! {player.name} wins the round instantly!")
            self._mark_player_finished_if_empty(self.current_idx)
            if self._check_game_over():
                return "game_over"
            self._end_round()
            return "queen_wins"

        # ── Mark player finished if hand empty ──
        self._mark_player_finished_if_empty(self.current_idx)

        # ── 7 Rule ──────────────────────────────────────────────────────────
        # Playing a 7 clears the table and re-opens the round so the very
        # next player may play ANY card (even lower).  The round is NOT over
        # and there is NO winner yet — last_played_by stays untouched so that
        # if everyone passes after this point the player who played the 7
        # (or whoever played last before passing started) still wins.
        # After that one free play, normal rules resume (must beat the new card).
        # ─────────────────────────────────────────────────────────────────────
        if any(c.is_seven for c in cards):
            self.log(f"    7️⃣  7 played by {player.name}! Table resets — next player may play any card.")
            if self._check_game_over():
                return "game_over"
            # Clear the table and reset count: next player starts completely fresh —
            # any single card (or multiple) is valid, even a lower value.
            self.table_pile = []
            self.required_count = 1
            # Re-admit all players who still have cards into this round
            # (players who passed before the 7 get another chance).
            self.active_players = [i for i, p in enumerate(self.players) if p.has_cards]
            self._advance_turn()
            return "seven_played"

        # ── Check game over ──
        if self._check_game_over():
            return "game_over"

        # ── Check if play is unbeatable (rank 2) ──
        top = self.top_card
        if top and top.rank == 2:
            self._end_round()
            return "unbeatable"

        # ── Advance turn ──
        self._advance_turn()
        return "ok"

    def pass_turn(self) -> str:
        """Current player passes. Returns 'round_end', 'game_over', or 'ok'."""
        player = self.current_player
        self.log(f"  {player.icon} {player.name}: pass")

        if self.current_idx in self.active_players:
            self.active_players.remove(self.current_idx)

        # Round ends when only the last-player-who-played remains
        remaining = list(self.active_players)
        if not remaining or (len(remaining) == 1 and remaining[0] == self.last_played_by):
            if self._check_game_over():
                return "game_over"
            self._end_round()
            return "round_end"

        self._advance_turn()
        return "ok"

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _mark_player_finished_if_empty(self, idx: int):
        p = self.players[idx]
        if not p.has_cards and p.finish_rank is None:
            rank = len(self.finished_order) + 1
            p.finish_rank = rank
            self.finished_order.append(idx)
            titles = {1: "🏆 President!", 2: "⭐ Vice-President"}
            title = titles.get(rank, f"#{rank} place")
            self.log(f"    🎉 {p.name} finished – {title}")
            if idx in self.active_players:
                self.active_players.remove(idx)

    def _check_game_over(self) -> bool:
        """Game ends when ≤1 player still holds cards."""
        active_with_cards = [i for i, p in enumerate(self.players) if p.has_cards]
        if len(active_with_cards) <= 1:
            # Record remaining player as Peasant
            for i in active_with_cards:
                if self.players[i].finish_rank is None:
                    rank = len(self.finished_order) + 1
                    self.players[i].finish_rank = rank
                    self.finished_order.append(i)
                    self.log(f"    💀 {self.players[i].name} is the Peasant!")
            self.phase = Phase.GAME_OVER
            return True
        return False

    def _end_round(self):
        winner_idx = self.last_played_by
        if winner_idx is None:
            return
        winner = self.players[winner_idx]
        self.log(f"  ── Round won by {winner.name}. Cards cleared. ──")
        self.table_pile      = []
        self.required_count  = 1
        self.last_played_by  = None
        self.active_players  = [i for i, p in enumerate(self.players) if p.has_cards]

        # Winner starts next round (if still in game)
        starter = winner_idx if winner_idx in self.active_players else (
            self.active_players[0] if self.active_players else winner_idx
        )
        self.current_idx = starter
        if self.active_players:
            self.log(f"  {self.players[starter].name} starts next round.")

    def _advance_turn(self):
        """Move to the next active player in clockwise (seat-number) order.

        Works correctly even when current_idx has already been removed from
        active_players (player finished their hand or was removed after a 7-reset).
        """
        if not self.active_players:
            self._end_round()
            return
        seats = sorted(self.active_players)
        # Pick the first seat whose index is strictly greater than current_idx;
        # if none exists, wrap around to the lowest seat.
        next_seat = next((s for s in seats if s > self.current_idx), seats[0])
        self.current_idx = next_seat

    # ── Card trade between games ──────────────────────────────────────────────

    def start_next_game_with_trade(self):
        """
        Safe all-in-one transition to the next game.

        The correct order is critical:
          1. Capture president / peasant indices NOW (finished_order is intact)
          2. Increment game counter and store peasant for round-start logic
          3. start_new_game() — deals fresh hands to all players
          4. Swap cards on the NEW hands (president's hand is full again)

        Returns (pres_idx, peasant_idx, card_pres_gave, card_peasant_gave)
        so the GUI can show a trade summary.
        """
        pres_idx    = self.president_idx()
        peasant_idx = self.peasant_idx()

        # Fallback: if rankings are incomplete just start clean
        if pres_idx is None or peasant_idx is None:
            self.game_number += 1
            self.start_new_game()
            return None

        # Save before start_new_game() wipes finished_order
        self._last_peasant_idx = peasant_idx
        self.game_number += 1

        # Deal fresh cards — president's hand is now full
        self.start_new_game()

        # Trade on the new hands
        pres    = self.players[pres_idx]
        peasant = self.players[peasant_idx]
        pres_gives    = sorted(pres.hand)[0]       # worst (lowest) for president
        peasant_gives = sorted(peasant.hand)[-1]   # best (highest) for peasant

        pres.hand.remove(pres_gives)
        peasant.hand.append(pres_gives)
        peasant.hand.remove(peasant_gives)
        pres.hand.append(peasant_gives)
        pres.sort_hand()
        peasant.sort_hand()

        self.log(f"  💱 {peasant.name} gave {peasant_gives.label()} → {pres.name}")
        self.log(f"  💱 {pres.name} gave {pres_gives.label()} → {peasant.name}")

        return (pres_idx, peasant_idx, pres_gives, peasant_gives)

    # Keep old method for any code that still calls it (no-op guard)
    def execute_card_trade(self, *args, **kwargs):
        """Deprecated: use start_next_game_with_trade() instead."""
        pass

    def prepare_next_game(self):
        """Deprecated: use start_next_game_with_trade() instead."""
        pass
