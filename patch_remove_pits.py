"""
Super Mario Bros. (NES) - Accessibility Pit Removal Patch

Makes Super Mario Bros. more accessible for special needs players.
Applies 4 patches and 4 Game Genie codes to the ROM:

1. Pit survival: falling below screen launches Mario upward with springboard velocity (pits = bounce, not death)
2. Timer freeze: NOP the timer digit decrement (timer stays at starting value)
3. Springboard always boosts: default force changed from $F9 to $F4 (max bounce every time)
4. Castle maze auto-correct: teleport Mario to the correct path at each checkpoint (4-4, 7-4, 8-4)

Game Genie codes baked in:
- POAISA: Power up on enemies (touching enemies powers you up instead of hurting you)
- OZTLLX + AATLGZ + SZLIVO: Always stay big (never revert to small Mario)

Usage:
    python patch_remove_pits.py "Super Mario Bros. (World).nes"

The patched ROM is written alongside the original with " - No Pits" appended to the name.
The original ROM is not modified.
"""

import sys
import os
import hashlib


GG_LETTERS = "APZLGITYEOXUKSVN"


def decode_game_genie(code):
    """Decode a 6-letter NES Game Genie code into (cpu_address, value)."""
    code = code.upper()
    if len(code) != 6:
        raise ValueError(f"Expected 6-letter code, got {len(code)}: {code}")
    n = []
    for ch in code:
        idx = GG_LETTERS.find(ch)
        if idx < 0:
            raise ValueError(f"Invalid Game Genie letter '{ch}' in {code}")
        n.append(idx)
    address = (0x8000
               | ((n[3] & 7) << 12)
               | ((n[5] & 7) << 8)
               | ((n[4] & 8) << 8)
               | ((n[2] & 7) << 4)
               | ((n[1] & 8) << 4)
               | (n[4] & 7)
               | (n[3] & 8))
    value = ((n[1] & 7) << 4) | ((n[0] & 8) << 4) | (n[0] & 7) | (n[5] & 8)
    return address, value


def cpu_to_file(cpu_addr):
    """Convert a CPU address ($8000-$FFFF) to iNES file offset."""
    return cpu_addr - 0x8000 + 0x10


def apply_game_genie(data, code, description):
    """Decode and apply a Game Genie code to the ROM data."""
    cpu_addr, value = decode_game_genie(code)
    file_offset = cpu_to_file(cpu_addr)
    old_byte = data[file_offset]
    print(f"  {code}: CPU ${cpu_addr:04X} -> file ${file_offset:04X},"
          f" ${old_byte:02X} -> ${value:02X}  ({description})")
    data = data[:file_offset] + bytes([value]) + data[file_offset + 1:]
    return data


def verify_rom(data):
    """Verify this is a valid SMB1 NES ROM."""
    if len(data) != 40976:
        print(f"ERROR: Unexpected ROM size {len(data)} (expected 40976)")
        return False
    if data[:4] != b'NES\x1a':
        print("ERROR: Not a valid iNES ROM (missing NES header)")
        return False
    if data[4] != 2 or data[5] != 1:
        print(f"ERROR: Unexpected bank count PRG={data[4]} CHR={data[5]} (expected 2,1)")
        return False
    return True


def apply_patch(data, offset, old_byte, new_byte, description):
    """Apply a single byte patch with verification."""
    actual = data[offset]
    if actual != old_byte:
        print(f"  WARNING: At ${offset:04X}, expected ${old_byte:02X} but found ${actual:02X}")
        print(f"  Skipping patch: {description}")
        return data, False
    data = data[:offset] + bytes([new_byte]) + data[offset + 1:]
    print(f"  OK: ${offset:04X}: ${old_byte:02X} -> ${new_byte:02X}  ({description})")
    return data, True


def verify_context(data, offset, expected_bytes, label):
    """Verify surrounding bytes match expected pattern."""
    actual = data[offset:offset + len(expected_bytes)]
    if actual != expected_bytes:
        print(f"  Context check FAILED for {label}:")
        print(f"    Expected: {expected_bytes.hex()}")
        print(f"    Actual:   {actual.hex()}")
        return False
    return True


def main():
    print("=" * 60)
    print("Super Mario Bros. - Accessibility Pit Removal Patch")
    print("=" * 60)
    print()

    # Parse arguments
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(sys.argv[0])} <rom_path>")
        print()
        print("Example:")
        print(f'  python {os.path.basename(sys.argv[0])} "Super Mario Bros. (World).nes"')
        sys.exit(1)

    rom_path = sys.argv[1]
    if not os.path.exists(rom_path):
        print(f"ERROR: ROM not found at {rom_path}")
        sys.exit(1)

    # Build output path: insert " - No Pits" before extension
    base, ext = os.path.splitext(rom_path)
    output_path = f"{base} - No Pits{ext}"

    # Read ROM
    with open(rom_path, 'rb') as f:
        data = f.read()

    print(f"Loaded ROM: {len(data)} bytes")
    md5 = hashlib.md5(data).hexdigest()
    print(f"MD5: {md5}")
    print()

    if not verify_rom(data):
        sys.exit(1)

    patches_applied = 0
    patches_failed = 0

    # ================================================================
    # PATCH 1: Pit survival - early catch with upward boost
    # ================================================================
    print("--- Patch 1: Pit survival (early Y-floor with upward boost) ---")
    # REPLACES the 6-byte death check ($3189) AND the 59-byte death routine ($318F)
    # with 65 bytes of new code ($3189-$31C9). ExitCtrl RTS at $31CA is untouched.
    # CloudExit at $B1BB ($31CB) is also untouched and used for coin heaven exits.
    #
    # When Mario is airborne (State!=0) and moving downward (Y_Speed>=0) in the
    # normal play area (HighPos==1) with Y position >= $C0, apply springboard
    # upward velocity with jump gravity. Checking Y_Speed instead of State==2
    # fixes the bug where jumping into a pit with A held keeps State==1 during
    # the downward arc, bypassing the old State==2 check entirely.
    #
    # Cloud/coin heaven areas (CloudTypeOverride != 0) are excluded — Mario must be
    # able to fall through the bottom to exit coin heaven. When HighPos >= 2 in a
    # cloud area, we JMP to the original CloudExit routine.
    #
    # During i-frames (InjuryTimer != 0), both vertical and horizontal velocity
    # are zeroed instead of boosting. This prevents clipping through bricks
    # (vertical from boost, horizontal from walking through pit walls) while
    # tile collision is disabled.
    #
    # CPU addresses (file offset = CPU - $8000 + $10):
    #   Code start:  CPU $B179 = file $3189
    #   boost:       CPU $B19F = file $31AF
    #   deep_fall:   CPU $B1A9 = file $31B9
    #   df_normal:   CPU $B1AE = file $31BE
    #   hold:        CPU $B1B5 = file $31C5
    #   ExitCtrl:    CPU $B1BA = file $31CA (original RTS, untouched)
    #   CloudExit:   CPU $B1BB = file $31CB (original routine, untouched)
    if verify_context(data, 0x3189, bytes([0xA5, 0xB5, 0xC9, 0x02, 0x30, 0x3B, 0xA2, 0x01]),
                       "PlayerHole: LDA HighPos, CMP #$02, BMI ExitCtrl, LDX #$01"):
        new_code = bytes([
            # --- Check HighPos ---
            0xA5, 0xB5,             # LDA Player_Y_HighPos
            0xC9, 0x02,             # CMP #$02
            0xB0, 0x2A,             # BCS deep_fall            (HighPos >= 2 -> $B1A9)
            0xAA,                   # TAX                      (X = HighPos; Z=1 if 0)
            0xF0, 0x38,             # BEQ ExitCtrl             (HighPos == 0 -> $B1BA)
            # --- HighPos == 1 (normal play area): check if airborne ---
            0xA5, 0x1D,             # LDA Player_State
            0xF0, 0x34,             # BEQ ExitCtrl             (on ground -> $B1BA)
            # --- Check if moving downward (not on upward arc of boost/jump) ---
            0xA5, 0x9F,             # LDA Player_Y_Speed
            0x30, 0x30,             # BMI ExitCtrl             (going up -> $B1BA)
            # --- Cloud area bypass: don't catch falls in coin heaven ---
            0xAD, 0x43, 0x07,       # LDA CloudTypeOverride    ($0743)
            0xD0, 0x2B,             # BNE ExitCtrl             (cloud area -> $B1BA)
            # --- Check if below ground threshold ---
            0xA5, 0xCE,             # LDA Player_Y_Position
            0xC9, 0xC0,             # CMP #$C0
            0x90, 0x25,             # BCC ExitCtrl             (above $C0 -> $B1BA)
            # --- Zero sub-pixel before injury check (shared by boost and hold) ---
            0xA2, 0x00,             # LDX #$00                 (X=0 for STX ops)
            0x8E, 0x33, 0x04,       # STX Player_Y_MoveForce   ($0433, X=0)
            # --- chk_injury: if i-frames active, hold instead of boost ---
            0xAD, 0x9E, 0x07,       # LDA InjuryTimer          ($079E)
            0xD0, 0x16,             # BNE hold                 (i-frames active -> $B1B5)
            # --- boost: set velocity, fix gravity ---
            0xA9, 0xF4,             # LDA #$F4                 (springboard velocity)
            0x85, 0x9F,             # STA Player_Y_Speed
            0xA9, 0x70,             # LDA #$70                 (jump gravity)
            0x8D, 0x0A, 0x07,       # STA VerticalForceDown    ($070A)
            0x60,                   # RTS
            # --- deep_fall: HighPos >= 2 ---
            0xAD, 0x43, 0x07,       # LDA CloudTypeOverride    ($0743)
            0xD0, 0x0D,             # BNE CloudExit            (cloud area -> $B1BB)
            # --- df_normal: reset to play area, zero velocity, return ---
            0x85, 0x9F,             # STA Player_Y_Speed       (A=0, zero velocity)
            0xA9, 0x01,             # LDA #$01
            0x85, 0xB5,             # STA Player_Y_HighPos     (back to page 1)
            0x60,                   # RTS
            # --- hold: i-frames active, freeze Mario in place ---
            0x86, 0x9F,             # STX Player_Y_Speed       (X=0, stop vertical)
            0x86, 0x57,             # STX Player_X_Speed       (X=0, stop horizontal)
            0xEA,                   # NOP (pad; falls through to ExitCtrl RTS)
        ])
        nop_fill = bytes([0xEA] * (65 - len(new_code)))
        data = data[:0x3189] + new_code + nop_fill + data[0x31CA:]
        print(f"  OK: $3189-$31C9: pit survival with cloud area bypass ({len(new_code)} bytes)")
        patches_applied += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 2: Timer freeze - NOP the digit decrement
    # ================================================================
    print()
    print("--- Patch 2: Timer freeze (NOP digit decrement) ---")
    # In RunGameTimer (CPU $B74F), the timer is decremented by storing $FF (-1)
    # into DigitModifier+5 at CPU $B78F: STA $0139 (bytes: $8D $39 $01)
    # NOP these 3 bytes so the timer digit modifier is never set, freezing the timer.
    # This does NOT affect DigitsMathRoutine (shared by scores/coins) — only the
    # timer's -1 input is removed. The timer display still refreshes harmlessly.
    # Context: LDA #$FF ($A9 $FF) before, JSR DigitsMathRoutine ($20 $5F $8F) after
    if verify_context(data, 0x379D, bytes([0xA9, 0xFF, 0x8D, 0x39, 0x01, 0x20, 0x5F, 0x8F]),
                       "RunGameTimer: LDA #$FF, STA DigitModifier+5, JSR DigitsMathRoutine"):
        data = data[:0x379F] + bytes([0xEA, 0xEA, 0xEA]) + data[0x37A2:]
        print(f"  OK: $379F-$37A1: $8D $39 $01 -> $EA $EA $EA  (STA DigitModifier+5 -> NOP NOP NOP)")
        patches_applied += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 3: Springboard always gives max boost
    # ================================================================
    print()
    print("--- Patch 3: Springboard always max boost ---")
    # In ChkForLandJumpSpring (CPU $DEC4), when Mario lands on the springboard,
    # JumpspringForce is initialized to $F9 (low bounce). The player must press A
    # with precise timing during the animation to upgrade it to $F4 (high bounce).
    # Change the default from $F9 to $F4 so the max boost always happens.
    # Context: LDA #$70, STA $0709, LDA #$F9, STA $06DB
    if verify_context(data, 0x5ED9, bytes([0xA9, 0x70, 0x8D, 0x09, 0x07, 0xA9, 0xF9, 0x8D, 0xDB, 0x06]),
                       "ChkForLandJumpSpring: LDA #$70, STA VerticalForce, LDA #$F9, STA JumpspringForce"):
        data, ok = apply_patch(data, 0x5EDF, 0xF9, 0xF4,
                               "JumpspringForce default: $F9 (low bounce) -> $F4 (always max bounce)")
        if ok:
            patches_applied += 1
        else:
            patches_failed += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 4: Castle maze auto-correct
    # ================================================================
    print()
    print("--- Patch 4: Castle maze auto-correct ---")
    # In ProcLoopCommand (CPU $C0CC), castle levels 4-4, 7-4, 8-4 check if Mario
    # is at the correct Y-position at certain page boundaries. Wrong position loops
    # the level back, creating a maze puzzle. This is inaccessible for cognitively
    # impaired players, AND simply disabling the loop causes soft-locks (dead-end paths).
    #
    # Fix: load the correct Y from the table. If the value is safe (< $C0), teleport
    # Mario there and set him on-ground. If the value is dangerous (>= $C0, i.e. 8-4's
    # $F0 entries which are below the floor), skip the teleport entirely — the maze check
    # still passes (no loopback), but Mario stays at his natural position.
    #
    # This works because all 4-4/7-4 table values ($40/$80/$B0) are < $C0 and land in
    # open corridors, while all 8-4 values ($F0) are >= $C0. For 8-4, our pit fill
    # patches ensure all terrain is walkable, so Mario can proceed from any position.
    #
    # Original 13 bytes at CPU $C0EB (file $40FB):
    #   A5 CE       LDA Player_Y_Position
    #   D9 81 C0    CMP $C081,Y           (required Y from table)
    #   D0 23       BNE WrongChk
    #   A5 1D       LDA Player_State
    #   C9 00       CMP #$00
    #   D0 1D       BNE WrongChk
    #
    # New 13 bytes:
    #   B9 81 C0    LDA $C081,Y           (load correct Y from table)
    #   C9 C0       CMP #$C0              (is it at/below floor level?)
    #   B0 06       BCS $C0F8             (>= $C0: skip teleport, fall through to pass)
    #   85 CE       STA Player_Y_Position (teleport Mario to correct path)
    #   A9 00       LDA #$00
    #   85 1D       STA Player_State      (set to on-ground)
    original = bytes([0xA5, 0xCE, 0xD9, 0x81, 0xC0, 0xD0, 0x23,
                      0xA5, 0x1D, 0xC9, 0x00, 0xD0, 0x1D])
    if verify_context(data, 0x40FB, original,
                       "ProcLoopCommand: Y-position check + Player_State check"):
        new_code = bytes([
            0xB9, 0x81, 0xC0,   # LDA $C081,Y  (correct Y from table)
            0xC9, 0xC0,         # CMP #$C0     (at/below floor level?)
            0xB0, 0x06,         # BCS +6       (>= $C0: skip teleport -> $C0F8)
            0x85, 0xCE,         # STA Player_Y_Position (teleport)
            0xA9, 0x00,         # LDA #$00
            0x85, 0x1D,         # STA Player_State (on ground)
        ])
        data = data[:0x40FB] + new_code + data[0x4108:]
        print(f"  OK: $40FB-$4107: maze auto-correct with conditional teleport")
        print(f"       4-4/7-4: teleport to correct path  |  8-4: pass check, no teleport")
        patches_applied += 1
    else:
        patches_failed += 1

    # ================================================================
    # GAME GENIE CODES
    # ================================================================
    print()
    print("--- Game Genie codes ---")
    data = apply_game_genie(data, "POAISA", "Power up on enemies")
    data = apply_game_genie(data, "OZTLLX", "Always stay big (1/3)")
    data = apply_game_genie(data, "AATLGZ", "Always stay big (2/3)")
    data = apply_game_genie(data, "SZLIVO", "Always stay big (3/3)")
    gg_applied = 4
    print(f"  Applied {gg_applied} Game Genie codes")

    # ================================================================
    # Summary and write output
    # ================================================================
    print()
    print("=" * 60)
    print(f"Patches applied: {patches_applied}/4")
    print(f"Patches failed:  {patches_failed}/4")
    print(f"Game Genie codes: {gg_applied}/4")

    if patches_applied == 0:
        print("ERROR: No patches were applied! ROM may be incompatible.")
        sys.exit(1)

    if patches_failed > 0:
        print(f"WARNING: {patches_failed} patch(es) failed. ROM may be partially patched.")

    # Write patched ROM
    with open(output_path, 'wb') as f:
        f.write(data)

    new_md5 = hashlib.md5(data).hexdigest()
    print()
    print(f"Original ROM: {os.path.basename(rom_path)}")
    print(f"Patched ROM:  {os.path.basename(output_path)}")
    print(f"New MD5: {new_md5}")
    print()
    print("What was changed:")
    print("  - Pits are survivable (Mario bounces out with springboard velocity)")
    print("  - Timer is frozen (no time pressure)")
    print("  - Springboard always gives max boost (no precise timing needed)")
    print("  - Castle mazes auto-corrected (Mario teleported to correct path in 4-4, 7-4, 8-4)")
    print("  - Touching enemies powers you up (POAISA)")
    print("  - Mario always stays big (OZTLLX + AATLGZ + SZLIVO)")
    print()
    print("Done! The patched ROM is ready to play.")


if __name__ == "__main__":
    main()
