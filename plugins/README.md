# Plugin manifests

This directory publishes the TOML manifests of native Lapinux plugins. A
manifest describes the plugin, its translations and the native library it
expects next to it.

The `.so` binaries are **not** stored in this catalog: this repository only
contains declarative data, and the validator rejects executable files. Plugin
authors distribute the matching binary beside the manifest.
