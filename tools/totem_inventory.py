#!/usr/bin/env python3
"""List the shaman totem looks and write data/totems.tsv.

    python3 totem_inventory.py --cache <download dir>

Retail has no table of totem looks (a totem's model follows the shaman's race), so the sets are
listed here: the five races the 3.3.5a client already has (used as they are, effects and all),
and every retail set since, by retail CreatureDisplayInfo id. Each look gets a 3.3.5 display id,
a name and the Individual Progression tier that unlocks it. Display ids already in totems.tsv are
kept, so rerunning never moves a look a player may have chosen.
"""
import argparse
import os

from fetch import db2

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKS = os.path.join(HERE, "..", "data", "totems.tsv")
FIRST_DISPLAY = 96000
PREVIEW_BASE = 9501500          # ported looks: base + (display - 96000)
STOCK_PREVIEW_BASE = 9501900    # client's own looks: base + position in STOCK (append only)

ELEMENTS = ["fire", "earth", "water", "air"]

# Sets the 3.3.5a client already has: (name, tier, fire, earth, water, air) client display ids.
STOCK = [
    ("Tauren", 0, 4589, 4588, 4587, 4590),
    ("Orc", 0, 30758, 30757, 30759, 30756),
    ("Troll", 0, 30762, 30761, 30763, 30760),
    ("Dwarf", 0, 30754, 30753, 30755, 30736),
    ("Draenei", 0, 19074, 19073, 19075, 19071),
]

# Retail sets: (folder, name, tier, fire, earth, water, air) retail display ids. The tier is the
# Individual Progression state that unlocks the set (n = content n cleared).
RETAIL = [
    ("DarkIron", "Dark Iron", 1, 86433, 86435, 86434, 86432),                # Molten Core
    ("TaurenRemastered", "Tauren (Remastered)", 2, 4589, 4588, 4587, 4590),  # Onyxia's Lair
    ("Goblin", "Goblin", 3, 30783, 30782, 30784, 30781),                     # Blackwing Lair
    ("Zandalari", "Zandalari", 4, 84933, 84987, 84934, 84680),               # Zul'Gurub
    ("Vulpera", "Vulpera", 5, 94543, 94542, 94544, 94541),                   # Ahn'Qiraj War Effort
    ("Pandaren", "Pandaren", 6, 41670, 41669, 41671, 41668),                 # Temple of Ahn'Qiraj
    ("DarkShaman", "Dark Shaman", 7, 52510, 52509, 52511, 52512),            # Naxxramas
    ("Highmountain", "Highmountain", 8, 81444, 81443, 81442, 81441),         # the road to Outland
    ("Maghar", "Mag'har", 9, 86438, 86440, 86439, 86437),                    # Karazhan, Gruul, Magtheridon
    ("KulTiran", "Kul Tiran", 10, 90695, 90691, 90694, 90693),               # SSC and Tempest Keep
    ("DraenorClans", "Draenor Clans", 11, 54900, 54899, 54902, 54901),       # Hyjal and Black Temple
    ("Haranir", "Haranir", 12, 139805, 139666, 139667, 139669),              # Zul'Aman
    ("DraeneiRemastered", "Draenei (Remastered)", 13, 19074, 19073, 19075, 19071),  # Sunwell Plateau
    ("Earthen", "Earthen", 15, 118170, 118169, 118171, 118168),              # Ulduar
    ("Maelstrom", "Maelstrom", 17, 74647, 74649, 74648, 74650),              # Icecrown Citadel
]


def look_name(set_name, element):
    """"Tauren (Remastered)" + fire -> "Tauren Fire Totem (Remastered)"."""
    base, _, note = set_name.partition(" (")
    return "%s %s Totem%s" % (base, element.capitalize(), " (" + note if note else "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    args = ap.parse_args()
    cdi = db2(args.cache, "CreatureDisplayInfo")

    known = {}
    if os.path.exists(LOOKS):
        for line in open(LOOKS, encoding="utf-8").read().splitlines()[1:]:
            f = line.split("\t")
            if f[1]:
                known[(f[8], f[3])] = int(f[0])
    next_id = max(list(known.values()) + [FIRST_DISPLAY - 1]) + 1

    rows = []
    for i, (name, tier, *displays) in enumerate(STOCK):
        for k, (element, display) in enumerate(zip(ELEMENTS, displays)):
            rows.append((display, "", "", element, tier, "", look_name(name, element), "", "",
                         STOCK_PREVIEW_BASE + 4 * i + k))
    for folder, name, tier, *displays in RETAIL:
        for element, retail in zip(ELEMENTS, displays):
            if str(retail) not in cdi:
                raise SystemExit("retail display %d (%s %s) is gone" % (retail, name, element))
            display = known.get((folder, element))
            if display is None:
                display = next_id
                next_id += 1
            rows.append((display, retail, "", element, tier, "%s_%s" % (folder.lower(), element),
                         look_name(name, element), "", folder, PREVIEW_BASE + display - FIRST_DISPLAY))
    with open(LOOKS, "w", encoding="utf-8") as f:
        f.write("display\tretail_display\tvariant\tform\ttier\tmodel\tname\ttextures\tfolder\tpreview\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    print("%d looks (%d from the client, %d from retail) -> %s" % (
        len(rows), 4 * len(STOCK), 4 * len(RETAIL), LOOKS))


if __name__ == "__main__":
    main()
