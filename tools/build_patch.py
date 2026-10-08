#!/usr/bin/env python3
"""Build patch-I.MPQ: every look in data/looks.tsv as a 3.3.5a creature display.

    python3 build_patch.py --dbc <dir> --cache <download dir> --work <dir> --out patch-I.MPQ \\
        [--sql forms.sql] [--max-texture 1024]

--dbc holds the CreatureDisplayInfo.dbc, CreatureModelData.dbc and AnimationData.dbc the realm's
players already have. A patch MPQ replaces whole files, so if another patch the players use ships
those DBCs (an HD creature pack, say), pass its copies, or its creatures lose their textures.

Each retail model is downloaded from wago.tools with its skin, external animations and textures,
converted by m2creature.py (one copy per geoset combination a look needs) and stored under
Creature\\RetailForms. Each look gets a CreatureDisplayInfo row (id from looks.tsv) on a
CreatureModelData row cloned from the stock form model, so sounds and footprints stay the form's.
--sql writes the mod-transmog-plus rows (mod_transmog_plus_forms + preview creatures).
"""
import argparse
import collections
import ctypes
import hashlib
import os
import struct
import sys

from check_m2 import check
from fetch import casc, casc_path, db2, db2_rows, listfile
from m2creature import Converter, Retail

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKS = os.path.join(HERE, "..", "data", "looks.tsv")
MODEL_ROOT = "Creature\\RetailForms"
FIRST_MODEL_ID = 9500          # CreatureModelData ids (stock max 3440)
PREVIEW_CREATURE_BASE = 9501000  # creature_template entry = base + (display - 95000), for addon previews

# Stock display each form clones for sounds, blood, footprints, size class.
TEMPLATE_DISPLAY = {"bear": 2281, "cat": 892, "travel": 918, "aquatic": 2428, "flight": 21243,
                    "moonkin": 15374, "tree": 864}


# --- DBC ---------------------------------------------------------------------------------------

def read_dbc(path):
    data = open(path, "rb").read()
    magic, count, fields, size, strsize = struct.unpack_from("<4s4I", data, 0)
    assert magic == b"WDBC" and size == fields * 4, path
    rows = [list(struct.unpack_from("<%dI" % fields, data, 20 + i * size)) for i in range(count)]
    strings = bytearray(data[20 + count * size:20 + count * size + strsize])
    return rows, strings, fields


def write_dbc(path, rows, strings, fields):
    rows = sorted(rows, key=lambda r: r[0])
    with open(path, "wb") as f:
        f.write(struct.pack("<4s4I", b"WDBC", len(rows), fields, fields * 4, len(strings)))
        for r in rows:
            f.write(struct.pack("<%dI" % fields, *r))
        f.write(strings)


def add_string(strings, text):
    at = len(strings)
    strings.extend(text.encode("utf-8") + b"\0")
    return at


def f32(v):
    return struct.unpack("<I", struct.pack("<f", float(v)))[0]


def row_of(rows, row_id):
    for r in rows:
        if r[0] == row_id:
            return list(r)
    sys.exit("row %d missing from the base DBC" % row_id)


# --- textures ----------------------------------------------------------------------------------

def shrink_blp(data, max_size):
    """Drop top mip levels of a mipmapped BLP2 until it fits max_size (lossless for the rest)."""
    if data[:4] != b"BLP2" or not max_size:
        return data
    ctype, enc, adepth, atype, mips = struct.unpack_from("<I4B", data, 4)
    w, h = struct.unpack_from("<II", data, 12)
    offs = list(struct.unpack_from("<16I", data, 20))
    sizes = list(struct.unpack_from("<16I", data, 84))
    drop = 0
    while max(w >> drop, h >> drop) > max_size and drop + 1 < 16 and sizes[drop + 1]:
        drop += 1
    if not drop or not mips:
        return data
    header = 148 + (1024 if enc == 1 else 0)
    body, new_offs, new_sizes, at = bytearray(), [], [], header
    for i in range(drop, 16):
        if not sizes[i]:
            break
        body += data[offs[i]:offs[i] + sizes[i]]
        new_offs.append(at)
        new_sizes.append(sizes[i])
        at += sizes[i]
    new_offs += [0] * (16 - len(new_offs))
    new_sizes += [0] * (16 - len(new_sizes))
    out = bytearray(data[:header])
    struct.pack_into("<II", out, 12, max(1, w >> drop), max(1, h >> drop))
    struct.pack_into("<16I", out, 20, *new_offs)
    struct.pack_into("<16I", out, 84, *new_sizes)
    return bytes(out + body)


# --- MPQ ---------------------------------------------------------------------------------------

def pack(out, files):
    lib = ctypes.CDLL(os.environ.get("STORMLIB", "/usr/local/lib/libstorm.dylib"))
    H = ctypes.c_void_p
    lib.SFileCreateArchive.argtypes = [ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.POINTER(H)]
    lib.SFileAddFileEx.argtypes = [H, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint, ctypes.c_uint]
    lib.SFileCloseArchive.argtypes = [H]
    for fn in (lib.SFileCreateArchive, lib.SFileAddFileEx, lib.SFileCloseArchive):
        fn.restype = ctypes.c_bool
    if os.path.exists(out):
        os.remove(out)
    h = H()
    if not lib.SFileCreateArchive(out.encode(), 0x00300000, max(64, len(files) * 2), ctypes.byref(h)):
        sys.exit("can't create " + out)
    for src, name in files:
        if not lib.SFileAddFileEx(h, src.encode(), name.encode(), 0x80000200, 0x02, 0x02):
            lib.SFileCloseArchive(h)
            os.remove(out)
            sys.exit("can't add " + name)
    if not lib.SFileCloseArchive(h):
        os.remove(out)
        sys.exit("can't finish " + out)


# --- build -------------------------------------------------------------------------------------

def load_looks():
    lines = open(LOOKS, encoding="utf-8").read().splitlines()
    head = lines[0].split("\t")
    return [dict(zip(head, l.split("\t"))) for l in lines[1:]]


def folder_name(model):
    return "".join(p[:1].upper() + p[1:] for p in model.split("_"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dbc", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--work", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--sql")
    ap.add_argument("--max-texture", type=int, default=1024)
    ap.add_argument("--only", help="comma-separated display ids (test builds)")
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)

    looks = load_looks()
    if args.only:
        only = {int(x) for x in args.only.split(",")}
        looks = [l for l in looks if int(l["display"]) in only]
    cdi_r = db2(args.cache, "CreatureDisplayInfo")
    cmd_r = db2(args.cache, "CreatureModelData")
    geo = collections.defaultdict(dict)
    for g in db2_rows(args.cache, "CreatureDisplayInfoGeosetData"):
        geo[g["CreatureDisplayInfoID"]][int(g["GeosetIndex"]) + 1] = int(g["GeosetValue"])

    valid = {r[0] for r in read_dbc(os.path.join(args.dbc, "AnimationData.dbc"))[0]}
    cdi_rows, cdi_str, cdi_fields = read_dbc(os.path.join(args.dbc, "CreatureDisplayInfo.dbc"))
    cmd_rows, cmd_str, cmd_fields = read_dbc(os.path.join(args.dbc, "CreatureModelData.dbc"))
    taken = {r[0] for r in cdi_rows}
    clash = [l["display"] for l in looks if int(l["display"]) in taken]
    if clash:
        sys.exit("display ids already in the base CreatureDisplayInfo.dbc: %s" % ", ".join(clash[:10]))
    if any(r[0] >= FIRST_MODEL_ID for r in cmd_rows):
        sys.exit("the base CreatureModelData.dbc already uses ids from %d" % FIRST_MODEL_ID)

    # Textures per model slot, for looks retail leaves blank (Haranir: the player's own skin).
    slot_fallback = collections.defaultdict(dict)
    for l in looks:
        rd = cdi_r[l["retail_display"]]
        override = [int(x) for x in l.get("textures", "").split(",") if x]
        for k in range(3):
            fd = override[k] if override else int(rd["TextureVariationFileDataID_%d" % k])
            if fd:
                slot_fallback[l["model"]].setdefault(k, fd)

    files = {}  # archive name -> source path
    variants = {}  # (fdid, geosets) -> (model id, folder, stem)
    texture_slots = {}
    warnings = []
    sql_rows = []
    new_cmd, new_cdi = [], []  # rows added to the client DBCs, mirrored into the server's *_dbc tables
    for l in looks:
        display = int(l["display"])
        rd = cdi_r[l["retail_display"]]
        rm = cmd_r[rd["ModelID"]]
        fdid = int(rm["FileDataID"])
        geosets = tuple(sorted(geo.get(l["retail_display"], {}).items()))
        folder = "%s\\%s" % (MODEL_ROOT, folder_name(l["model"]))
        key = (fdid, geosets)
        if key not in variants:
            raw = casc(args.cache, fdid)
            m = Retail(raw)
            anims = {(a, s): casc(args.cache, f) for a, s, f in m.afid if f}
            stem = folder_name(l["model"])
            if any(k[0] == fdid for k in variants):
                stem += "_" + hashlib.md5(repr(geosets).encode()).hexdigest()[:6]
            conv = Converter(raw, casc(args.cache, m.sfid[0]), anims, valid, stem)
            textures, slots = [], set()
            for i, (ttype, tflags, _n, _o) in enumerate(m.arr("textures", "<IIII")):
                if ttype not in (0, 11, 12, 13):
                    fd = m.txid[i] if i < len(m.txid) else 0
                    if not fd:
                        textures.append((None, tflags, None))  # a retail-only texture slot: not drawn
                        continue
                    ttype = 0
                if ttype == 0:
                    fd = m.txid[i] if i < len(m.txid) else 0
                    if not fd:
                        textures.append((0, tflags, "Textures\\ShaneCube.blp"))
                        warnings.append("%s: texture %d has no file" % (stem, i))
                        continue
                    name = "%s\\T%d.blp" % (folder, fd)
                    files[name] = ("tex", fd)
                    textures.append((0, tflags, name))
                else:
                    textures.append((ttype, tflags, None))
                    if 11 <= ttype <= 13:
                        slots.add(ttype - 11)
            m2, skin = conv.convert(textures, dict(geosets))
            errors, info = check(m2, skin)
            if errors:
                sys.exit("%s fails the 3.3.5 checks: %s" % (stem, errors[:5]))
            mp = os.path.join(args.work, stem + ".m2")
            sp = os.path.join(args.work, stem + "00.skin")
            open(mp, "wb").write(m2)
            open(sp, "wb").write(skin)
            files["%s\\%s.m2" % (folder, stem)] = ("file", mp)
            files["%s\\%s00.skin" % (folder, stem)] = ("file", sp)
            model_id = FIRST_MODEL_ID + len(variants)
            row = row_of(cmd_rows, row_of(cdi_rows, TEMPLATE_DISPLAY[l["form"]])[1])
            row[0] = model_id
            row[2] = add_string(cmd_str, "%s\\%s.mdx" % (folder, stem))
            row[4] = f32(rm["ModelScale"] or 1)
            row[14] = f32(rm["CollisionWidth"])
            row[15] = f32(rm["CollisionHeight"])
            row[16] = f32(rm["MountHeight"])
            for k in range(6):
                row[17 + k] = f32(rm["GeoBox_%d" % k])
            cmd_rows.append(row)
            new_cmd.append((row, "%s\\%s.mdx" % (folder, stem)))
            variants[key] = (model_id, folder, stem)
            texture_slots[key] = slots
            print("%-34s %2d/%2d anims, %3d bones, %d batches" % (
                stem, len(conv.kept), len(conv.seqs), m.h["bones"][0], info["batches"]))
            if conv.bad_tracks:
                warnings.append("%s: %d keyframe arrays out of order, left still" % (stem, conv.bad_tracks))
            if conv.dropped:
                warnings.append("%s: stale .anim files, animations %s dropped" % (stem, sorted(set(conv.dropped))))
        model_id, folder, stem = variants[key]
        row = row_of(cdi_rows, TEMPLATE_DISPLAY[l["form"]])
        row[0] = display
        row[1] = model_id
        row[3] = 0
        row[4] = f32(rd["CreatureModelScale"] or 1)
        row[5] = int(rd["CreatureModelAlpha"]) or 255
        override = [int(x) for x in l.get("textures", "").split(",") if x]
        for k in range(3):
            fd = override[k] if override else int(rd["TextureVariationFileDataID_%d" % k])
            if not fd and k in texture_slots[key]:
                fd = slot_fallback[l["model"]].get(k, 0)
                if fd:
                    warnings.append("%d %s: texture slot %d borrowed from another look" % (display, l["name"], k))
                else:
                    warnings.append("%d %s: texture slot %d has no texture (renders white)" % (display, l["name"], k))
            if fd:
                files["%s\\T%d.blp" % (folder, fd)] = ("tex", fd)
                row[6 + k] = add_string(cdi_str, "T%d" % fd)
            else:
                row[6 + k] = 0
        row[9] = 0
        row[13] = 0
        row[14] = 0
        row[15] = 0
        cdi_rows.append(row)
        new_cdi.append((row, [cdi_str[row[6 + k]:cdi_str.index(b"\0", row[6 + k])].decode() if row[6 + k] else ""
                              for k in range(3)]))
        sql_rows.append((display, l["form"], l["name"], int(l["tier"])))

    # Textures (top mips dropped above --max-texture).
    tex_dir = os.path.join(args.work, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    for name, (kind, src) in list(files.items()):
        if kind == "tex":
            data = shrink_blp(casc(args.cache, src), args.max_texture)
            p = os.path.join(tex_dir, "%d_%d.blp" % (src, args.max_texture))
            open(p, "wb").write(data)
            files[name] = ("file", p)

    write_dbc(os.path.join(args.work, "CreatureDisplayInfo.dbc"), cdi_rows, cdi_str, cdi_fields)
    write_dbc(os.path.join(args.work, "CreatureModelData.dbc"), cmd_rows, cmd_str, cmd_fields)
    files["DBFilesClient\\CreatureDisplayInfo.dbc"] = ("file", os.path.join(args.work, "CreatureDisplayInfo.dbc"))
    files["DBFilesClient\\CreatureModelData.dbc"] = ("file", os.path.join(args.work, "CreatureModelData.dbc"))
    pack(args.out, [(src, name) for name, (_k, src) in sorted(files.items())])
    print("%s: %d looks, %d models, %d files, %.1f MB" % (
        args.out, len(looks), len(variants), len(files), os.path.getsize(args.out) / 1e6))
    for w in warnings:
        print("warning:", w)
    if args.sql:
        write_sql(args.sql, sql_rows, new_cdi, new_cmd)


def sql_str(s):
    return "'" + s.replace("\\", "\\\\").replace("'", "\\'") + "'"


def fl(v):
    return "%g" % struct.unpack("<f", struct.pack("<I", v))[0]


def write_sql(path, rows, new_cdi, new_cmd):
    """mod-transmog-plus world rows: the looks, and one creature per look for the addon's preview
    (3.3.5 model frames can show a creature entry, not a display id)."""
    previews = [(PREVIEW_CREATURE_BASE + d - 95000, d, name) for d, _form, name, _tier in rows]
    last = PREVIEW_CREATURE_BASE + 499
    if any(entry > last for entry, _d, _n in previews):
        sys.exit("preview creature entries run past %d" % last)
    with open(path, "w", encoding="utf-8") as f:
        f.write("-- Generated by buildthehomelab/wow-mod-retail-druid-forms tools/build_patch.py from\n")
        f.write("-- data/looks.tsv. The display ids are in that repo's patch-I.MPQ.\n")
        f.write("DELETE FROM `mod_transmog_plus_forms`;\n")
        f.write("INSERT INTO `mod_transmog_plus_forms` (`DisplayId`, `Form`, `Name`, `UnlockPhase`, `PreviewCreature`, `SortOrder`) VALUES\n")
        f.write(",\n".join("(%d, %s, %s, %d, %d, %d)" % (d, sql_str(form), sql_str(name), tier,
                                                       PREVIEW_CREATURE_BASE + d - 95000, i + 1)
                           for i, (d, form, name, tier) in enumerate(rows)) + ";\n\n")
        f.write("-- Preview creatures %d-%d: never spawned.\n" % (PREVIEW_CREATURE_BASE, last))
        f.write("DELETE FROM `creature_template_model` WHERE `CreatureID` BETWEEN %d AND %d;\n" % (PREVIEW_CREATURE_BASE, last))
        f.write("DELETE FROM `creature_template` WHERE `entry` BETWEEN %d AND %d;\n" % (PREVIEW_CREATURE_BASE, last))
        f.write("INSERT INTO `creature_template` (`entry`, `name`, `subname`, `minlevel`, `maxlevel`, `faction`, `type`) VALUES\n")
        f.write(",\n".join("(%d, %s, 'Druid Form', 1, 1, 35, 1)" % (e, sql_str(n)) for e, _d, n in previews) + ";\n")
        f.write("INSERT INTO `creature_template_model` (`CreatureID`, `Idx`, `CreatureDisplayID`, `DisplayScale`, `Probability`) VALUES\n")
        f.write(",\n".join("(%d, 0, %d, 1, 1)" % (e, d) for e, d, _n in previews) + ";\n\n")

        # The server checks creature displays against its own DBC stores: give it the patch's rows.
        ids = [r[0] for r, _t in new_cdi]
        f.write("-- The patch's CreatureDisplayInfo and CreatureModelData rows, for the server's DBC stores.\n")
        f.write("DELETE FROM `creaturedisplayinfo_dbc` WHERE `ID` BETWEEN %d AND %d;\n" % (min(ids), max(ids)))
        f.write("INSERT INTO `creaturedisplayinfo_dbc` (`ID`, `ModelID`, `SoundID`, `ExtendedDisplayInfoID`, `CreatureModelScale`, `CreatureModelAlpha`, `TextureVariation_1`, `TextureVariation_2`, `TextureVariation_3`, `PortraitTextureName`, `BloodLevel`, `BloodID`, `NPCSoundID`, `ParticleColorID`, `CreatureGeosetData`, `ObjectEffectPackageID`) VALUES\n")
        f.write(",\n".join("(%d, %d, %d, %d, %s, %d, %s, %s, %s, '', %d, %d, %d, %d, %d, %d)" % (
            r[0], r[1], r[2], r[3], fl(r[4]), r[5], sql_str(t[0]), sql_str(t[1]), sql_str(t[2]),
            r[10], r[11], r[12], r[13], r[14], r[15]) for r, t in new_cdi) + ";\n")
        mids = [r[0] for r, _n in new_cmd]
        f.write("DELETE FROM `creaturemodeldata_dbc` WHERE `ID` BETWEEN %d AND %d;\n" % (min(mids), max(mids)))
        f.write("INSERT INTO `creaturemodeldata_dbc` (`ID`, `Flags`, `ModelName`, `SizeClass`, `ModelScale`, `BloodID`, `FootprintTextureID`, `FootprintTextureLength`, `FootprintTextureWidth`, `FootprintParticleScale`, `FoleyMaterialID`, `FootstepShakeSize`, `DeathThudShakeSize`, `SoundID`, `CollisionWidth`, `CollisionHeight`, `MountHeight`, `GeoBoxMinX`, `GeoBoxMinY`, `GeoBoxMinZ`, `GeoBoxMaxX`, `GeoBoxMaxY`, `GeoBoxMaxZ`, `WorldEffectScale`, `AttachedEffectScale`, `MissileCollisionRadius`, `MissileCollisionPush`, `MissileCollisionRaise`) VALUES\n")
        f.write(",\n".join("(%d, %d, %s, %d, %s, %d, %d, %s, %s, %s, %d, %d, %d, %d, %s)" % (
            r[0], r[1], sql_str(n), r[3], fl(r[4]), r[5], r[6], fl(r[7]), fl(r[8]), fl(r[9]), r[10], r[11], r[12],
            r[13], ", ".join(fl(x) for x in r[14:28])) for r, n in new_cmd) + ";\n")
        f.write("DELETE FROM `creature_model_info` WHERE `DisplayID` BETWEEN %d AND %d;\n" % (min(ids), max(ids)))
        f.write("INSERT INTO `creature_model_info` (`DisplayID`, `BoundingRadius`, `CombatReach`, `Gender`, `DisplayID_Other_Gender`) VALUES\n")
        f.write(",\n".join("(%d, 1, 1.5, 2, 0)" % d for d in ids) + ";\n")
    print("wrote", path)


if __name__ == "__main__":
    main()
