# Plugin manifests

This directory publishes the TOML manifests of native Lapinux plugins. A
manifest describes the plugin, its translations and the native library it
expects next to it.

For a native plugin, the matching `.so` is published in `plugins/bin/`. The
catalog records its path, size and SHA-256, so Lapinux can download, verify and
install the binary beside the manifest. The validator refuses a native plugin
whose binary is missing.
