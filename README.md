# SMB1 Accessibility Patch

A Python script that patches **Super Mario Bros. (NES)** to make the game more accessible for special needs players. Bounces Mario out of pits instead of dying, freezes the timer, auto-solves castle mazes, and bakes in Game Genie codes for power-up-on-enemies and always-stay-big.

The original file is not modified — a new patched ROM is created.

## Usage

```
python patch_smb1_accessible.py "Super Mario Bros. (World).nes"
```

Outputs a patched ROM with `- Accessible` appended to the filename.

## What It Does

| Patch | Offset | Size | Effect |
|-------|--------|------|--------|
| 1 | `$3189` | 65 bytes | Pit survival: bounce out with springboard velocity |
| 2 | `$379F` | 3 bytes | Timer frozen (digit decrement NOPed) |
| 3 | `$5EDF` | 1 byte | Springboard always gives max boost |
| 4 | `$40FB` | 13 bytes | Castle maze auto-solved (4-4, 7-4 teleport; 8-4 pass-through) |

**Patch 1: Pit survival.** Safety net that replaces the original `PlayerHole` death routine with new 6502 code. Instead of dying when falling into a pit, Mario bounces out:

- Detects Mario falling below Y=$C0 in the normal play area (HighPos=1) while airborne and moving downward
- Applies springboard upward velocity ($F4) with jump gravity ($70) to launch him out of the pit
- During i-frames (after getting hit), freezes Mario in place instead of boosting — zeroes both vertical and horizontal speed plus the sub-pixel accumulator to prevent clipping through pit walls or floor while tile collision is disabled
- Bypasses cloud/coin heaven areas (`CloudTypeOverride != 0`) so Mario can fall through the bottom to exit bonus areas normally
- If Mario somehow reaches HighPos >= 2 (full screen below), resets him to the play area; in cloud areas, jumps to the original `CloudExit` routine instead

**Patch 2: Timer freeze.** NOPs the `STA DigitModifier+5` instruction in `RunGameTimer`, removing the -1 fed into `DigitsMathRoutine` each tick. The timer display never changes. Scores and coin counts are unaffected.

**Patch 3: Springboard always max boost.** Changes the default `JumpspringForce` from `$F9` (low bounce) to `$F4` (max bounce). Every springboard gives a full boost regardless of button timing.

**Patch 4: Castle maze auto-correct.** Worlds 4-4, 7-4, and 8-4 have branching paths where only one continues forward. Instead of checking Mario's Y-position against a lookup table, this patch loads the table value and checks if it's safe (< $C0). For 4-4 and 7-4 (table values $40/$80/$B0), Mario is teleported to the correct corridor. For 8-4 (table values $F0, which are below the floor), the teleport is skipped — the maze check still passes (no loopback), but Mario stays at his natural position.

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
