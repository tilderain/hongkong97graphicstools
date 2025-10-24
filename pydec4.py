import os
import sys
import json
from PIL import Image

# Add this entire block after your imports
ASSET_MAP = [
    {'address': 0x848600, 'type': 'GRAPHIC'}, {'address': 0x84A725, 'type': 'PALETTE'},
    {'address': 0x84A829, 'type': 'GRAPHIC'}, {'address': 0x84D483, 'type': 'PALETTE'},
    {'address': 0x84D4E7, 'type': 'PALETTE'}, {'address': 0x84D4F3, 'type': 'PALETTE'},
    {'address': 0x84D516, 'type': 'GRAPHIC'}, {'address': 0x8599ED, 'type': 'PALETTE'},
    {'address': 0x859A51, 'type': 'GRAPHIC'}, {'address': 0x85AA58, 'type': 'GRAPHIC'},
    {'address': 0x85AD0D, 'type': 'GRAPHIC'}, {'address': 0x85ECA9, 'type': 'PALETTE'},
    {'address': 0x85ECED, 'type': 'GRAPHIC'}, {'address': 0x868289, 'type': 'GRAPHIC'},
    {'address': 0x8684B5, 'type': 'GRAPHIC'}, {'address': 0x86CB5E, 'type': 'PALETTE'},
    {'address': 0x86CB82, 'type': 'GRAPHIC'}, {'address': 0x87AD76, 'type': 'PALETTE'},
    {'address': 0x87AD9A, 'type': 'GRAPHIC'}, {'address': 0x88827C, 'type': 'PALETTE'},
    {'address': 0x8882A0, 'type': 'GRAPHIC'}, {'address': 0x88DA4D, 'type': 'PALETTE'},
    {'address': 0x88DA71, 'type': 'GRAPHIC'}, {'address': 0x899B7D, 'type': 'PALETTE'},
    {'address': 0x899BA1, 'type': 'GRAPHIC'}, {'address': 0x89D181, 'type': 'PALETTE'},
    {'address': 0x89D1A5, 'type': 'GRAPHIC'}, {'address': 0x8A8C49, 'type': 'PALETTE'},
    {'address': 0x8A8C6D, 'type': 'GRAPHIC'}, {'address': 0x8AECDD, 'type': 'PALETTE'},
    {'address': 0x8AED01, 'type': 'GRAPHIC'}, {'address': 0x8BBC5A, 'type': 'PALETTE'},
    {'address': 0x8BBC7E, 'type': 'GRAPHIC'}, {'address': 0x8BEB25, 'type': 'PALETTE'},
    {'address': 0x8BEB49, 'type': 'GRAPHIC'},
]

# (The DecompressionMismatchError class remains unchanged)
class DecompressionMismatchError(Exception):
    def __init__(self, message, partial_data, mismatch_offset):
        super().__init__(message)
        self.partial_data = partial_data
        self.mismatch_offset = mismatch_offset

# --- DECOMPRESSOR AND UTILITIES (REMAIN UNCHANGED) ---
def decompress_data(compressed_data: bytes, debug=False) -> tuple[bytearray, int]:
    # ... (This function is identical to the one in the prompt, no changes needed) ...
    if len(compressed_data) < 2:
        raise ValueError("Compressed data too short for a size header.")
    decompressed_size = int.from_bytes(compressed_data[0:2], 'little')
    if decompressed_size == 0:
        return bytearray(0), 2
    stream = compressed_data[2:]
    in_ptr = 0
    out_buffer = bytearray(decompressed_size)
    out_ptr = 0
    cmd_count = 0
    while out_ptr < decompressed_size:
        if in_ptr >= len(stream): break
        cmd = stream[in_ptr]; in_ptr += 1
        temp = cmd
        carry = 0
        new_carry = (temp >> 7) & 1; temp = ((temp << 1) & 0xFF) | carry; carry = new_carry
        new_carry = (temp >> 7) & 1; temp = ((temp << 1) & 0xFF) | carry; carry = new_carry
        cmd_stored = temp
        new_carry = (temp >> 7) & 1; temp = ((temp << 1) & 0xFF) | carry
        first_jump = ((temp & 0x03) << 1)
        a_reg = 0
        temp = cmd_stored
        carry = 0
        while True:
            new_carry = (temp >> 7) & 1; temp = ((temp << 1) & 0xFF) | carry; carry = new_carry
            if not carry: break
            a_reg += 2
        second_jump = a_reg
        if debug and cmd_count < 10: print(f"  CMD {cmd_count}: 0x{cmd:02X} -> first_jump={first_jump}, second_jump={second_jump}, out_ptr={out_ptr}")
        cmd_count += 1
        length = 0
        copy_src = 0
        try:
            if first_jump == 0:
                length, offset = (cmd & 0x03) + 3, cmd >> 2
                copy_src = out_ptr - (offset + 1)
            elif first_jump == 2:
                length = (cmd & 0x03) + 3
                offset = (((cmd >> 2) & 0x0F) << 8) | stream[in_ptr]; in_ptr += 1
                copy_src = out_ptr - (offset + 1)
            elif first_jump == 4:
                length = ((cmd >> 2) & 0x0F) + 7
                offset = ((cmd & 0x03) << 8) | stream[in_ptr]; in_ptr += 1
                copy_src = out_ptr - (offset + 1)
            elif first_jump == 6:
                if second_jump == 0:
                    b1 = stream[in_ptr]; in_ptr += 1
                    b2 = stream[in_ptr]; in_ptr += 1
                    len_val_low_nibble = cmd & 0x0F
                    len_val_high_nibble = (b1 >> 4) & 0x0F
                    len_val_bit_8 = (cmd >> 4) & 0x01
                    length_val = (len_val_bit_8 << 8) | (len_val_high_nibble << 4) | len_val_low_nibble
                    length = length_val + 7
                    offset = ((b1 & 0x0F) << 8) | b2
                    copy_src = out_ptr - (offset + 1)
                elif second_jump == 2:
                    length = (cmd & 0x0F) + 1
                    actual_len = min(length, decompressed_size - out_ptr, len(stream) - in_ptr)
                    out_buffer[out_ptr:out_ptr+actual_len] = stream[in_ptr:in_ptr+actual_len]
                    out_ptr += actual_len; in_ptr += actual_len
                    length = 0
                elif second_jump >= 4:
                    len_high = cmd & 0x03
                    b1 = stream[in_ptr]; in_ptr += 1
                    temp_len = b1 + 0x11
                    if temp_len > 0xFF: len_high += 1
                    length = (len_high << 8) | (temp_len & 0xFF)
                    actual_len = min(length, decompressed_size - out_ptr, len(stream) - in_ptr)
                    out_buffer[out_ptr:out_ptr+actual_len] = stream[in_ptr:in_ptr+actual_len]
                    out_ptr += actual_len; in_ptr += actual_len
                    length = 0
            else: raise ValueError(f"Unknown command type: first={first_jump}")
            if length > 0:
                for _ in range(min(length, decompressed_size - out_ptr)):
                    if copy_src < 0: out_buffer[out_ptr] = 0xFF
                    else: out_buffer[out_ptr] = out_buffer[copy_src]
                    out_ptr += 1
                    copy_src += 1
        except IndexError: raise RuntimeError(f"Unexpected end of stream at in_ptr=0x{in_ptr:X}, out_ptr=0x{out_ptr:X}")
        except Exception as e: raise RuntimeError(f"Error at in_ptr=0x{in_ptr:X}, out_ptr=0x{out_ptr:X}: {e}") from e
    compressed_size_read = in_ptr + 2
    return out_buffer[:decompressed_size], compressed_size_read

def snes_palette_to_rgba(palette_data: bytes) -> list[tuple[int, int, int, int]]:
    # ... (This function is identical to the one in the prompt, no changes needed) ...
    rgba_palette = []
    for i in range(0, len(palette_data), 2):
        color_val = int.from_bytes(palette_data[i:i+2], 'little')
        r = (color_val & 0x1F)
        g = (color_val >> 5) & 0x1F
        b = (color_val >> 10) & 0x1F
        r_8bit = (r << 3) | (r >> 2)
        g_8bit = (g << 3) | (g >> 2)
        b_8bit = (b << 3) | (b >> 2)
        rgba_palette.append((r_8bit, g_8bit, b_8bit, 255))
    return rgba_palette

def snes_4bpp_to_rgba(snes_data: bytes, palette: list[tuple[int, int, int, int]], tiles_per_row: int = 16) -> tuple[bytes, tuple[int, int]]:
    # ... (This function is identical to the one in the prompt, no changes needed) ...
    num_tiles = len(snes_data) // 32
    if num_tiles == 0: return b'', (0, 0)
    image_width = tiles_per_row * 8
    num_tile_rows = (num_tiles + tiles_per_row - 1) // tiles_per_row
    image_height = num_tile_rows * 8
    rgba_data = bytearray(image_width * image_height * 4)
    for tile_idx in range(num_tiles):
        tile_data = snes_data[tile_idx * 32 : (tile_idx + 1) * 32]
        if len(tile_data) < 32: continue
        base_tile_x = (tile_idx % tiles_per_row) * 8
        base_tile_y = (tile_idx // tiles_per_row) * 8
        for y_in_tile in range(8):
            bp0, bp1 = tile_data[y_in_tile*2], tile_data[y_in_tile*2+1]
            bp2, bp3 = tile_data[16+y_in_tile*2], tile_data[16+y_in_tile*2+1]
            for x_in_tile in range(8):
                bit = 7 - x_in_tile
                color_index = (((bp3>>bit)&1)<<3) | (((bp2>>bit)&1)<<2) | (((bp1>>bit)&1)<<1) | ((bp0>>bit)&1)
                color = palette[color_index % len(palette)]
                px, py = base_tile_x + x_in_tile, base_tile_y + y_in_tile
                if py < image_height and px < image_width:
                    idx = (py * image_width + px) * 4
                    rgba_data[idx:idx+4] = color
    return bytes(rgba_data), (image_width, image_height)

def save_snes_4bpp_as_png(snes_data: bytes, output_filename: str, palette: list, tiles_per_row: int):
    # ... (This function is identical to the one in the prompt, no changes needed) ...
    if not snes_data:
        print(f"    Warning: No data to save for '{output_filename}'. Skipping.")
        return
    try:
        rgba_pixels, (width, height) = snes_4bpp_to_rgba(snes_data, palette, tiles_per_row=tiles_per_row)
        if width == 0 or height == 0: raise ValueError("Image has zero dimensions.")
        img = Image.frombytes('RGBA', (width, height), rgba_pixels)
        img.save(output_filename)
        print(f"    -> Saved image to '{output_filename}'")
    except Exception as e:
        print(f"    -> Error saving PNG '{output_filename}': {e}")

def lorom_to_file_offset(snes_addr: int) -> int:
    # ... (This function is identical to the one in the prompt, no changes needed) ...
    bank = snes_addr >> 16
    addr_in_bank = snes_addr & 0xFFFF
    if not (0x80 <= bank <= 0xBF and 0x8000 <= addr_in_bank <= 0xFFFF):
         print(f"    Warning: Address 0x{snes_addr:06X} is outside the standard LoROM mapping area.")
    return ((bank - 0x80) * 0x8000) + (addr_in_bank - 0x8000)


def main():
    if len(sys.argv) < 2:
        print("Usage: python pydec3.py <path_to_hongkong97.smc>")
        sys.exit(1)

    rom_path = sys.argv[1]
    output_dir = "decompressed_pngs_color"
    
    palette_map = {}
    map_path = 'palette_map.json'
    if os.path.isfile(map_path):
        with open(map_path, 'r') as f:
            palette_map = json.load(f)
        print(f"Loaded '{map_path}' for explicit palette mapping.")
    else:
        print(f"Warning: '{map_path}' not found. Using fallback palette logic only.")

    if not os.path.isfile(rom_path):
        print(f"Error: ROM file not found at '{rom_path}'")
        sys.exit(1)
        
    file_size = os.path.getsize(rom_path)
    header_offset = 512 if file_size % 1024 == 512 else 0
    if header_offset > 0:
        print(f"Detected 512-byte header, adjusting offsets.")

    os.makedirs(output_dir, exist_ok=True)

    asset_type_map = {f"{item['address']:06x}": item['type'] for item in ASSET_MAP}
    offsets_hex = sorted(asset_type_map.keys())

    print("\n--- PASS 1: Decompressing and Classifying Data ---")
    palettes = {}
    graphics = {}
    
    with open(rom_path, 'rb') as f:
        for hex_str in offsets_hex:
            try:
                snes_address = int(hex_str, 16)
                file_offset = lorom_to_file_offset(snes_address) + header_offset
                f.seek(file_offset)
                compressed_chunk = f.read(65536)
                data, compressed_size = decompress_data(compressed_chunk)
                asset_type = asset_type_map.get(hex_str)

                if asset_type == 'PALETTE':
                    if len(data) > 0:
                        palettes[hex_str] = snes_palette_to_rgba(data)
                        print(f"  0x{hex_str}: Identified as PALETTE (Compressed: {compressed_size} bytes -> Decompressed: {len(data)} bytes)")
                    else:
                        print(f"  0x{hex_str}: Identified as PALETTE but decompressed to 0 bytes. Skipping.")
                elif asset_type == 'GRAPHIC':
                    if len(data) > 0:
                        graphics[hex_str] = data
                        print(f"  0x{hex_str}: Identified as GRAPHIC (Compressed: {compressed_size} bytes -> Decompressed: {len(data)} bytes)")
                    else:
                        print(f"  0x{hex_str}: Identified as GRAPHIC but decompressed to 0 bytes. Skipping.")
                else:
                    print(f"  0x{hex_str}: Warning - Not in ASSET_MAP. (Decompressed: {len(data)} bytes)")
            except Exception as e:
                print(f"  0x{hex_str}: FAILED to decompress - {e}")

    print("\n--- PASS 2: Generating PNGs with Associated Palettes ---")
    grayscale_palette = [(i * 17, i * 17, i * 17, 255) for i in range(16)]
    
    if not graphics:
        print("No graphics files were successfully decompressed. Exiting.")
        return

    sorted_palette_offsets = sorted(palettes.keys())

    # --- MODIFIED: Define special widths here ---
    special_width_map = {"859a51", "848600", "85eced"}

    for hex_str, graphic_data in sorted(graphics.items()):
        snes_addr_hex_fmt = f"0x{int(hex_str, 16):06X}"

        # --- MODIFIED: Determine the correct width for this graphic ---
        tiles_per_row = 16 if hex_str in special_width_map else 32

        if snes_addr_hex_fmt in palette_map:
            print(f"Processing graphic 0x{hex_str} with explicit palette map (width={tiles_per_row*8}px):")
            map_entry = palette_map[snes_addr_hex_fmt]
            palette_addr_hex = map_entry['palette_address']
            palette_key = palette_addr_hex[2:].lower()

            if palette_key not in palettes:
                print(f"  -> ERROR: Mapped palette 0x{palette_key} not found or failed decompression. Skipping.")
                continue

            full_palette = palettes[palette_key]
            for line_num in map_entry['palette_lines']:
                print(f"  -> Applying palette 0x{palette_key}, line {line_num}")
                start_idx, end_idx = line_num * 16, (line_num + 1) * 16
                
                if start_idx >= len(full_palette):
                    print(f"    Warning: Line {line_num} is out of bounds for palette 0x{palette_key} (size: {len(full_palette)} colors). Skipping.")
                    continue
                
                palette_slice = full_palette[start_idx:end_idx]
                while len(palette_slice) < 16:
                    palette_slice.append((0, 0, 0, 255))

                output_path = os.path.join(output_dir, f"graphic_{hex_str}_pal_{palette_key}_line{line_num}.png")
                # --- MODIFIED: Use the determined width ---
                save_snes_4bpp_as_png(graphic_data, output_path, palette_slice, tiles_per_row=tiles_per_row)
        else:
            print(f"Processing graphic 0x{hex_str} with fallback palette search (width={tiles_per_row*8}px):")
            best_palette_key = None
            for p_key in sorted_palette_offsets:
                if p_key < hex_str:
                    best_palette_key = p_key
                else:
                    break
            
            palette_to_use = grayscale_palette
            if best_palette_key:
                palette_to_use = palettes[best_palette_key][:16]
                print(f"  -> Applying palette from 0x{best_palette_key}")
            else:
                print("  -> No preceding palette found. Using grayscale fallback.")
            
            output_path = os.path.join(output_dir, f"graphic_{hex_str}.png")
            # --- MODIFIED: Use the determined width ---
            save_snes_4bpp_as_png(graphic_data, output_path, palette_to_use, tiles_per_row=tiles_per_row)

    print("\n-------------------------------------")
    print(f"Batch processing complete. Check the '{output_dir}' folder.")

if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("Error: The 'Pillow' library is required. Please install it with: pip install Pillow")
        sys.exit(1)
    
    main()
