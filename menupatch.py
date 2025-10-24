import os

# --- Configuration ---
SOURCE_ROM = "hongkong97_font_patched.smc"
PATCHED_ROM = "cavestory97-ogsong.smc"

# --- Address Definitions ---
# Address where the game reads/stores the language choice. This is our hijack point.
HIJACK_ADDRESS = 0x80BCA0
# A safe "code cave" location before the SNES interrupt vectors at the end of the bank.
# The original address 0x80FFF0 overwrote the NMI and Reset vectors, causing crashes.
CODE_CAVE_ADDRESS = 0x80FFD0

# --- Byte Definitions ---
# The original 6 bytes we are overwriting (lda $0640, sta $1252)
ORIGINAL_HIJACK_BYTES = b'\xAD\x40\x06\x8D\x52\x12'

# Our new hijack code: JMP to the code cave, padded with NOPs.
# 4C D0 FF = JMP $FFD0 (within the current bank $80)
PATCHED_HIJACK_BYTES = b'\x4C\xD0\xFF\xEA\xEA\xEA'

# Our custom logic to be written into the code cave. It is 15 bytes long.
# Assembly Translation:
#   lda $0640       ; Load the player's menu choice
#   cmp #$01        ; Is the choice Chinese?
#   bne IS_NOT_CHINESE ; If not, skip the next instruction
#   lda #$02        ; If yes, change the choice to English
# IS_NOT_CHINESE:
#   sta $1252       ; Store the (potentially modified) choice
#   jmp $BCA6       ; Jump back to the normal code flow
CODE_CAVE_LOGIC = bytes([
    0xAD, 0x40, 0x06,  # lda $0640
    0xC9, 0x01,        # cmp #$01
    0xD0, 0x02,        # bne +2 bytes
    0xA9, 0x02,        # lda #$02
    0x8D, 0x52, 0x12,  # sta $1252
    0x4C, 0xA6, 0xBC,  # jmp $BCA6
])

# --- Utility Functions ---
def lorom_to_fileoffset(snes_address: int) -> int:
    return ((snes_address >> 16) & 0x7F) * 0x8000 + (snes_address & 0x7FFF)

def detect_header_size(rom_path: str) -> int:
    try:
        return 512 if os.path.getsize(rom_path) % 1024 == 512 else 0
    except FileNotFoundError:
        return 0

# --- Main Script Logic ---
def create_patched_rom():
    if not os.path.exists(SOURCE_ROM):
        print(f"Error: Source ROM file '{SOURCE_ROM}' not found.")
        return

    try:
        print(f"Reading source ROM: '{SOURCE_ROM}'...")
        rom_data = bytearray(open(SOURCE_ROM, "rb").read())

        header_offset = detect_header_size(SOURCE_ROM)
        print(f"Detected a {header_offset}-byte header." if header_offset else "No header detected.")
            
        hijack_offset = lorom_to_fileoffset(HIJACK_ADDRESS) + header_offset
        cave_offset = lorom_to_fileoffset(CODE_CAVE_ADDRESS) + header_offset

        print(f"Hijack point file offset: 0x{hijack_offset:06X}")
        print(f"Code cave file offset:    0x{cave_offset:06X} (safe area before interrupt vectors)")

        # 1. Verify the original code at the hijack point
        if rom_data[hijack_offset : hijack_offset + len(ORIGINAL_HIJACK_BYTES)] != ORIGINAL_HIJACK_BYTES:
            print("\nError: The bytes at the hijack location do not match what's expected.")
            print("The ROM may be a different version or already patched. Aborting.")
            return
        
        # 2. Apply the patches in memory
        print("Original code verified. Applying patches...")
        
        # Write the JMP instruction to the hijack point
        rom_data[hijack_offset : hijack_offset + len(PATCHED_HIJACK_BYTES)] = PATCHED_HIJACK_BYTES
        print(f"- Hijack JMP instruction written to 0x{hijack_offset:06X}.")
        
        # Write our new logic into the code cave
        rom_data[cave_offset : cave_offset + len(CODE_CAVE_LOGIC)] = CODE_CAVE_LOGIC
        print(f"- Custom logic written to code cave at 0x{cave_offset:06X}.")

        # 3. Write the modified data to the new file
        print(f"\nWriting patched ROM to '{PATCHED_ROM}'...")
        with open(PATCHED_ROM, "wb") as patched_file:
            patched_file.write(rom_data)
        
        print(f"Success! Patched ROM saved as '{PATCHED_ROM}'.")
        print("FIX: Moved code cave to avoid overwriting SNES interrupt vectors, which was causing crashes.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    create_patched_rom()
