# Bento Blocks — dedicated GPU reported as integrated graphics

## Symptom

Bento Blocks runs at a fraction of the expected frame rate, often around
20–30 FPS on hardware that should be far above that. Changing the in-game
quality settings does not help.

## Cause

The engine compares the shared memory reported by the GPU with its dedicated
VRAM budget. On machines with 24 GB of RAM or more, the reported shared memory
reaches or exceeds dedicated VRAM, so the engine concludes that the GPU is
"integrated or very old" and clamps its streaming bandwidth to 128 MB/s.

The cause is in the game's GPU detection, not in the driver: the value DXVK
reports is enough to trigger it.

## Fix

DXVK reports 1 GB of shared memory to the engine instead of the full system
RAM. The engine then recognises a dedicated GPU and raises its bandwidth
budget to 512 MB/s.

The configuration only sets one game setting:

```json
"dxvk": { "shared_mb": 1024 }
```

Nothing else is touched: no game file is replaced, no driver setting is
changed, and Proton is not patched. Lapinux stores the previous value and puts
it back when the configuration is removed.

## Applying it

Open the game sheet in Lapinux, go to **Configurations**, then choose
**Install this configuration**. Start the game afterwards; DXVK reads the
value at startup.

To undo it, use **Remove** in the same tab. The original DXVK value is
restored.

You can also set the value by hand in the game settings (`DXVK` card, shared
memory), but the configuration keeps it with the game and is restored
automatically.

## Tested on

| | |
| --- | --- |
| Proton | GE-Proton11-11 |
| GPU | NVIDIA GeForce RTX 4070 |
| RAM | 32 GB |
| Date | 2026-10-31 |
| Result | the engine stops reporting an integrated GPU; frame rate is no longer clamped |

If your machine has less than 24 GB of RAM, this configuration is harmless but
probably unnecessary: try the game once without it first.
