"""
ai_engine.py
============
AI decision engine for the President card game.

Three difficulty levels:
  Easy   – plays randomly from valid moves; passes often
  Medium – greedy: always plays the lowest valid combination
  Hard   – strategic: conserves high cards, plays multiples aggressively,
            uses Q♥ only when necessary, tries to empty hand fast

All AI logic is pure (no GUI, no state mutation).
The engine receives a read-only snapshot and returns the chosen play
(list of Cards) or None to pass.
"""

from __future__ import annotations
import random
import itertools
from typing import List, Optional, Tuple, Dict
from cards import Card, Suit, RANK_ORDER


# ── Helpers ───────────────────────────────────────────────────────────────────

def _group_by_rank(hand: List[Card]) -> Dict[int, List[Card]]:
    """Return {rank: [cards]} sorted cards within each group."""
    groups: Dict[int, List[Card]] = {}
    for c in hand:
        groups.setdefault(c.rank, []).append(c)
    for g in groups.values():
        g.sort()
    return groups


def _all_valid_combos(hand: List[Card], required_count: int,
                      top_card: Optional[Card]) -> List[List[Card]]:
    """
    Return every combination of `required_count` same-rank cards from hand
    that is a legal play given the current table state.
    """
    results: List[List[Card]] = []
    groups = _group_by_rank(hand)

    for rank, cards in groups.items():
        if len(cards) < required_count:
            continue
        for combo in itertools.combinations(cards, required_count):
            combo_list = list(combo)
            played_high = max(combo_list, key=lambda c: c.sort_key())
            if _is_valid_play(played_high, top_card):
                results.append(combo_list)

    return results


def _is_valid_play(played_high: Card, top_card: Optional[Card]) -> bool:
    """Check if a card strictly beats the current top. Q♥ always valid."""
    if played_high.is_queen_of_hearts:
        return True
    if top_card is None:
        return True
    return played_high > top_card


def _combo_strength(combo: List[Card]) -> float:
    """Higher = stronger combo (used for sorting)."""
    return max(c.sort_key()[0] * 10 + c.sort_key()[1] for c in combo)


# ── Public AI entry point ─────────────────────────────────────────────────────

def choose_play(
    hand:             List[Card],
    required_count:   int,
    top_card:         Optional[Card],
    difficulty:       str,
    cards_in_hands:   List[int],   # card counts for all players (Hard AI awareness)
    my_position:      int,         # seat index of this AI player
) -> Optional[List[Card]]:
    """
    Main AI decision function.
    Returns a list of cards to play, or None to pass.
    """
    starting_round = (top_card is None)

    if difficulty == "Easy":
        return _ai_easy(hand, required_count, top_card, starting_round)
    elif difficulty == "Medium":
        return _ai_medium(hand, required_count, top_card, starting_round)
    else:  # "Hard"
        return _ai_hard(hand, required_count, top_card,
                        starting_round, cards_in_hands, my_position)


# ── Easy AI ───────────────────────────────────────────────────────────────────

def _ai_easy(hand, req, top_card, starting_round) -> Optional[List[Card]]:
    """
    Easy: randomly plays any valid single card.
    When starting a round always plays a single.
    Passes 30% of the time even when it could play.
    """
    if starting_round:
        return [random.choice(hand)]

    candidates = _all_valid_combos(hand, req, top_card)
    if not candidates:
        return None
    # 30 % chance to pass even when able to play (makes Easy beatable)
    if random.random() < 0.30:
        return None
    return random.choice(candidates)


# ── Medium AI ─────────────────────────────────────────────────────────────────

def _ai_medium(hand, req, top_card, starting_round) -> Optional[List[Card]]:
    """
    Medium: greedy lowest-valid-combination strategy.
    When starting a round, prefers to play multiples to dump cards faster.
    Saves Q♥ as a last resort.
    """
    QH = Card(12, Suit.HEARTS)

    if starting_round:
        return _medium_start_play(hand)

    # Collect valid combos, exclude Q♥ initially
    candidates = [c for c in _all_valid_combos(hand, req, top_card)
                  if not any(card.is_queen_of_hearts for card in c)]

    if candidates:
        # Play the weakest valid combo (preserve strong cards)
        candidates.sort(key=_combo_strength)
        return candidates[0]

    # No normal play – try Q♥ if in hand and count matches
    if QH in hand and req == 1:
        return [QH]

    return None  # pass


def _medium_start_play(hand: List[Card]) -> List[Card]:
    """When starting a round, prefer playing the largest group of lowest rank."""
    groups = _group_by_rank(hand)
    # Sort by rank value ascending, then prefer larger groups
    ranked = sorted(groups.items(), key=lambda kv: (RANK_ORDER.index(kv[0]), -len(kv[1])))
    rank, cards = ranked[0]
    # Play the whole group (doubles/triples) or just one if large group
    count = min(len(cards), 3)   # cap at triples when starting
    return sorted(cards)[:count]


# ── Hard AI ───────────────────────────────────────────────────────────────────

def _ai_hard(hand, req, top_card, starting_round,
             cards_in_hands, my_position) -> Optional[List[Card]]:
    """
    Hard: strategic AI with several heuristics:

    1. Finishing move – if playing these cards empties the hand, always do it.
    2. When starting a round, choose the move that best clears low cards
       while considering multiples.
    3. When following, play the lowest combo that beats top_card,
       but AVOID wasting high-value cards unless necessary.
    4. Save Q♥ for situations where no other card can win.
    5. If an opponent has ≤3 cards, play aggressively to end the round.
    6. Strategically play 7s to end the current round and start fresh,
       useful when holding many low-value cards.
    """
    QH = Card(12, Suit.HEARTS)

    # ── Starting a fresh round ──
    if starting_round:
        return _hard_start_play(hand, cards_in_hands, my_position)

    # ── Collect all valid combos (excluding Q♥ for now) ──
    candidates = [c for c in _all_valid_combos(hand, req, top_card)
                  if not any(card.is_queen_of_hearts for card in c)]

    if not candidates:
        # Try Q♥ as trump if no other legal play
        if QH in hand and req == 1:
            return [QH]
        return None  # pass

    # ── Sort candidates: weakest first ──
    candidates.sort(key=_combo_strength)

    # ── Finishing move: if any combo empties our hand, take it ──
    for combo in candidates:
        if len(hand) - len(combo) == 0:
            return combo

    # ── If an opponent is close to winning (≤3 cards), be aggressive ──
    opponent_counts = [n for i, n in enumerate(cards_in_hands) if i != my_position and n > 0]
    someone_near_win = any(n <= 3 for n in opponent_counts)

    if someone_near_win:
        # Play strongest possible to keep control of the round
        return candidates[-1]

    # ── Prefer playing 7s to end round and start fresh with lower cards ──
    # Only worthwhile if we hold several low-rank cards that are stuck
    sevens_combos = [c for c in candidates if all(card.is_seven for card in c)]
    if sevens_combos:
        low_card_count = sum(1 for c in hand
                             if not c.is_seven and RANK_ORDER.index(c.rank) < RANK_ORDER.index(7))
        if low_card_count >= 2:
            return sevens_combos[0]

    # ── Normal: play weakest valid combo ──
    return candidates[0]


def _hard_start_play(hand: List[Card], cards_in_hands: List[int],
                     my_position: int) -> List[Card]:
    """
    Hard AI starting a round.
    Strategy:
      - If we can empty hand with a single play, do it.
      - Play the largest complete group of low-rank cards to dump many cards.
      - Avoid leading with very high cards unless the hand is small.
    """
    QH = Card(12, Suit.HEARTS)
    groups = _group_by_rank(hand)

    # Check for finishing play (entire hand is one rank)
    for rank, cards in groups.items():
        if len(cards) == len(hand):
            return cards  # play everything and finish!

    # Sort groups: low rank first, then larger groups preferred
    ranked = sorted(groups.items(),
                    key=lambda kv: (RANK_ORDER.index(kv[0]), -len(kv[1])))

    # Skip Q♥ when starting unless it's the only card
    playable = [(r, c) for r, c in ranked if not (r == 12 and Suit.HEARTS in [x.suit for x in c])]
    if not playable:
        playable = ranked  # fallback: play Q♥

    rank, cards = playable[0]
    # Play full group (to clear as many cards as possible)
    return list(cards)
