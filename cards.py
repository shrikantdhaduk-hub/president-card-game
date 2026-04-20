"""
cards.py
========
Card domain: Suit, Card, deck factory, deal helper.
No GUI or game-logic dependencies.
"""

from __future__ import annotations
import random
from dataclasses import dataclass
from enum import IntEnum
from typing import List, Tuple


# ── Suit ──────────────────────────────────────────────────────────────────────

class Suit(IntEnum):
    CLUBS    = 0   # lowest
    SPADES   = 1
    DIAMONDS = 2
    HEARTS   = 3   # highest


SUIT_SYMBOL = {Suit.CLUBS: "♣", Suit.SPADES: "♠", Suit.DIAMONDS: "♦", Suit.HEARTS: "♥"}
SUIT_COLOR  = {Suit.CLUBS: "#1a1a2e", Suit.SPADES: "#1a1a2e",
               Suit.DIAMONDS: "#c0392b", Suit.HEARTS: "#c0392b"}

# Rank ordering: 3 is lowest, 2 is second-highest (Queen of Hearts is absolute trump)
RANK_ORDER = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 2]  # 11=J 12=Q 13=K 14=A
RANK_NAME  = {3:"3", 4:"4", 5:"5", 6:"6", 7:"7", 8:"8", 9:"9", 10:"10",
              11:"J", 12:"Q", 13:"K", 14:"A", 2:"2"}


# ── Card ──────────────────────────────────────────────────────────────────────

@dataclass(frozen=True, order=False)
class Card:
    rank: int   # values from RANK_ORDER
    suit: Suit

    def __post_init__(self):
        if self.rank not in RANK_ORDER:
            raise ValueError(f"Invalid rank {self.rank}")

    # ── special identity ──

    @property
    def is_queen_of_hearts(self) -> bool:
        """Absolute trump – beats everything."""
        return self.rank == 12 and self.suit == Suit.HEARTS

    @property
    def is_seven(self) -> bool:
        return self.rank == 7

    # ── ordering ──

    def sort_key(self) -> Tuple[int, int]:
        if self.is_queen_of_hearts:
            return (99, 99)
        return (RANK_ORDER.index(self.rank), int(self.suit))

    def __lt__(self, other: Card) -> bool:  return self.sort_key() <  other.sort_key()
    def __le__(self, other: Card) -> bool:  return self.sort_key() <= other.sort_key()
    def __gt__(self, other: Card) -> bool:  return self.sort_key() >  other.sort_key()
    def __ge__(self, other: Card) -> bool:  return self.sort_key() >= other.sort_key()
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Card): return NotImplemented
        return self.rank == other.rank and self.suit == other.suit
    def __hash__(self) -> int:
        return hash((self.rank, self.suit))

    # ── display ──

    def label(self) -> str:
        """Short display label, e.g. 'Q♥'."""
        return f"{RANK_NAME[self.rank]}{SUIT_SYMBOL[self.suit]}"

    def __repr__(self) -> str:
        return self.label()


# ── Deck helpers ──────────────────────────────────────────────────────────────

def make_deck(n_decks: int = 1) -> List[Card]:
    """Return a freshly shuffled deck (no Jokers)."""
    single = [Card(rank, suit) for suit in Suit for rank in RANK_ORDER]
    deck   = single * n_decks
    random.shuffle(deck)
    return deck


def deal_cards(deck: List[Card], n_players: int) -> List[List[Card]]:
    """Distribute all cards round-robin; each hand is sorted low→high."""
    hands: List[List[Card]] = [[] for _ in range(n_players)]
    for i, card in enumerate(deck):
        hands[i % n_players].append(card)
    for hand in hands:
        hand.sort()
    return hands
