# mod-retail-druid-forms

Tools that bring retail World of Warcraft's druid form looks and shaman totem looks to a 3.3.5a
client. They download the retail models, convert them (animations included) to the 3.3.5a model
format, and build a client patch that adds each look as a creature display. Everyone with the
patch sees everyone's looks, with no client hacks.

The server side (which looks a character has unlocked, the Forms and Totems tabs, swapping the
model when the druid shifts or the shaman drops a totem) lives in
[wow-mod-transmog-plus](https://github.com/buildthehomelab/wow-mod-transmog-plus). This repo is
only the client patch toolchain.

## The looks

`data/looks.tsv` lists all 265 looks: every druid form choice retail's barber shop offers, plus
the Haranir forms in each skin colour.

| Form | Looks | Examples |
| --- | --- | --- |
| Bear | 71 | race colours, Claws of Ursoc, Fallen to Nightmare, Bristlebruin, Umbraclaw, Runebear |
| Cat | 68 | race colours, Fangs of Ashamane, Moonspirit, Druid of the Flame, Dreamsaber |
| Moonkin | 44 | race moonkin, Kul Tiran, Haranir, Batbear |
| Flight | 36 | Storm Crow, Sentinel, Lunarwing, Dredbats, Ravens, Somnowls, Ardenmoths |
| Travel | 25 | stags, Cheetah, Moose, Raptor, Gladehart, Runestag, Dreamtalon |
| Aquatic | 18 | Orca, Sea Lion, Dolphin, race sea creatures, Dreaming Nae'dra |
| Tree | 3 | Tree of Life, Treant, Haranir Treant |

Each look has the individual progression phase that unlocks it (0 = from the start). The
classic looks are free; each phase after that unlocks a themed batch:

| Phase | Unlocks |
| --- | --- |
| 0 | the classic Night Elf and Tauren looks remade in HD, stags, cheetah, seal, crow, moonkin, trees |
| 1 Molten Core | Stonepaw, Druid of the Flame, Anu'relos |
| 2 Onyxia | Darkspear (troll) bear, cat and bat |
| 3 Blackwing Lair | Gilnean (worgen) bear, cat, crow and Doe |
| 4 Zul'Gurub | all Zandalari forms |
| 5 AQ War Effort | Guardian of the Glade, Moonspirit, Sentinel owls |
| 6 Ahn'Qiraj | Avatar of Ursol, Nature's Fury, Dolphin |
| 7 Naxxramas | Fallen to Nightmare, Incarnation of Nightmare, Dredbats, Ravens |
| 8 Road to Outland | all Highmountain forms |
| 9 Karazhan / Gruul / Magtheridon | Kul Tiran bear and cat |
| 10 SSC / Tempest Keep | the other Kul Tiran forms |
| 11 Hyjal / Black Temple | Primal Stalker, Lunarwing, Scornwing |
| 12 Zul'Aman | Umbraclaw, Runebear, Ghost of the Pridemother |
| 13 Sunwell | all Haranir forms |
| 14 Naxxramas (80) / EoE / OS | Might and Blight of the Grizzlemaw, Ardenmoths |
| 15 Ulduar | Claws of Ursoc, Fangs of Ashamane |
| 16 Trial of the Crusader | Gladehart, Runestag, Somnowls, Dreaming Nae'dra |
| 17 Icecrown Citadel | Dreamsaber, Bristlebruin, Dreamtalon |
| 18 Ruby Sanctum | Batbear (30 colour and style combinations) |

To move a batch, change its line in `TIERS` in `tools/inventory.py` and rerun it.

## The totems

`data/totems.tsv` lists 80 totem looks: 20 sets of four (fire, earth, water, air). A shaman
picks a look per element, whatever their race.

Five sets are the 3.3.5a client's own race totems. They need no patch and keep all their
effects; any shaman can use them from the start. The other 15 are retail's, converted:

| Phase | Unlocks |
| --- | --- |
| 0 | Tauren, Orc, Troll, Dwarf and Draenei totems (the client's own) |
| 1 Molten Core | Dark Iron |
| 2 Onyxia | Tauren (Remastered), retail's remake of the classic totems |
| 3 Blackwing Lair | Goblin |
| 4 Zul'Gurub | Zandalari |
| 5 AQ War Effort | Vulpera |
| 6 Ahn'Qiraj | Pandaren |
| 7 Naxxramas | Dark Shaman (Ashflare, Rusted Iron, Foulstream, Poisonmist) |
| 8 Road to Outland | Highmountain |
| 9 Karazhan / Gruul / Magtheridon | Mag'har |
| 10 SSC / Tempest Keep | Kul Tiran |
| 11 Hyjal / Black Temple | Draenor Clans |
| 12 Zul'Aman | Haranir |
| 13 Sunwell | Draenei (Remastered), retail's crystal totems |
| 15 Ulduar | Earthen |
| 17 Icecrown Citadel | Maelstrom (the Legion class hall totems) |

Retail has no table of totem looks (a totem follows the shaman's race), so the sets, their
retail display ids and their phases are listed in `tools/totem_inventory.py`. To move a set,
change its phase there and rerun it.

## How it works

- `tools/inventory.py` reads retail's barber shop tables (ChrCustomizationDisplayInfo and
  friends, from [wago.tools](https://wago.tools)) and writes `data/looks.tsv`. Display ids
  already in the file never move, so a rerun can't change a look a player picked.
- `tools/m2creature.py` converts a retail model (MD21, v272/274) to 3.3.5a (MD20, v264):
  - It keeps the skin-0 mesh, all bones, and every animation 3.3.5 knows (ids 0-505). Animations
    in external `.anim` files are inlined.
  - It also keeps attachments, key bones, colours, texture animations, footstep events and the
    portrait camera.
  - Retail creature geosets are baked in per look, because the 3.3.5 client can't pick them.
  - Particles, ribbons, lights and extra texture passes (env/glow) have no 3.3.5 equivalent and
    are dropped. The artifact forms lose some sparkle.
  - Some retail `.anim` files no longer match their model (left over from an older version).
    Those animations (mostly sit, sleep and emotes) are dropped, and the client falls back to
    another animation.
- `tools/totem_inventory.py` writes `data/totems.tsv` from its list of totem sets, with the
  same rule: ids already in the file never move.
- `tools/check_m2.py` checks a converted model the way the client reads it.
- `tools/build_patch.py` downloads everything, converts each model once per geoset combination,
  and writes the patch. It also writes the mod-transmog-plus SQL: the looks, one preview
  creature per look, and the server copies of the new display rows. `--pack` picks what to build:
  - `forms` (the default) is `patch-R.MPQ`: CreatureDisplayInfo rows 95000+, CreatureModelData
    rows 9500+, models under `Creature\RetailForms`.
  - `totems` is `patch-V.MPQ`: CreatureDisplayInfo and CreatureModelData rows 96000+, models
    under `Creature\RetailTotems`. Textures only the dropped particles used are left out, and
    an effect mesh that blends two textures is drawn with the one that isn't a mask.
  - Textures larger than `--max-texture` (default 1024) lose their top mip levels.

Nothing from Blizzard is stored in this repo; the files come from wago.tools at build time.

## Building

```bash
python3 tools/inventory.py --cache ~/forms-cache
```

```bash
python3 tools/build_patch.py --dbc <dbc dir> --cache ~/forms-cache --work ~/forms-work --out patch-R.MPQ --sql forms_data.sql
```

`--dbc` needs `CreatureDisplayInfo.dbc`, `CreatureModelData.dbc` and `AnimationData.dbc` as the
players' client has them: the copies from the last patch in its load order that ships each one. On
the realm's base client (TheraWoW with Project Reforged HD) that's Reforged's `patch-C.mpq` for the
two creature DBCs and the stock `AnimationData.dbc` (`Data/enUS/patch-enUS-3.MPQ`). Model ids the base
already uses (Reforged has 9511 and 9571) move past the 9500 block, to 9590 and 9591.

The totem patch goes on top of the form patch. Both ship `CreatureDisplayInfo.dbc` and
`CreatureModelData.dbc`, and the later letter wins, so build patch-V with `--dbc` holding the
two DBCs from the finished patch-R (plus `AnimationData.dbc`), and rebuild it whenever patch-R
changes:

```bash
python3 tools/totem_inventory.py --cache ~/forms-cache
```

```bash
python3 tools/build_patch.py --pack totems --dbc <patch-R's DBCs> --cache ~/forms-cache --work ~/totems-work --out patch-V.MPQ --sql totems_data.sql
```

### HD creature packs

A patch replaces whole files. An HD creature pack ships its own `CreatureDisplayInfo.dbc` and
`CreatureModelData.dbc`, so the form patch has to carry the pack's rows too: build it with `--dbc`
pointing at the pack's copies, and give it a letter that loads after the pack's (patch-R loads after
Reforged's patch-C). Built on the wrong DBCs, the pack's creatures lose their textures (white armour
on HD kodos, for one).

When the base client changes, the finished patch can also be moved onto it without downloading the
models again: `tools/client-patches/rebase_patch.py` in the realm's server repo merges the DBCs
(`--renumber CreatureModelData:CreatureDisplayInfo.1` gives clashing models the same new ids as above).
A client whose own HD pack isn't the realm's can still use a small DBC-only patch that loads after
patch-R:

```bash
python3 tools/build_patch.py --dbc <the pack's DBCs + AnimationData.dbc> --cache ~/forms-cache --work ~/forms-work-hd --out patch-Y.MPQ --dbc-only
```

## Requirements

- Python 3.10+ (standard library only).
- [StormLib](https://github.com/ladislav-zezula/StormLib) as a shared library. The default is
  `/usr/local/lib/libstorm.dylib`; point `STORMLIB` at yours.

## Troubleshooting

- **A druid shows as nothing, or a white model**: that client lacks patch-R, or an HD creature
  pack loads after it. Build the small `--dbc-only` patch above for that client.
- **Druid forms vanish after adding patch-V**: it was built on DBCs without the form rows. Build
  it with `--dbc` from patch-R.
- **A retail totem has no flames, drips or sparks**: those are particle effects, which the
  converter drops. The mesh glows and scrolling effects stay. The client's own five race sets
  keep everything.
- **White armour on other creatures after adding patch-R**: same cause; the HD pack's DBCs were
  replaced. Use the `--dbc-only` patch.
- **wago.tools answers 502/504**: the fetcher retries; rerun if it still gives up. Downloads are
  cached in `--cache`.

## Credits

- Model and table data: Blizzard Entertainment, downloaded at build time from
  [wago.tools](https://wago.tools); file names from the
  [wowdev community listfile](https://github.com/wowdev/wow-listfile).
- M2 format notes: [wowdev.wiki](https://wowdev.wiki/M2) and
  [whoa](https://github.com/thunderbrewhq/whoa).

## Patch Notes: Druid Form Looks

Category: Classes / Druid

- Druids can now choose from 265 looks for their shapeshift forms, from the new Forms tab of the
  Transmogrify window (`/transmog`).
- Every form has looks: bear, cat, travel, aquatic, flight, moonkin and Tree of Life.
- The classic looks, remade in HD, are yours from the start. Every raid tier you clear unlocks a
  new batch, from the Zandalari forms in Zul'Gurub to the Batbear in the Ruby Sanctum.
- Previews show each look; locked ones show as a silhouette and tell you where they unlock.

> These are retail's own form models, converted with their animations. Particle effects don't
> survive the trip, so the artifact forms glow a little less than on retail.

## License

MIT. See [LICENSE](LICENSE).
