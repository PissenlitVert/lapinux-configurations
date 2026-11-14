#!/usr/bin/env python3
"""Vérifie les bibliothèques natives du catalogue sans lancer Lapinux.

Pour chaque binaire publié : architecture ELF, empreinte, taille, export du
point d'entrée, version d'ABI annoncée et callbacks attendus (thème ou plugin).
Un thème compilé pour une autre ABI, ou un fichier qui n'est pas un plugin, est
refusé ici plutôt que chez l'utilisateur au moment de l'installation.
"""

from __future__ import annotations

import ctypes
import hashlib
import json
import struct
import sys
from pathlib import Path

#: Version d'ABI que ce dépôt publie (lapinux-plugin-api, HOST_ABI_VERSION).
ABI_SUPPORTED = 6
#: e_machine -> nom d'architecture utilisé dans le catalogue.
MACHINES = {0x3E: "x86_64", 0xB7: "aarch64"}


class Descriptor(ctypes.Structure):
    """Miroir de `lapinux_plugin_api::PluginDescriptor` (repr(C)).

    `u32` puis quatre octets de remplissage avant les pointeurs alignés sur 8.
    """

    _fields_ = [
        ("abi_version", ctypes.c_uint32),
        ("_padding", ctypes.c_uint32),
        ("init", ctypes.c_void_p),
        ("draw", ctypes.c_void_p),
        ("page", ctypes.c_void_p),
        ("theme", ctypes.c_void_p),
        ("theme_frame", ctypes.c_void_p),
        ("home", ctypes.c_void_p),
    ]


def elf_arch(raw: bytes) -> tuple[str, str]:
    if raw[:4] != b"\x7fELF":
        raise ValueError("pas une bibliothèque ELF")
    bits = "64" if raw[4] == 2 else "32"
    machine = struct.unpack("<H", raw[18:20])[0]
    name = MACHINES.get(machine, f"machine-0x{machine:04x}")
    return f"elf{bits}", name


def probe(entry: dict, root: Path, problems: list[str]) -> None:
    binary = entry["binary"]
    path = root / binary["file"]
    if not path.is_file():
        problems.append(f"{entry['id']}: binaire absent ({binary['file']})")
        return
    raw = path.read_bytes()
    if len(raw) != binary["size"]:
        problems.append(f"{entry['id']}: taille {len(raw)} != {binary['size']}")
    if hashlib.sha256(raw).hexdigest() != binary["sha256"]:
        problems.append(f"{entry['id']}: empreinte différente du catalogue")

    _, machine = elf_arch(raw)
    declared = entry.get("arch")
    if declared and declared != "any" and declared != machine:
        problems.append(
            f"{entry['id']}: publié pour {declared}, binaire {machine}"
        )

    try:
        library = ctypes.CDLL(str(path))
    except OSError as error:
        problems.append(f"{entry['id']}: chargement impossible ({error})")
        return
    try:
        entry_point = library.lapinux_plugin_entry
    except AttributeError:
        problems.append(f"{entry['id']}: lapinux_plugin_entry manquant")
        return
    entry_point.restype = ctypes.POINTER(Descriptor)
    entry_point.argtypes = []
    try:
        descriptor = entry_point().contents
    except (ValueError, OSError) as error:
        problems.append(f"{entry['id']}: point d'entrée en échec ({error})")
        return

    if descriptor.abi_version != ABI_SUPPORTED:
        problems.append(
            f"{entry['id']}: ABI {descriptor.abi_version}, "
            f"le dépôt publie l'ABI {ABI_SUPPORTED}"
        )
    declared_abi = entry.get("abi")
    if declared_abi is not None and declared_abi != descriptor.abi_version:
        problems.append(
            f"{entry['id']}: ABI déclarée {declared_abi}, "
            f"binaire {descriptor.abi_version}"
        )

    callbacks = {
        "init": descriptor.init,
        "draw": descriptor.draw,
        "page": descriptor.page,
        "theme": descriptor.theme,
        "theme_frame": descriptor.theme_frame,
        "home": descriptor.home,
    }
    present = [name for name, pointer in callbacks.items() if pointer]
    if entry.get("theme"):
        if not {"theme", "theme_frame"} & set(present):
            problems.append(
                f"{entry['id']}: thème sans callback theme/theme_frame"
            )
    elif not {"draw", "page", "home"} & set(present):
        problems.append(f"{entry['id']}: plugin sans callback draw/page/home")

    print(
        f"{entry['id']}: {machine} · ABI {descriptor.abi_version} · "
        f"{len(raw)} o · {', '.join(present) or 'aucun callback'}"
    )


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent
    catalog_path = root / "catalog.json"
    try:
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"catalog.json illisible : {error}", file=sys.stderr)
        return 1
    problems: list[str] = []
    plugins = catalog.get("plugins", [])
    if not plugins:
        problems.append("le catalogue ne publie aucun plugin")
    for entry in plugins:
        probe(entry, root, problems)
    if problems:
        print("\nProblèmes :", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1
    print(f"{len(plugins)} bibliothèque(s) vérifiée(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
