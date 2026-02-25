"""
Super Mario Bros. (NES) - Accessibility Pit Removal Patch

Removes all pits/holes from the game to make it accessible for special needs players.
Applies 8 patches and 4 Game Genie codes to the ROM:

1. TerrainRenderBits pattern 0: "no floor" -> "2-row floor" (visual floor everywhere)
2. TerrainRenderBits pattern 10: "ceiling only, no floor" -> "ceiling + floor"
3. Hole_Empty subroutine: RTS immediately (holes never remove ground tiles)
4. Hole_Water subroutine: RTS immediately (water holes never remove ground)
5. PlayerHole death -> position reset (if Mario falls, reappear mid-screen instead of dying)
6. Timer freeze: NOP the timer digit decrement (timer stays at starting value)
7. Springboard always boosts: default force changed from $F9 to $F4 (max bounce every time)
8. Castle maze loops disabled: NOP the LoopCommand flag so 4-4, 7-4, 8-4 never loop

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
    # PATCH 1: TerrainRenderBits pattern 0 - add floor
    # ================================================================
    print("--- Patch 1: TerrainRenderBits pattern 0 (no floor -> floor) ---")
    # The table at file offset $13EC starts with: $00 $00 (pattern 0 = no terrain)
    # Change byte 2 from $00 to $18 (adds 2-row floor, matching pattern 1)
    # Context: TerrainMetatiles ($69 $54 $52 $62) immediately before
    if verify_context(data, 0x13E8, bytes([0x69, 0x54, 0x52, 0x62, 0x00, 0x00, 0x00, 0x18]),
                       "TerrainMetatiles + TerrainRenderBits[0..1]"):
        data, ok = apply_patch(data, 0x13ED, 0x00, 0x18,
                               "TerrainRenderBits pattern 0 byte 2: no floor -> 2-row floor")
        if ok:
            patches_applied += 1
        else:
            patches_failed += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 2: TerrainRenderBits pattern 10 - add floor
    # ================================================================
    print()
    print("--- Patch 2: TerrainRenderBits pattern 10 (ceiling, no floor -> ceiling+floor) ---")
    # Pattern 10 is at table offset 20 (0x14): file offset $13EC + $14 = $1400
    # Bytes: $01 $00 -> change $00 to $18
    if verify_context(data, 0x1400, bytes([0x01, 0x00]),
                       "TerrainRenderBits pattern 10"):
        data, ok = apply_patch(data, 0x1401, 0x00, 0x18,
                               "TerrainRenderBits pattern 10 byte 2: no floor -> 2-row floor")
        if ok:
            patches_applied += 1
        else:
            patches_failed += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 3: Hole_Empty subroutine - skip entirely
    # ================================================================
    print()
    print("--- Patch 3: Hole_Empty subroutine (JSR -> RTS, skip hole rendering) ---")
    # HoleMetatiles table at $1B4D: $87 $00 $00 $00
    # Hole_Empty code starts at $1B51 with JSR ChkLrgObjLength ($20 $AC $9B)
    # Change first byte from $20 (JSR) to $60 (RTS) to skip the entire routine
    if verify_context(data, 0x1B4D, bytes([0x87, 0x00, 0x00, 0x00, 0x20, 0xAC, 0x9B]),
                       "HoleMetatiles + Hole_Empty start"):
        data, ok = apply_patch(data, 0x1B51, 0x20, 0x60,
                               "Hole_Empty: JSR $9BAC -> RTS (skip hole rendering)")
        if ok:
            patches_applied += 1
        else:
            patches_failed += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 4: Hole_Water subroutine - skip entirely
    # ================================================================
    print()
    print("--- Patch 4: Hole_Water subroutine (JSR -> RTS, skip water hole rendering) ---")
    # Hole_Water at $1967: JSR ChkLrgObjLength ($20 $AC $9B), then LDA #$86 ($A9 $86)
    if verify_context(data, 0x1967, bytes([0x20, 0xAC, 0x9B, 0xA9, 0x86]),
                       "Hole_Water start"):
        data, ok = apply_patch(data, 0x1967, 0x20, 0x60,
                               "Hole_Water: JSR $9BAC -> RTS (skip water hole rendering)")
        if ok:
            patches_applied += 1
        else:
            patches_failed += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 5: PlayerHole - position reset instead of death
    # ================================================================
    print()
    print("--- Patch 5: PlayerHole death -> position reset ---")
    # At $3189: LDA Player_Y_HighPos, CMP #$02, BMI ExitCtrl
    # The death code runs from $318F to $31C9 (59 bytes) when Mario falls below screen.
    # Replace it with code that resets Mario's position to mid-screen and lets him
    # fall back to the ground, instead of killing him.
    #
    # RAM addresses (confirmed from disassembly cross-references):
    #   $B5   = Player_Y_HighPos    (vertical screen page)
    #   $CE   = Player_Y_Position   (vertical position low byte)
    #   $9F   = Player_Y_Speed      (vertical velocity)
    #   $0433 = Player_Y_MoveForce  (sub-pixel vertical accumulator)
    #   $1D   = Player_State        (0=ground, 1=jump, 2=falling, 3=climbing)
    #   ExitCtrl = CPU $B1BA        (RTS at file offset $31CA)
    if verify_context(data, 0x318F, bytes([0xA2, 0x01, 0x8E, 0x23, 0x07]),
                       "PlayerHole death code: LDX #$01, STX ScrollLock"):
        new_code = bytes([
            0xA9, 0x01,             # LDA #$01
            0x85, 0xB5,             # STA Player_Y_HighPos     (back on screen)
            0xA9, 0x80,             # LDA #$80
            0x85, 0xCE,             # STA Player_Y_Position    (mid-screen)
            0xA9, 0x00,             # LDA #$00
            0x85, 0x9F,             # STA Player_Y_Speed       (zero velocity)
            0x8D, 0x33, 0x04,       # STA Player_Y_MoveForce   (zero sub-pixel)
            0xA9, 0x02,             # LDA #$02
            0x85, 0x1D,             # STA Player_State         (set to falling)
            0x4C, 0xBA, 0xB1,       # JMP ExitCtrl             (resume gameplay)
        ])
        nop_fill = bytes([0xEA] * (59 - len(new_code)))
        data = data[:0x318F] + new_code + nop_fill + data[0x31CA:]
        print(f"  OK: $318F-$31C9: replaced 59-byte death routine with position reset")
        patches_applied += 1
    else:
        patches_failed += 1

    # ================================================================
    # PATCH 6: Timer freeze - NOP the digit decrement
    # ================================================================
    print()
    print("--- Patch 6: Timer freeze (NOP digit decrement) ---")
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
    # PATCH 7: Springboard always gives max boost
    # ================================================================
    print()
    print("--- Patch 7: Springboard always max boost ---")
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
    # PATCH 8: Castle maze loops disabled
    # ================================================================
    print()
    print("--- Patch 8: Castle maze loops disabled ---")
    # In the area object parser (CPU $95DA), when a loop-command object is found,
    # INC $0745 sets the LoopCommand flag. ProcLoopCommand (CPU $C0CC) then checks
    # Mario's Y-position each frame and loops the level back if he's on the wrong path.
    # NOP the INC so the flag is never set — castles 4-4, 7-4, 8-4 play straight through.
    # Context: CMP #$4B ($C9 $4B), BNE +3 ($D0 $03), INC $0745 ($EE $45 $07)
    if verify_context(data, 0x15E6, bytes([0xC9, 0x4B, 0xD0, 0x03, 0xEE, 0x45, 0x07]),
                       "LoopCommand: CMP #$4B, BNE +3, INC $0745"):
        data = data[:0x15EA] + bytes([0xEA, 0xEA, 0xEA]) + data[0x15ED:]
        print(f"  OK: $15EA-$15EC: $EE $45 $07 -> $EA $EA $EA  (INC LoopCommand -> NOP NOP NOP)")
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
    print(f"Patches applied: {patches_applied}/8")
    print(f"Patches failed:  {patches_failed}/8")
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
    print("  - Ground/floor is always present (no gaps in terrain)")
    print("  - Hole objects in level data are ignored (pits never carved out)")
    print("  - Water holes are also ignored")
    print("  - Falling below the screen resets Mario to mid-screen (no death)")
    print("  - Timer is frozen (no time pressure)")
    print("  - Springboard always gives max boost (no precise timing needed)")
    print("  - Castle maze loops disabled (4-4, 7-4, 8-4 play straight through)")
    print("  - Touching enemies powers you up (POAISA)")
    print("  - Mario always stays big (OZTLLX + AATLGZ + SZLIVO)")
    print()
    print("Done! The patched ROM is ready to play.")


if __name__ == "__main__":
    main()
