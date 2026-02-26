# SMB1 No Pits - Accessibility Patch

A Python script that patches **Super Mario Bros. (NES)** to make the game more accessible for special needs players. Fills all pits with ground, adds a safety-net bounce for any remaining falls, freezes the timer, auto-solves castle mazes, and bakes in Game Genie codes for power-up-on-enemies and always-stay-big.

The original file is not modified — a new patched ROM is created.

## Usage

```
python patch_remove_pits.py "Super Mario Bros. (World).nes"
```

Outputs a patched ROM with `- No Pits` appended to the filename.

## What It Does

| Patch | Offset | Size | Effect |
|-------|--------|------|--------|
| 1 | `$13ED` | 1 byte | Terrain pattern "no floor" now renders 2-row ground |
| 2 | `$1401` | 1 byte | Terrain pattern "ceiling only" now includes floor |
| 3 | `$1B51` | 1 byte | `Hole_Empty` returns immediately (ground never carved out) |
| 4 | `$1967` | 1 byte | `Hole_Water` returns immediately (water pits removed) |
| 5 | `$3189` | 65 bytes | Pit survival: bounce out with springboard velocity |
| 6 | `$379F` | 3 bytes | Timer frozen (digit decrement NOPed) |
| 7 | `$5EDF` | 1 byte | Springboard always gives max boost |
| 8 | `$40FB` | 13 bytes | Castle maze auto-solved (4-4, 7-4 teleport; 8-4 pass-through) |

**Patches 1-4: Pit removal.** Pits in SMB1 are created through three independent mechanisms — terrain patterns that omit floor tiles, and hole objects that carve ground out. Patches 1-2 change the "no floor" and "ceiling only" terrain patterns to always include ground. Patches 3-4 change the `Hole_Empty` and `Hole_Water` subroutines from `JSR` (call) to `RTS` (return immediately), so they never remove ground tiles.

**Patch 5: Pit survival.** Safety net for any fall that gets past the pit fill (e.g. pushed through floor by a moving platform). Replaces the original 65-byte `PlayerHole` death check and death routine with new 6502 code that:

- Detects Mario falling below Y=$C0 in the normal play area (HighPos=1) while airborne and moving downward
- Applies springboard upward velocity ($F4) with jump gravity ($70) to launch him out of the pit
- During i-frames (after getting hit), freezes Mario in place instead of boosting — zeroes both vertical and horizontal speed plus the sub-pixel accumulator to prevent clipping through pit walls or floor while tile collision is disabled
- Bypasses cloud/coin heaven areas (`CloudTypeOverride != 0`) so Mario can fall through the bottom to exit bonus areas normally
- If Mario somehow reaches HighPos >= 2 (full screen below), resets him to the play area; in cloud areas, jumps to the original `CloudExit` routine instead

**Patch 6: Timer freeze.** NOPs the `STA DigitModifier+5` instruction in `RunGameTimer`, removing the -1 fed into `DigitsMathRoutine` each tick. The timer display never changes. Scores and coin counts are unaffected.

**Patch 7: Springboard always max boost.** Changes the default `JumpspringForce` from `$F9` (low bounce) to `$F4` (max bounce). Every springboard gives a full boost regardless of button timing.

**Patch 8: Castle maze auto-correct.** Worlds 4-4, 7-4, and 8-4 have branching paths where only one continues forward. Instead of checking Mario's Y-position against a lookup table, this patch loads the table value and checks if it's safe (< $C0). For 4-4 and 7-4 (table values $40/$80/$B0), Mario is teleported to the correct corridor. For 8-4 (table values $F0, which are below the floor in patched terrain), the teleport is skipped — the maze check still passes (no loopback), but Mario stays at his natural position. The pit fill patches ensure all 8-4 terrain is walkable from any position.

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

## References

- [SMB1 Disassembly (doppelganger)](https://gist.github.com/1wErt3r/4048722)
- [SMB1 Disassembly (Xkeeper0)](https://github.com/Xkeeper0/smb1)
- [Super Mario Bros. ROM Map - Data Crystal](https://datacrystal.tcrf.net/wiki/Super_Mario_Bros.:ROM_map)

## License

MIT
