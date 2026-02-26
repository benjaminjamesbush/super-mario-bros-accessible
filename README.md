# 🍄 SMB1 Accessibility Patch

A Python script that patches **Super Mario Bros. (NES)** to make the game more accessible for special needs players. Bounces Mario out of pits instead of dying, freezes the timer, maxes out springboards, auto-solves castle mazes, and bakes in Game Genie codes for power-up-on-enemies and always-stay-big.

## ❤️ Why This Exists

Super Mario Bros. is one of the best games to hand to a first-time player with intellectual disabilities. The controls are a d-pad and two buttons. The levels go left to right. The visual language is clear — coins are good, pipes go somewhere, the flag at the end means you made it. It runs on inexpensive retro handhelds, and nearly everyone recognizes it.

The ideal experience for this audience is casual and exploratory: walk to the right, jump sometimes, enjoy the music and the graphics and the variety of 32 different levels. Not a test of skill — just a pleasant walk through a colorful world.

But unmodified SMB1 doesn't let that experience happen. Bottomless pits and enemies both kill Mario and force the player to restart — and a player who doesn't think to avoid Goombas will walk into every single one. The timer kills Mario after 400 ticks — a sudden death with no obvious visible cause. Springboards require precisely timed button presses. Castle mazes loop endlessly without the right path memorized. Each of these is a source of frustration. For a player with intellectual disabilities, that frustration can mean the difference between engagement and abandonment.

This patch removes those frustrations. Mario bounces out of pits instead of dying, the timer stays frozen, springboards always give a full boost, castle mazes solve themselves, and enemies become fun collectables that power Mario up on contact. He still runs, jumps, collects coins, enters pipes, and progresses through all 32 levels. The world is the same — it's just safe to explore.

While there are many well-known Game Genie codes for Super Mario Bros., their effects can be unpredictable and frequently lead to soft locks. This patch has been extensively tested and iteratively refined to ensure a stable, playable experience across all 32 levels.

Pairing the patched ROM with a device that has arcade-style controls — like the Powkiddy A13 — can further increase accessibility for players with fine motor control challenges. A full-sized joystick and large buttons are easier to use than a small d-pad and tiny face buttons.

## 🕹️ Usage

```
python patch_smb1_accessible.py "Super Mario Bros. (World).nes"
```

Outputs a patched ROM with `- Accessible` appended to the filename. The original file is not modified.

## 🔧 What It Does

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

## 🧞 Game Genie Codes

The script also bakes in four Game Genie codes, decoded and applied directly to the ROM:

| Code | CPU Address | File Offset | Effect |
|------|-------------|-------------|--------|
| POAISA | `$D885` | `$5895` | Power up on enemies (touching enemies powers you up) |
| OZTLLX | `$B263` | `$3273` | Always stay big (1/3) |
| AATLGZ | `$B264` | `$3274` | Always stay big (2/3) |
| SZLIVO | `$D936` | `$5946` | Always stay big (3/3) |

Power-up-on-enemies alone doesn't make Mario invincible — fire bars and hammers still injure him. The OZTLLX + AATLGZ + SZLIVO combination prevents Mario from reverting to small form when hit, so the two codes together make him effectively invincible.

## ⚙️ How It Works

Each patch is verified before application — the script checks surrounding bytes to confirm it found the correct location. If a context check fails, that patch is skipped with a warning.

The script validates:
- iNES header magic bytes
- ROM size (40,976 bytes: 16-byte header + 32KB PRG + 8KB CHR)
- PRG/CHR bank counts (2 PRG, 1 CHR = NROM mapper)

## ✅ Compatibility

Tested with `Super Mario Bros. (World).nes`. Other regional variants (Japan, Europe) may have different byte offsets — the context verification will catch any mismatch.

## 📚 References

- [SMB1 Disassembly (doppelganger)](https://gist.github.com/1wErt3r/4048722)
- [SMB1 Disassembly (Xkeeper0)](https://github.com/Xkeeper0/smb1)
- [Super Mario Bros. ROM Map - Data Crystal](https://datacrystal.tcrf.net/wiki/Super_Mario_Bros.:ROM_map)

## 📬 Contact

If you have concerns, questions, or want to discuss anything related to accessibility and gaming, reach out directly at benjaminjamesbush@gmail.com.

## ⚖️ Disclaimer

This project is not affiliated with or endorsed by Nintendo. Super Mario Bros. is a trademark of Nintendo. No copyrighted material is distributed — the patch script modifies a ROM image that the user must supply.

## 🤝 Acknowledgements

This patch was developed in collaboration with [Claude Code](https://claude.ai/claude-code).

## 📄 License

[Unlicense](https://unlicense.org/) — public domain.
