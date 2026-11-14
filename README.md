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
plugins/<id>.toml                native plugin manifest
plugins/bin/<library>.so         the matching library, published at release
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

## Publish a native plugin

A plugin is a manifest plus its library:

```
plugins/<id>.toml      id, name, description, author, version, license,
                       status, native = { library = "plugins/bin/….so" }
plugins/bin/….so       the compiled library
```

`python3 tools/catalog.py` records the manifest and the library with their
digests and sizes. The app downloads both, verifies them, checks the plugin ABI
and only then writes them to `~/.config/lapinux/plugins/`. A plugin that
provides an interface theme sets `native.theme = true` and is listed with the
themes in the app.

## Declarative themes

A small palette-only theme is a `.theme` file (TOML syntax) under `themes/`:
`id`, `name`, `description`, `author`, `version`, `license`, `status` and the
palette fields. No image, no script, no game action. The file name must be
`<id>.theme`. A theme that draws its own layout belongs in a native plugin
instead.

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
