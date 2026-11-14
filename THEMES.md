# Native plugins and themes

This repository publishes one model only: **native plugins**. A theme is a
native plugin with `"theme": true` in its catalog entry. There is no
declarative theme file, and no second theme list to keep in sync.

A plugin is a shared library that Lapinux loads with `dlopen`. It gets the
same rights as the user running Lapinux. It is reviewed like code, not like
data: see [Safety](#safety).

## Layout

```
plugins/<library>.so    regular plugin
themes/<library>.so     theme plugin (theme: true)
```

The `.so` is the only file you publish. Lapinux downloads it, verifies its
SHA-256 and size, checks the ABI and the architecture, then writes a local
manifest `<id>.toml` next to the library and loads it. Nothing else is
downloaded and no manifest is published here.

## Catalog entry

A plugin or theme entry carries its metadata in `catalog.json`:

```json
{
  "id": "kokiri",
  "title": "Kokiri",
  "description": "Forest village palette, fireflies and grass.",
  "author": { "name": "…" },
  "version": "1.0.0",
  "license": "CC0-1.0",
  "status": "experimental",
  "theme": true,
  "abi": 6,
  "arch": "x86_64",
  "min_lapinux_version": "0.1.1",
  "binary": {
    "file": "themes/liblapinux_plugin_theme_kokiri.so",
    "sha256": "…",
    "size": 18576
  }
}
```

- `theme`: `true` makes it appear in **Settings → Appearance → Themes**;
  otherwise it appears in the plugin list.
- `abi`: the native ABI it was built against. Lapinux refuses another version
  instead of loading it. Current ABI: **6**.
- `arch`: `x86_64`, `aarch64` or `any`. Lapinux refuses a binary built for
  another architecture.
- `min_lapinux_version`: optional; install is refused on an older Lapinux.
- `binary.sha256` and `binary.size` are computed by `tools/catalog.py` from the
  file on disk — never edit them by hand.

`tools/catalog.py` rewrites the catalog from the libraries present, and
`tools/theme_probe.py` (run in CI) loads each library, reads its descriptor and
checks the ABI, the ELF architecture and the callbacks it exports.

## Install, activate, remove

- Installing from the catalog downloads the `.so`, verifies it, and writes the
  manifest and library in `~/.config/lapinux/plugins/`.
- Installing a theme also makes it the active theme.
- The library is loaded immediately; a restart is not needed for a fresh
  install.
- Removing a theme falls back to the classic theme.
- Replacing an already-loaded library is not safe in-process: after an update,
  restart Lapinux. Libraries are kept loaded for the whole process lifetime.

## Native ABI, version 6

The library exports one symbol:

```c
const PluginDescriptor *lapinux_plugin_entry(void);
```

`PluginDescriptor` is `#[repr(C)]` and 56 bytes wide on 64-bit targets:

| offset | field | type |
| --- | --- | --- |
| 0 | `abi_version` | `uint32_t` (must be `6`) |
| 4 | padding | 4 bytes |
| 8 | `init` | `bool (*)(const HostApi *)`, nullable |
| 16 | `draw` | `void (*)(const HostApi *)`, nullable |
| 24 | `page` | `const char *(*)(const HostApi *, float w, float h, double time)`, nullable |
| 32 | `theme` | `const char *(*)(const HostApi *)`, nullable |
| 40 | `theme_frame` | `const char *(*)(const HostApi *, float w, float h, double time)`, nullable |
| 48 | `home` | `const char *(*)(const HostApi *, float w, float h, double time)`, nullable |

A theme needs `theme` (palette and geometry) and usually `theme_frame` (the
background). A plugin needs at least one of `draw`, `page` or `home`.
`init` is called once with the host API; returning `false` refuses the plugin.

`HostApi` is versioned too. It starts with `abi_version` (`uint32_t`),
`struct_size` (`size_t`) and `context` (opaque pointer that must be passed back
to every callback). Then come the host callbacks: `library_json`, `action`,
`free_string`, `page_json`, `input_json`. Check `abi_version == 6` and
`struct_size >= sizeof(HostApi)` before using it.

### Units and JSON

All lengths are in points of the Lapinux window (the same unit egui uses),
`time` is seconds since Lapinux started, `now` is a Unix timestamp.

`theme` returns a `ThemeSpec` object:

```json
{
  "colors": {
    "background": [r, g, b, a], "panel": [r, g, b, a], "card": [r, g, b, a],
    "card_hover": [r, g, b, a], "card_active": [r, g, b, a],
    "border": [r, g, b, a], "accent": [r, g, b, a],
    "text": [r, g, b, a], "text_dim": [r, g, b, a]
  },
  "rounding": 12.0,
  "font_scale": 1.0
}
```

Colours are straight (non-premultiplied) RGBA. Missing keys fall back to the
classic theme.

`theme_frame`, `page` and `home` return a JSON array of drawing commands, each
tagged by `type`:

| type | fields |
| --- | --- |
| `text` | `x`, `y`, `text`, `size`, `color`, `align` (`left`/`center`/`right`) |
| `rect` | `x`, `y`, `width`, `height`, `rounding`, `color` |
| `circle` | `x`, `y`, `radius`, `color` |
| `line` | `x1`, `y1`, `x2`, `y2`, `width`, `color` |
| `cover` | `appid`, `x`, `y`, `width`, `height`, `rounding` — host picks the art |
| `nav_icon` | `page`, `x`, `y`, `size`, `color` — host draws the section icon |

The host API hands back `library_json` (`LibraryGame[]`), `page_json`
(`PageText`) and `input_json` (`PageInput`: `width`, `height`, `time`, `now`,
`keys`, `mouse`, `clicked`, `double_clicked`, `scroll`, `nav`, `labels`).

### Ownership and errors

- Strings returned by a plugin (`*const char`) belong to the plugin and must
  stay valid until the next call of that same callback. Null means "nothing to
  draw this frame"; the host keeps the previous state and logs it in debug.
- Strings returned by the host (`library_json`, `page_json`, `input_json`) are
  allocated by Lapinux and must be released with `free_string`.
- Invalid JSON is logged and ignored; it never crashes the host.
- Callbacks run on the UI thread, once per frame, without reentrancy. They must
  not block: a slow callback blocks the interface.

## Safety

Native plugins are code, not data. Lapinux cannot sandbox a `.so` loaded in its
own process, so the catalogue is the trust boundary: only reviewed binaries are
published here, and the app asks before installing one. A theme may read files
you can read, use the network and crash the process. Do not install a theme
from an untrusted source.

## Contributing a native theme

1. Put the library in `themes/`, the source under `themes/<id>/src/`, plus a
   build script and the license of the code.
2. Add the catalog entry with `theme: true`, `abi`, `arch` and the license.
3. Build against ABI 6 for `x86_64`; keep the build reproducible and record the
   compiler and flags used.
4. Run `python3 tools/catalog.py` then `python3 tools/theme_probe.py`; both must
   pass with no problems.
5. Test it in Lapinux itself: 1280×800, 1080p and 4K, multi-DPI, theme switch,
   removal and restart.
6. Only then ask for `status: "verified"`.
