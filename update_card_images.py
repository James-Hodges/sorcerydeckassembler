#!/usr/bin/env python3
"""
Point every card in master_cards.json at its image on card.cards.army.

card.cards.army publishes an index (processed_cards.json) of card names and
the slugs its image URLs are built from:

    https://card.cards.army/cards/{slug}.webp      full quality
    https://card.cards.army/cards/10/{slug}.webp   thumbnail

This script matches each card by name (exactly, then ignoring case and
punctuation), falls back to a slug built from the name when the index has
no entry, and rewrites the card's image_url. Re-run it after data_setup.py
refreshes the card list.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import requests

IMAGE_HOST = "https://card.cards.army"
INDEX_URL = f"{IMAGE_HOST}/processed_cards.json"
MASTER_CARDS_PATH = Path(__file__).parent / "card_data" / "master_cards.json"


def image_url(slug: str) -> str:
    return f"{IMAGE_HOST}/cards/{slug}.webp"


def fold_accents(name: str) -> str:
    """"Maelström" -> "Maelstrom"."""
    return unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()


def normalize(name: str) -> str:
    """Lowercase and drop everything but letters and digits."""
    return re.sub(r"[^a-z0-9]", "", fold_accents(name).lower())


def slugify(name: str) -> str:
    """Build a slug the way card.cards.army does: "A Midsummer Night's Dream" -> "a_midsummer_nights_dream"."""
    name = re.sub(r"['’]", "", fold_accents(name).lower())
    return re.sub(r"[^a-z0-9]+", "_", name).strip("_")


def image_exists(slug: str) -> bool:
    return requests.head(image_url(slug), timeout=15).status_code == 200


def main() -> int:
    index = requests.get(INDEX_URL, timeout=30).json()
    by_name = {entry["name"]: entry["slug"] for entry in index}
    by_normalized = {normalize(entry["name"]): entry["slug"] for entry in index}

    with open(MASTER_CARDS_PATH) as f:
        cards = json.load(f)

    unmatched = []
    for name, card in cards.items():
        slug = by_name.get(name) or by_normalized.get(normalize(name))
        # Some cards (e.g. the Arthurian Legends Foot Soldiers tokens) have
        # images on the CDN but are missing from its index.
        if not slug and image_exists(slugify(name)):
            slug = slugify(name)
        if slug:
            card["image_url"] = image_url(slug)
        else:
            card["image_url"] = None
            unmatched.append(name)

    with open(MASTER_CARDS_PATH, "w") as f:
        json.dump(cards, f, indent=4, ensure_ascii=False)
        f.write("\n")

    print(f"Matched {len(cards) - len(unmatched)} of {len(cards)} cards to {IMAGE_HOST}")
    if unmatched:
        print("No image found for:")
        for name in unmatched:
            print(f"  - {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
