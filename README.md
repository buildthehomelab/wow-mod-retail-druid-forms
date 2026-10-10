# mod-retail-druid-forms

Retail World of Warcraft's druid form looks for a 3.3.5a realm: 265 looks across bear, cat, travel,
aquatic, flight, moonkin and Tree of Life, picked in the Forms tab of the Transmogrify window.

It is a look pack for [wow-mod-transmog-plus](https://github.com/buildthehomelab/wow-mod-transmog-plus),
which has the tab, remembers what each character picked and swaps the model. A pack is two things:

- a small server module: its world SQL lists the looks (`data/sql/db-world/mod_retail_druid_forms.sql`). There
  is no code to run and nothing to configure.
- a client patch, `patch-R.MPQ`, with the models. Everyone with the patch sees everyone's
  looks, with no client hacks.

Both are built from this repo's list of looks with
[wow-mod-retail-creatures](https://github.com/buildthehomelab/wow-mod-retail-creatures), the
converter the packs share.

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

## Installing

1. Install [wow-mod-transmog-plus](https://github.com/buildthehomelab/wow-mod-transmog-plus).
2. Add this module and rebuild. The SQL applies on the next start, and the druids' Forms tab appears.

   ```bash
   cd azerothcore/modules
   git clone https://github.com/buildthehomelab/wow-mod-retail-druid-forms.git mod-retail-druid-forms
   ```

   Clone into `mod-retail-druid-forms` exactly: AzerothCore derives the module's loader function from the folder
   name.
3. Build the client patch (below) and give it to every player. It has to be required: a player
   without it sees nothing where one of these looks stands.

Without this module the realm is plain transmog: no looks, no tab.

## Building the client patch

Clone the converter next to this repo (as `mod-retail-creatures`), or point `RETAIL_CREATURES` at it.

```bash
python3 tools/inventory.py --cache ~/retail-cache
```

```bash
python3 ../mod-retail-creatures/tools/build_patch.py --pack . --dbc <dbc dir> --cache ~/retail-cache --work ~/mod_retail_druid_forms-work --out patch-R.MPQ --sql data/sql/db-world/mod_retail_druid_forms.sql
```

`inventory.py` reads retail's barber shop tables (ChrCustomizationDisplayInfo and friends) and
writes `data/looks.tsv`. Display ids already in the file never move, so a rerun can't change a look
a player picked. Run it only to pick up new retail looks or after changing `TIERS`.

`--dbc` needs `CreatureDisplayInfo.dbc`, `CreatureModelData.dbc` and `AnimationData.dbc` as the
players' client has them: the copies from the last patch in its load order that ships each one. On
this realm's base client (TheraWoW with Project Reforged HD) that's Reforged's `patch-C.mpq` for the
two creature DBCs and the stock `AnimationData.dbc` (`Data/enUS/patch-enUS-3.MPQ`). Model ids the
base already uses (Reforged has 9511 and 9571) move past the 9500 block, to 9590 and 9591. The
converter's README has more on HD creature packs.

The build rewrites `data/sql/db-world/mod_retail_druid_forms.sql` to match the patch: commit it with the
patch you ship. Ids: CreatureDisplayInfo 95000+, CreatureModelData 9500+, preview creatures in
9501000-9501499 (subname `Druid Form`), `pack.json` has them all.

Nothing from Blizzard is stored in this repo; the files come from wago.tools at build time.

## Uninstalling

Remove the module folder, rebuild, and run `data/sql/uninstall/mod_retail_druid_forms_uninstall.sql` by hand.
Players can keep the patch: unused displays do nothing.

## Requirements

- AzerothCore with [wow-mod-transmog-plus](https://github.com/buildthehomelab/wow-mod-transmog-plus).
- To build the patch: [wow-mod-retail-creatures](https://github.com/buildthehomelab/wow-mod-retail-creatures)
  and what it needs (Python 3.10+, StormLib).

## Troubleshooting

- **A druid shows as nothing, or a white model**: that client lacks patch-R, or a patch that
  ships the creature DBCs loads after it.
- Anything about the models themselves (black or tiny previews, missing effects, white armour
  on other creatures): see the converter's
  [troubleshooting](https://github.com/buildthehomelab/wow-mod-retail-creatures#troubleshooting).

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
