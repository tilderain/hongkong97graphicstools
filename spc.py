import os

import os

# --- Configuration ---
# Your original, unmodified game ROM file (e.g., 'hongkong97.smc').
ROM_ORIGINAL_FILE = 'cavestory97-ogsong.smc'
# The new BRR sample you want to insert.
BRR_REPLACEMENT_FILE = 'carly6.brr'
# The name of the new, patched ROM file that will be created.
ROM_OUTPUT_FILE = 'cavestory97.smc'
# --- Technical Details ---
INJECTION_OFFSET = 0x78e9e
MAX_BRR_SIZE = 24750
BRR_BLOCK_SIZE = 9
# --- End of Configuration ---

def main():
    """
    Injects a BRR file into a ROM, ensuring the final block has the
    correct END and LOOP flags set for reliable playback.
    """
    print("--- BRR-Aware SNES ROM Injector ---")

    # 1. Read the original ROM file
    try:
        with open(ROM_ORIGINAL_FILE, 'rb') as f:
            patched_rom_data = bytearray(f.read())
        print(f"[OK] Read {len(patched_rom_data)} bytes from '{ROM_ORIGINAL_FILE}'")
    except FileNotFoundError:
        print(f"[ERROR] Original ROM file not found: '{ROM_ORIGINAL_FILE}'")
        return

    # 2. Read the replacement BRR file
    try:
        with open(BRR_REPLACEMENT_FILE, 'rb') as f:
            brr_data = bytearray(f.read()) # Read into a modifiable bytearray
        initial_brr_size = len(brr_data)
        print(f"[OK] Read {initial_brr_size} bytes from '{BRR_REPLACEMENT_FILE}'")
    except FileNotFoundError:
        print(f"[ERROR] Replacement BRR file not found: '{BRR_REPLACEMENT_FILE}'")
        return

    # 3. Prepare the final BRR payload
    payload = bytearray(MAX_BRR_SIZE) # Create an empty block of the target size

    # Determine the actual data size to use, truncated to a 9-byte boundary
    if initial_brr_size > MAX_BRR_SIZE:
        print(f"[INFO] BRR file is too large ({initial_brr_size} bytes). Truncating...")
        usable_size = (MAX_BRR_SIZE // BRR_BLOCK_SIZE) * BRR_BLOCK_SIZE
    else:
        usable_size = (initial_brr_size // BRR_BLOCK_SIZE) * BRR_BLOCK_SIZE
    
    print(f"[INFO] Final BRR data size will be {usable_size} bytes.")
    
    # Copy the usable part of the BRR data into our payload buffer
    payload[:usable_size] = brr_data[:usable_size]

    # --- THIS IS THE CRITICAL FIX ---
    if usable_size > 0:
        # Go to the header of the *new last block*
        last_block_header_index = usable_size - BRR_BLOCK_SIZE
        
        # Get the current header value
        header_byte = payload[last_block_header_index]
        
        # Force the END and LOOP flags to be set (binary ...11)
        # We use a bitwise OR with 0x03 to set the last two bits to 1
        # without disturbing the filter and shift settings.
        modified_header_byte = header_byte | 0x03
        
        # Write the corrected header back into our payload
        payload[last_block_header_index] = modified_header_byte
        
        print(f"[OK] Patched final BRR block header at index {last_block_header_index} from 0x{header_byte:02X} to 0x{modified_header_byte:02X}.")
    # --- END OF FIX ---

    # 4. Safety check the injection point
    if INJECTION_OFFSET + MAX_BRR_SIZE > len(patched_rom_data):
        print("[FATAL ERROR] The injection point is outside the bounds of the ROM file!")
        return

    # 5. Perform the injection
    print(f"[INFO] Injecting {len(payload)} bytes into ROM at file offset 0x{INJECTION_OFFSET:X}...")
    end_offset = INJECTION_OFFSET + MAX_BRR_SIZE
    patched_rom_data[INJECTION_OFFSET:end_offset] = payload

    # 6. Write the new, patched ROM file to disk
    try:
        with open(ROM_OUTPUT_FILE, 'wb') as f:
            f.write(patched_rom_data)
        print(f"\n[SUCCESS] Successfully created patched ROM: '{ROM_OUTPUT_FILE}'!")
    except IOError as e:
        print(f"[ERROR] Could not write to file '{ROM_OUTPUT_FILE}': {e}")

if __name__ == '__main__':
    main()
