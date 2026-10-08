#!/usr/bin/env python3
"""List every retail druid form look and write data/looks.tsv.

    python3 inventory.py --cache <download dir>

A look is a retail CreatureDisplayInfo that the barber shop offers for a druid form
(ChrCustomizationDisplayInfo), plus the Haranir forms retail files under no form. Each gets a
3.3.5 display id, a name and the Individual Progression tier that unlocks it. Display ids already
in looks.tsv are kept, so rerunning never moves a look a player may have chosen.
"""
import argparse
import collections
import os
import re

from fetch import db2, db2_rows, listfile

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKS = os.path.join(HERE, "..", "data", "looks.tsv")
FIRST_DISPLAY = 95000

RETAIL_FORMS = {"Bear Form": "bear", "Cat Form": "cat", "Travel Form": "travel", "Aquatic Form": "aquatic",
                "Flight Form": "flight", "Flight Form, Epic": "flight", "Moonkin Form": "moonkin",
                "Treant Form": "tree"}
FORM_ORDER = ["bear", "cat", "travel", "aquatic", "flight", "moonkin", "tree"]

# Unlock tier per model (Individual Progression state n = content n cleared; 0 = from the start).
TIERS = {
    # 0: the classic looks, remade in HD
    "druidbear2": 0, "druidbeartauren2": 0, "druidcat2": 0, "druidcattauren2": 0,
    "druidtravelalliance": 0, "druidtravelhorde": 0, "druidtravelcat": 0, "sealion2": 0,
    "orca_druid": 0, "stormcrowdruid": 0, "epicdruidflightalliance": 0, "epicdruidflighthorde": 0,
    "druidowlbear2": 0, "druidowlbeartauren2": 0, "druidtreeform": 0, "ent2": 0,
    # 1 Molten Core: fire and stone
    "flamecat": 1, "dreamowl_fire": 1, "druidbear2_artifact2": 1,
    # 2 Onyxia's Lair: Darkspear trolls
    "druidbeartroll2": 2, "druidcattroll2": 2, "epicdruidflighttroll": 2,
    # 3 Blackwing Lair: worgen of Gilneas
    "druidbearworgen2": 3, "druidcatworgen2": 3, "epicdruidflightworgen": 3, "doe": 3,
    # 4 Zul'Gurub: the Zandalari
    "druidbearzandalaritroll": 4, "druidcatzandalaritroll": 4, "druidtravelzandalaritroll": 4,
    "druidflightzandalaritroll": 4, "druidflightzandalaritroll_noarmor": 4,
    "druidaquaticzandalari": 4, "zandalarimoonkin": 4,
    # 5 Ahn'Qiraj War Effort: the Cenarion Circle
    "druidbear2_artifact5": 5, "owlcat": 5, "owl2": 5,
    # 6 Temple of Ahn'Qiraj
    "druidbear2_artifact3": 6, "druidcat2_artifact3": 6, "dolphin2": 6,
    # 7 Naxxramas: the Nightmare
    "druidbear2_artifact4": 7, "druidcat2_artifact5": 7, "raven2": 7, "giantvampirebat": 7,
    # 8 the road to Outland: Highmountain
    "druidbearhmtauren": 8, "druidcathmtauren": 8, "druidtravelhmtauren": 8,
    "druidflighthmtauren": 8, "druidowlbearhmtauren2": 8,
    # 9 Karazhan, Gruul, Magtheridon: Kul Tiras (bear, cat)
    "druidbearkultiran": 9, "druidcatkultiran": 9,
    # 10 SSC and Tempest Keep: Kul Tiras (the rest)
    "druidtravelkultiran": 10, "druidaquatickultiran": 10, "druidflightkultiran": 10, "kultiranmoonkin": 10,
    # 11 Hyjal and Black Temple
    "druidflightform": 11, "felbat": 11, "druidcat2_artifact4": 11,
    # 12 Zul'Aman
    "owlbear": 12, "druidcat2_artifact2": 12, "runebear": 12,
    # 13 Sunwell Plateau: the Haranir
    "druidbearharanir": 13, "druidcatharanir": 13, "druidtravelharanir": 13, "druidaquaticharanir": 13,
    "druidtreeharanir": 13, "harronirbat": 13, "tindralmoonkin": 13,
    # 14 Naxxramas (80), Eye of Eternity, Obsidian Sanctum: Grizzly Hills
    "druidbear2_artifact6": 14, "werebear": 14, "mothardenweald": 14,
    # 15 Ulduar: the artifact forms
    "druidbear2_artifact1": 15, "druidcat2_artifact1": 15,
    # 16 Trial of the Crusader / 17 Icecrown Citadel: the Emerald Dream
    "ardenwealdstag": 16, "emeralddreamstag": 16, "magicalfish": 16, "dreamowl": 16,
    "dreamsaber": 17, "dreambear": 17, "sabretoothraptor": 17,
    # 18 Ruby Sanctum: the Batbear
    "tindralmoonkin_haranir": 18,
}

GEOSET_STYLE = {"tindralmoonkin_haranir": "Style %d-%d"}

# Looks retail leaves untextured (Haranir druids wear their own skin colour): one look per colour
# in the model's folder. Each entry: model -> (colour file pattern, files for slots 1 and 2), where
# slot n is creature texture type 11+n and "{c}" is the colour.
SKIN_SETS = {
    "druidbearharanir": ("druidbearharanir_{c}_skin", "druidbearharanir_{c}_skin", None),
    "druidcatharanir": ("druidcatharanir_{c}_skin", "druidcatharanir_color_6224369", None),
    "druidtravelharanir": ("druidtravelharanir_{c}_skin", "druidtravelharanir_{c}_skin", None),
    "harronirbat": ("harronirbat_body_{c}", "harronirbat_5862800", None),
    "tindralmoonkin": ("tindralmoonkin_body_{c}", "tindralmoonkin_jewelry_{c}", "tindralmoonkin_antlers_5369290"),
}

# Race-model families: "<family> (<colour>)" reads better than a bare colour repeated per race.
FAMILY = {}
for race, label in (("", "Kaldorei"), ("tauren", "Shu'halo"), ("troll", "Darkspear"), ("worgen", "Gilnean"),
                    ("hmtauren", "Highmountain"), ("kultiran", "Kul Tiran"), ("zandalaritroll", "Zandalari"),
                    ("zandalari", "Zandalari"), ("haranir", "Haranir")):
    for form, word, models in (("bear", "Bear", ["druidbear%s2", "druidbear%s"]),
                               ("cat", "Cat", ["druidcat%s2", "druidcat%s"]),
                               ("travel", "Stag", ["druidtravel%s"]), ("aquatic", "Seal", ["druidaquatic%s"]),
                               ("moonkin", "Moonkin", ["druidowlbear%s2", "druidowlbear%s", "%smoonkin"]),
                               ("flight", "Flyer", ["druidflight%s"])):
        for m in models:
            FAMILY.setdefault((m % race).rstrip("2") if not race else m % race, "%s %s" % (label, word))
FAMILY.update({"druidbear2": "Kaldorei Bear", "druidcat2": "Kaldorei Cat", "druidowlbear2": "Kaldorei Moonkin",
               "druidtravelalliance": "Kaldorei Stag", "druidtravelhorde": "Shu'halo Stag",
               "druidtravelcat": "Cheetah", "druidtravelhmtauren": "Highmountain Moose",
               "druidtravelzandalaritroll": "Zandalari Raptor", "druidaquaticzandalari": "Zandalari Sea Creature",
               "druidaquatickultiran": "Kul Tiran Sea Creature", "druidaquaticharanir": "Haranir Sea Creature",
               "druidtravelkultiran": "Kul Tiran Stag", "druidtravelharanir": "Haranir Stag",
               "druidtreeharanir": "Haranir Treant", "druidtreeform": "Tree of Life", "harronirbat": "Haranir Bat",
               "tindralmoonkin": "Haranir Moonkin", "tindralmoonkin_haranir": "Batbear",
               "druidflighthmtauren": "Highmountain Eagle", "druidflightzandalaritroll": "Zandalari Pterrordax",
               "druidflightzandalaritroll_noarmor": "Unarmored Zandalari Pterrordax",
               "epicdruidflightworgen": "Gilnean Storm Crow", "epicdruidflighttroll": "Darkspear Bat",
               "epicdruidflightalliance": "Storm Crow", "epicdruidflighthorde": "Hawk",
               "druidflightkultiran": "Kul Tiran Flyer", "kultiranmoonkin": "Kul Tiran Moonkin",
               "zandalarimoonkin": "Zandalari Moonkin", "druidowlbearhmtauren2": "Highmountain Moonkin",
               "druidowlbeartauren2": "Shu'halo Moonkin"})
GENERIC = {"Classic", "Humble Flyer"}
NOISE = {"ne", "ta", "hmt", "skin", "eyes", "noarmor", "color", "colour", "base", "diffuse", "horns",
         "duidowlbear", "druidowlbear", "bat", "batskin"}


def stem(path):
    return os.path.splitext(os.path.basename(path))[0]


def title(word):
    return " ".join(w.capitalize() for w in word.replace("_", " ").split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    args = ap.parse_args()

    forms = {r["ID"]: r["Name_lang"] for r in db2(args.cache, "SpellShapeshiftForm").values()}
    cdi = db2(args.cache, "CreatureDisplayInfo")
    cmd = db2(args.cache, "CreatureModelData")
    choice = db2(args.cache, "ChrCustomizationChoice")
    geo = collections.defaultdict(list)
    for g in db2_rows(args.cache, "CreatureDisplayInfoGeosetData"):
        geo[g["CreatureDisplayInfoID"]].append((int(g["GeosetIndex"]), int(g["GeosetValue"])))
    names = collections.defaultdict(set)
    for e in db2_rows(args.cache, "ChrCustomizationElement"):
        c = choice.get(e["ChrCustomizationChoiceID"])
        if e["ChrCustomizationDisplayInfoID"] != "0" and c and c["Name_lang"]:
            names[e["ChrCustomizationDisplayInfoID"]].add(c["Name_lang"])

    rows = db2_rows(args.cache, "ChrCustomizationDisplayInfo")
    fdids = set()
    for r in rows:
        d = cdi.get(r["CreatureDisplayInfoID"])
        if d and d["ModelID"] in cmd:
            fdids.add(int(cmd[d["ModelID"]]["FileDataID"]))
            fdids.update(int(d["TextureVariationFileDataID_%d" % k]) for k in range(3))
    paths = listfile(args.cache, fdids)

    looks = {}
    for r in rows:
        d = cdi.get(r["CreatureDisplayInfoID"])
        if not d or d["ModelID"] not in cmd:
            continue
        fdid = int(cmd[d["ModelID"]]["FileDataID"])
        model = stem(paths.get(fdid, str(fdid)))
        form = RETAIL_FORMS.get(forms.get(r["SpellShapeshiftFormID"], ""))
        if form is None:  # Haranir looks sit under no form; their model names tell
            if "druid" not in model and "moonkin" not in model:
                continue
            form = next(f for k, f in (("bear", "bear"), ("cat", "cat"), ("travel", "travel"),
                                        ("aquatic", "aquatic"), ("tree", "tree"), ("moonkin", "moonkin"),
                                        ("bat", "flight")) if k in model)
        if model not in TIERS:
            raise SystemExit("no unlock tier for model %s (display %s)" % (model, r["CreatureDisplayInfoID"]))
        key = int(r["CreatureDisplayInfoID"])
        look = looks.setdefault(key, dict(retail=key, form=form, model=model, fdid=fdid, tier=TIERS[model],
                                          names=set(), geosets=sorted(geo.get(str(key), [])),
                                          tex=[int(d["TextureVariationFileDataID_%d" % k]) for k in range(3)],
                                          option=r["ID"]))
        look["names"] |= names.get(r["ID"], set())

    # Names: race models read "<family> (<choice or colour>)"; others use the barber choice and
    # are told apart by texture colour (and geoset style) when they repeat.
    # Retail repeats some looks (same model, textures and geosets) under several races: keep one.
    unique = {}
    for look in sorted(looks.values(), key=lambda x: x["retail"]):
        unique.setdefault((look["model"], tuple(look["tex"]), tuple(look["geosets"])), look)
    dropped = len(looks) - len(unique)
    looks = {x["retail"]: dict(x, variant="") for x in unique.values()}
    # Untextured looks with a skin set become one look per colour.
    by_path = {}
    folders = {x["model"] for x in looks.values() if x["model"] in SKIN_SETS}
    for fd, path in listfile(args.cache, None, prefixes=["creature/%s/" % m for m in folders]).items():
        by_path[stem(path).lower()] = fd
    expanded = {}
    for look in looks.values():
        if look["model"] not in SKIN_SETS or any(look["tex"]):
            expanded[(look["retail"], "")] = look
            continue
        if any(k[0] != look["retail"] and v["model"] == look["model"] and not any(v["tex"])
               for k, v in expanded.items()):
            continue  # one untextured look per model is enough
        base_pat, slot1, slot2 = SKIN_SETS[look["model"]]
        prefix, suffix = base_pat.split("{c}")
        colours = sorted(n[len(prefix):len(n) - len(suffix)] for n in by_path
                         if n.startswith(prefix) and n.endswith(suffix) and len(n) > len(prefix) + len(suffix))
        for c in colours:
            tex = [by_path[base_pat.format(c=c)]]
            for pat in (slot1, slot2):
                tex.append(by_path.get(pat.format(c=c), by_path.get(pat, 0)) if pat else 0)
            v = dict(look, tex=tex + [0], variant=c, names={title(c)})
            expanded[(look["retail"], c)] = v
    # An untextured look next to textured ones of the same model is only the model's default skin.
    textured = {x["model"] for x in expanded.values() if any(x["tex"])}
    looks = {k: v for k, v in expanded.items() if any(v["tex"]) or v["model"] not in textured}
    textures_of = collections.defaultdict(set)
    for look in looks.values():
        textures_of[look["model"]].add(look["tex"][0])
    colour_index = collections.defaultdict(dict)
    for look in sorted(looks.values(), key=lambda x: x["retail"]):
        tex = paths.get(look["tex"][0], "")
        model_words = set(re.split(r"[_\d]+", look["model"].lower())) | {look["model"].lower()}
        words = [w for w in re.split(r"[_\d]+", stem(tex).lower()) if w]
        words = [re.sub(r"^(bat)?skin|skin$", "", w) for w in words]
        colour = title(" ".join(w for w in words if w and w not in model_words and w not in NOISE
                                and not any(w.startswith(m) and len(m) > 4 for m in model_words)))
        if not colour and look["tex"][0] and len(textures_of[look["model"]]) > 1 and not look["names"]:
            idx = colour_index[look["model"]].setdefault(look["tex"][0], len(colour_index[look["model"]]) + 1)
            colour = "Colour %d" % idx
        look["colour"] = colour
        choice_name = sorted(look["names"])[0] if look["names"] else None
        if look["variant"]:
            choice_name = title(look["variant"])
        if look["model"] in FAMILY:
            look["base"] = FAMILY[look["model"]]
            look["detail"] = choice_name if choice_name and choice_name not in GENERIC else colour
            if not look["detail"] and len(textures_of[look["model"]]) > 1:
                look["detail"] = choice_name
            if look["detail"] and look["detail"].lower() in look["base"].lower():
                look["detail"] = None
        else:
            look["base"] = choice_name or title(look["model"])
            look["detail"] = None
    seen = collections.Counter((x["form"], x["base"]) for x in looks.values())
    for look in looks.values():
        extra = []
        if look["detail"]:
            extra.append(look["detail"])
        elif seen[(look["form"], look["base"])] > 1 and look["colour"]:
            extra.append(look["colour"])
        if look["model"] in GEOSET_STYLE and look["geosets"]:
            idx = colour_index[look["model"]].setdefault(look["tex"][0], len(colour_index[look["model"]]) + 1)
            extra = ["Colour %d" % idx]
            vals = dict(look["geosets"])
            extra.append(GEOSET_STYLE[look["model"]] % (vals.get(0, 0), vals.get(1, 0)))
        look["name"] = "%s (%s)" % (look["base"], ", ".join(extra)) if extra else look["base"]
    dupes = collections.Counter((x["form"], x["name"]) for x in looks.values())
    numbered = collections.Counter()
    for look in sorted(looks.values(), key=lambda x: x["retail"]):
        if dupes[(look["form"], look["name"])] > 1:
            numbered[(look["form"], look["name"])] += 1
            look["name"] += " %d" % numbered[(look["form"], look["name"])]

    # Stable display ids.
    known = {}
    if os.path.exists(LOOKS):
        for line in open(LOOKS, encoding="utf-8").read().splitlines()[1:]:
            f = line.split("\t")
            known[(int(f[1]), f[2] if len(f) > 7 else "")] = int(f[0])
    next_id = max(list(known.values()) + [FIRST_DISPLAY - 1]) + 1
    ordered = sorted(looks.values(), key=lambda x: (x["tier"], FORM_ORDER.index(x["form"]), x["model"], x["name"]))
    for look in ordered:
        if (look["retail"], look["variant"]) in known:
            look["display"] = known[(look["retail"], look["variant"])]
        else:
            look["display"] = next_id
            next_id += 1
    with open(LOOKS, "w", encoding="utf-8") as f:
        f.write("display\tretail_display\tvariant\tform\ttier\tmodel\tname\ttextures\n")
        for look in sorted(ordered, key=lambda x: x["display"]):
            tex = ",".join(str(t) for t in look["tex"][:3]) if look["variant"] else ""
            f.write("%d\t%d\t%s\t%s\t%d\t%s\t%s\t%s\n" % (look["display"], look["retail"], look["variant"],
                                                         look["form"], look["tier"], look["model"],
                                                         look["name"], tex))
    per_tier = collections.Counter(x["tier"] for x in ordered)
    print("%d duplicate retail displays skipped" % dropped)
    print("%d looks, %d models -> %s" % (len(ordered), len({x["fdid"] for x in ordered}), LOOKS))
    print("per tier:", dict(sorted(per_tier.items())))


if __name__ == "__main__":
    main()
