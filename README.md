# SMB1 No Pits - Accessibility Patch

A Python script that patches **Super Mario Bros. (NES)** to remove all pits and holes, making the game more accessible for special needs players. Also bakes in Game Genie codes for power-up-on-enemies and always-stay-big.

Changes 4 bytes, replaces one 59-byte routine, NOPs the timer decrement, and applies 4 Game Genie codes. The original file is not modified.

## Usage

```
python patch_remove_pits.py "Super Mario Bros. (World).nes"
```

Outputs a patched ROM with `- No Pits` appended to the filename.

## What It Does

Pits in SMB1 are created through three independent mechanisms. This patch neutralizes all of them:

| Patch | Offset | Change | Mechanism |
|-------|--------|--------|-----------|
| 1 | `$13ED` | `$00`->`$18` | Terrain pattern "no floor" now renders 2-row ground |
| 2 | `$1401` | `$00`->`$18` | Terrain pattern "ceiling only" now includes floor |
| 3 | `$1B51` | `$20`->`$60` | `Hole_Empty` routine returns immediately (ground never carved out) |
| 4 | `$1967` | `$20`->`$60` | `Hole_Water` routine returns immediately (water pits removed) |
| 5 | `$318F` | 59 bytes | `PlayerHole` death routine replaced with position reset |
| 6 | `$379F` | 3 bytes NOP | Timer digit decrement removed (timer frozen) |

**Patches 1-2** ensure the base terrain always includes ground tiles, even when level data or mid-level commands set the floor pattern to "empty."

**Patches 3-4** prevent hole objects from removing ground tiles. The `Hole_Empty` and `Hole_Water` 6502 subroutines have their first instruction changed from `JSR` (call subroutine) to `RTS` (return immediately), so they do nothing.

**Patch 5** replaces the pit death routine with a position reset. If Mario somehow falls below the screen (e.g. pushed through the floor by a moving platform), instead of dying he reappears mid-screen and falls back to the ground. The 59-byte death routine is replaced with 22 bytes of new 6502 code that resets `Player_Y_HighPos`, `Player_Y_Position`, `Player_Y_Speed`, `Player_Y_MoveForce`, and `Player_State`.

**Patch 6** freezes the level timer by NOPing the `STA DigitModifier+5` instruction in `RunGameTimer`. This removes the -1 that the timer routine feeds into `DigitsMathRoutine` each tick, so the timer display never changes. Scores and coin counts are unaffected because `DigitsMathRoutine` itself is not modified.

## Game Genie Codes

The script also bakes in four Game Genie codes, decoded and applied directly to the ROM:

| Code | CPU Address | File Offset | Effect |
|------|-------------|-------------|--------|
| POAISA | `$D885` | `$5895` | Power up on enemies (touching enemies powers you up) |
| OZTLLX | `$B263` | `$3273` | Always stay big (1/3) |
| AATLGZ | `$B264` | `$3274` | Always stay big (2/3) |
| SZLIVO | `$D936` | `$5946` | Always stay big (3/3) |

The OZTLLX + AATLGZ + SZLIVO combination prevents Mario from reverting to small form when hit.

## How It Works

Each patch is verified before application — the script checks surrounding bytes to confirm it found the correct location. If a context check fails, that patch is skipped with a warning.

The script validates:
- iNES header magic bytes
- ROM size (40,976 bytes: 16-byte header + 32KB PRG + 8KB CHR)
- PRG/CHR bank counts (2 PRG, 1 CHR = NROM mapper)

## Compatibility

Tested with `Super Mario Bros. (World).nes`. Other regional variants (Japan, Europe) may have different byte offsets — the context verification will catch any mismatch.

## Roadmap

- ~~**Stop timer**: Freeze the level timer so there's no time pressure~~ Done (Patch 6)
- **Springboard always boosts**: Make the trampoline/springboard always give a full boost jump instead of requiring precise timing

## References

- [SMB1 Disassembly (doppelganger)](https://gist.github.com/1wErt3r/4048722)
- [SMB1 Disassembly (Xkeeper0)](https://github.com/Xkeeper0/smb1)
- [Super Mario Bros. ROM Map - Data Crystal](https://datacrystal.tcrf.net/wiki/Super_Mario_Bros.:ROM_map)

## License

MIT
