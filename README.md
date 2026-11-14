# Lapinux Configurations

Community catalog for [Lapinux](../README.md): per-game fixes and native
plugins, published as `catalog.json` and consumed by the app.

A configuration never launches a game or a store client. It edits settings and
copies files that the player chooses to apply, and every file is verified
against its published SHA-256 before it is written. Native plugins are the one
deliberate exception: they ship a compiled `.so`, are opt-in, and the app checks
their ABI before loading them.

## Layout

```
catalog.json                     generated catalog, never hand-edited
configurations/<game>/<variant>/
  manifest.json                  the configuration itself
  README.md                      what it fixes, how it was tested
  files/…                        optional files copied into the game
plugins/<library>.so              native plugin libraries
themes/<library>.so               native theme libraries (draw their own layout)
schema/catalog.schema.json       catalog validation
schema/configuration.schema.json manifest validation
tools/catalog.py                 validator and catalog builder
```

## Publish a fix

1. Create `configurations/<game>/<variant>/` with `manifest.json`, a short
   `README.md` and, if needed, the files under `files/`.
2. Fill the fields — `schema/configuration.schema.json` is the reference:
   `id`, `title`, `description`, `solution`, `type`, `platform`, `layers`,
   `author`, `version`, `license`, `status`, `tested`, `game` and `actions`.
3. Describe the game by `game.names`, `game.steam_appids` or `game.store_ids`;
   the app matches on all three.
4. Build and check:

```bash
python3 tools/catalog.py          # validate, rewrite catalog.json
python3 tools/catalog.py --check  # CI: fails if catalog.json is stale
python3 tools/theme_probe.py      # CI: ELF, ABI and callbacks of each .so
```

Every `sha256` and `size` is computed from the files on disk: never edit them
by hand. A manifest that fails validation is reported and left out.

## Actions

- `settings`: `env`, `dxvk`, `args`, Proton or GameScope options applied at
  launch.
- `files`: files copied into the install folder, with `backup` (default true)
  so **Remove** restores the original bytes.

Every file entry needs `source`, `target` and `sha256`; a mismatch aborts the
installation instead of writing unknown bytes.

## Publish a native plugin or theme

A plugin or theme is a single `.so`, dropped in `plugins/` or `themes/`. Its
metadata lives in `catalog.json`: `id`, `title`, `description`, `author`,
`version`, `license`, `status`, and the `binary` entry the builder keeps up to
date with the library's SHA-256 and size. A library in `themes/` is published
with `theme: true` and appears with the interface themes in Lapinux.

To add one, copy the `.so` into the right folder and add its metadata entry to
`catalog.json` — including `abi` and `arch` — then run
`python3 tools/catalog.py`: the builder finds every library, matches it to its
entry, refreshes digest and size, and refuses a library without metadata.
Lapinux downloads the `.so`, verifies it, checks the ABI and architecture, and
writes a local manifest itself.

`python3 tools/theme_probe.py` is the smoke test: it loads every published
library, reads its descriptor and refuses an ABI, an architecture or a missing
callback that Lapinux could not use. CI runs it after the catalog check.

## Themes

A theme is a native plugin with `"theme": true`. It draws its own palette and
background, so it can change as much of the interface as the plugin API
exposes. This repository publishes no declarative theme files.

The full contract — descriptor layout, host API, JSON commands, units, string
ownership, compatibility metadata and the review checklist — is in
[THEMES.md](THEMES.md).

## Versions and retirement

Each entry carries its own `version`. To withdraw one, set `"status": "broken"`
and keep a retired entry in `catalog.json`: the builder preserves retired
entries whose folder is gone, so the published version is not offered again.

## Safety rules

- Never touch a file outside the game's install folder.
- Keep `backup` on for anything you overwrite.
- Do not ship game assets, copyrighted files or credentials.
- A configuration that needs a kernel driver, a store client or an anti-cheat
  bypass is out of scope and will be refused.

## License

CC0-1.0 for the catalog metadata — see [LICENSE](LICENSE). Files and plugins you
add keep their own rights; say so in the entry's `README.md`.
