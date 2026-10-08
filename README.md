# mod-retail-druid-forms

Tools that bring retail World of Warcraft's druid form looks to a 3.3.5a client. They download
the retail models, convert them (animations included) to the 3.3.5a model format, and build a
client patch that adds each look as a creature display. Everyone with the patch sees everyone's
form looks, with no client hacks.

The server side (which looks a druid has unlocked, the Forms tab, swapping the model when the
druid shifts) lives in
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
- `tools/check_m2.py` checks a converted model the way the client reads it.
- `tools/build_patch.py` downloads everything, converts each model once per geoset combination,
  and writes `patch-I.MPQ`. It also writes the mod-transmog-plus SQL: the looks, one preview
  creature per look, and the server copies of the new display rows.
  - New CreatureDisplayInfo rows are 95000+, and CreatureModelData rows are 9500+.
  - The models are under `Creature\RetailForms`.
  - Textures larger than `--max-texture` (default 1024) lose their top mip levels.

Nothing from Blizzard is stored in this repo; the files come from wago.tools at build time.

## Building

```bash
python3 tools/inventory.py --cache ~/forms-cache
```

```bash
python3 tools/build_patch.py --dbc <dbc dir> --cache ~/forms-cache --work ~/forms-work --out patch-I.MPQ --sql forms_data.sql
```

`--dbc` needs `CreatureDisplayInfo.dbc`, `CreatureModelData.dbc` and `AnimationData.dbc`: the
client's stock copies (the server has them in `env/dist/data/dbc`).

### HD creature packs

A patch replaces whole files. An HD creature pack ships its own `CreatureDisplayInfo.dbc` and
`CreatureModelData.dbc`, and patch-I loads after it, so the pack's creatures lose textures (white
armour on HD kodos, for one). A player with such a pack adds a small patch that loads after
patch-I and carries the pack's DBCs plus the form rows:

```bash
python3 tools/build_patch.py --dbc <the pack's DBCs + AnimationData.dbc> --cache ~/forms-cache --work ~/forms-work-hd --out patch-J.MPQ --dbc-only
```

Take the DBCs from the pack's last patch (the highest letter that has them).

## Requirements

- Python 3.10+ (standard library only).
- [StormLib](https://github.com/ladislav-zezula/StormLib) as a shared library. The default is
  `/usr/local/lib/libstorm.dylib`; point `STORMLIB` at yours.

## Troubleshooting

- **A druid shows as nothing, or a white model**: that client lacks patch-I, or an HD creature
  pack loads after it. Build the small `--dbc-only` patch above for that client.
- **White armour on other creatures after adding patch-I**: same cause; the HD pack's DBCs were
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
