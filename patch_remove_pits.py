"""
Super Mario Bros. (NES) - Accessibility Pit Removal Patch

Removes all pits/holes from the game to make it accessible for special needs players.
Applies 4 patches (4 bytes changed) to the ROM:

1. TerrainRenderBits pattern 0: "no floor" -> "2-row floor" (visual floor everywhere)
2. TerrainRenderBits pattern 10: "ceiling only, no floor" -> "ceiling + floor"
3. Hole_Empty subroutine: RTS immediately (holes never remove ground tiles)
4. Hole_Water subroutine: RTS immediately (water holes never remove ground)

Usage:
    python patch_remove_pits.py "Super Mario Bros. (World).nes"

The patched ROM is written alongside the original with " - No Pits" appended to the name.
The original ROM is not modified.
"""

import sys
import os
import hashlib


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
    # Summary and write output
    # ================================================================
    print()
    print("=" * 60)
    print(f"Patches applied: {patches_applied}/4")
    print(f"Patches failed:  {patches_failed}/4")

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
    print()
    print("Done! The patched ROM is ready to play.")


if __name__ == "__main__":
    main()
