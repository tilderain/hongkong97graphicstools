import os
import sys
from PIL import Image
import json
import traceback

# --- DATA STRUCTURES (Unchanged) ---
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

# --- HELPER FUNCTIONS ---
def find_closest_palette(graphic_address: int, asset_map: list) -> int | None:
    palettes = [item['address'] for item in asset_map if item['type'] == 'PALETTE']
    if not palettes: return None
    closest_palette, min_distance = None, float('inf')
    for pal_addr in palettes:
        distance = abs(graphic_address - pal_addr)
        if distance < min_distance: min_distance, closest_palette = distance, pal_addr
    return closest_palette

def lorom_to_file_offset(snes_addr: int) -> int:
    bank, addr_in_bank = snes_addr >> 16, snes_addr & 0xFFFF
    return ((bank - 0x80) * 0x8000) + (addr_in_bank - 0x8000)

# --- PNG CONVERTER (New flexible version) ---
def png_to_snes_data(image_path: str, target_size: int = None) -> tuple[bytes, bytes]:
    """
    Converts a PNG to SNES 4bpp tile data and palette data.
    - If image is RGBA, extracts up to 16 unique colors.
    - If image is Indexed (Mode 'P'), extracts the entire color table.
    """
    img = Image.open(image_path)
    width, height = img.size
    if width % 8 != 0 or height % 8 != 0: raise ValueError(f"Image dimensions must be multiples of 8. Got {width}x{height}")
    
    palette_list_rgb = []
    
    if img.mode == 'P':
        print("  -> Indexed PNG detected. Extracting full palette.")
        raw_palette = img.getpalette()
        for i in range(0, len(raw_palette), 3):
            palette_list_rgb.append(tuple(raw_palette[i:i+3]))
        # The image is already indexed, so we can use the pixel values directly.
        pixels = img.load()
        get_color_index = lambda x, y: pixels[x, y]
    else:
        print("  -> RGBA PNG detected. Extracting up to 16 colors.")
        img = img.convert('RGBA')
        pixels = img.load()
        color_set = {pixels[x, y][:3] for y in range(height) for x in range(width)}
        if len(color_set) > 16: print(f"  Warning: Image has {len(color_set)} colors. Reducing to 16.")
        palette_list_rgb = sorted(list(color_set))[:16]
        while len(palette_list_rgb) < 16: palette_list_rgb.append((0, 0, 0))
        color_to_index = {color: idx for idx, color in enumerate(palette_list_rgb)}
        get_color_index = lambda x, y: color_to_index.get(pixels[x, y][:3], 0)

    palette_data = bytearray()
    for r, g, b in palette_list_rgb:
        r5, g5, b5 = r >> 3, g >> 3, b >> 3
        color_val = (b5 << 10) | (g5 << 5) | r5
        palette_data.extend(color_val.to_bytes(2, 'little'))

    tile_data = bytearray()
    for tile_y in range(height // 8):
        for tile_x in range(width // 8):
            base_x, base_y = tile_x * 8, tile_y * 8
            tile_bytes = bytearray(32)
            for y_in_tile in range(8):
                bp0, bp1, bp2, bp3 = 0, 0, 0, 0
                for x_in_tile in range(8):
                    color_idx = get_color_index(base_x + x_in_tile, base_y + y_in_tile)
                    bit_pos = 7 - x_in_tile
                    bp0 |= ((color_idx >> 0) & 1) << bit_pos; bp1 |= ((color_idx >> 1) & 1) << bit_pos
                    bp2 |= ((color_idx >> 2) & 1) << bit_pos; bp3 |= ((color_idx >> 3) & 1) << bit_pos
                tile_bytes[y_in_tile * 2] = bp0; tile_bytes[y_in_tile * 2 + 1] = bp1
                tile_bytes[16 + y_in_tile * 2] = bp2; tile_bytes[16 + y_in_tile * 2 + 1] = bp3
            tile_data.extend(tile_bytes)

    if target_size is not None:
        if len(tile_data) < target_size: tile_data.extend(bytes(target_size - len(tile_data)))
        elif len(tile_data) > target_size: tile_data = tile_data[:target_size]
    
    return bytes(tile_data), bytes(palette_data)

# --- COMPRESSOR (The fast rfind() version) ---
def compress_data(data: bytes) -> bytes:
    if len(data) > 0xFFFF: raise ValueError("Data too large to compress")
    compressed = bytearray(len(data).to_bytes(2, 'little'))
    output_buffer, literal_buffer = bytearray(), bytearray()
    pos = 0
    def flush_literals():
        nonlocal literal_buffer
        if not literal_buffer: return
        lit_pos = 0
        while lit_pos < len(literal_buffer):
            chunk_size = min(16, len(literal_buffer) - lit_pos)
            cmd = 0xE0 | ((chunk_size - 1) & 0x0F)
            compressed.append(cmd)
            chunk_data = literal_buffer[lit_pos:lit_pos + chunk_size]
            compressed.extend(chunk_data); output_buffer.extend(chunk_data)
            lit_pos += chunk_size
        literal_buffer.clear()
    while pos < len(data):
        best_match_len, best_match_pos = 0, -1
        if len(output_buffer) >= 3 and pos + 3 <= len(data):
            search_start = max(0, len(output_buffer) - 4095)
            search_pattern = data[pos:pos+3]
            current_search_end = len(output_buffer)
            while current_search_end > search_start:
                check_pos = output_buffer.rfind(search_pattern, search_start, current_search_end)
                if check_pos == -1: break
                match_len = 3
                max_len = min(263, len(data) - pos, len(output_buffer) - check_pos)
                while match_len < max_len and output_buffer[check_pos + match_len] == data[pos + match_len]:
                    match_len += 1
                if match_len > best_match_len:
                    best_match_len, best_match_pos = match_len, check_pos
                    if best_match_len >= 263: break
                current_search_end = check_pos
        if best_match_len >= 3:
            final_offset = (len(output_buffer) + len(literal_buffer)) - best_match_pos - 1
            can_be_encoded = ((best_match_len <= 6 and final_offset <= 1023) or
                              (7 <= best_match_len <= 22 and final_offset <= 1023) or
                              (7 <= best_match_len <= 263 and final_offset <= 4095))
            if can_be_encoded:
                flush_literals()
                offset = len(output_buffer) - best_match_pos - 1
                if best_match_len <= 6 and offset <= 15:
                    cmd = (offset << 2) | ((best_match_len - 3) & 0x03)
                    compressed.append(cmd)
                elif best_match_len <= 6 and offset <= 1023:
                    cmd = 0x40 | ((best_match_len - 3) & 0x03) | (((offset >> 8) & 0x0F) << 2)
                    compressed.extend([cmd, offset & 0xFF])
                elif best_match_len <= 22 and offset <= 1023:
                    cmd = 0x80 | (((best_match_len - 7) & 0x0F) << 2) | ((offset >> 8) & 0x03)
                    compressed.extend([cmd, offset & 0xFF])
                elif best_match_len <= 263 and offset <= 4095:
                    length_val = best_match_len - 7
                    cmd = 0xC0 | (length_val & 0x0F)
                    if length_val >= 256: cmd |= 0x10
                    b1 = ((length_val & 0xF0)) | ((offset >> 8) & 0x0F)
                    compressed.extend([cmd, b1, offset & 0xFF])
                copy_src_start = len(output_buffer) - offset - 1
                output_buffer.extend(output_buffer[copy_src_start + i] for i in range(best_match_len))
                pos += best_match_len
                continue
        literal_buffer.append(data[pos]); pos += 1
        if len(literal_buffer) >= 16: flush_literals()
    flush_literals()
    return bytes(compressed)

# --- MAIN INJECTION LOGIC (The proven blind-overwrite method) ---
def main():
    if len(sys.argv) < 4 or sys.argv[1] != '--batch':
        print("Usage: python pyenc5.py --batch <json_file> <rom_path> [output_path]"); sys.exit(1)
    json_path, rom_path = sys.argv[2], sys.argv[3]
    output_path = sys.argv[4] if len(sys.argv) > 4 else f"{os.path.splitext(rom_path)[0]}_modified.smc"
    
    # REMOVED: palette_map.json logic. It is the source of the instability.
    
    print(f"Loading ROM '{rom_path}'...")
    with open(rom_path, 'rb') as f: rom_data = bytearray(f.read())
    
    header_offset = 512 if len(rom_data) % 1024 == 512 else 0
    if header_offset: print("Detected 512-byte header.")
    
    with open(json_path, 'r') as f: config = json.load(f)

    for item in config.get("graphics", []):
        try:
            print("\n" + "="*50 + f"\nProcessing: {item['image_path']}")
            image_path = item['image_path']
            if not os.path.isfile(image_path): print(f"  -> ERROR: Not found: '{image_path}'. Skipping."); continue
            
            snes_address = int(item['snes_address'], 16)
            
            # 1. Convert image to data using the new flexible function
            tile_data, palette_data = png_to_snes_data(image_path, target_size=item.get('target_size'))
            
            # 2. Compress both data blocks
            print("Compressing data...")
            compressed_tiles = compress_data(tile_data)
            compressed_palette = compress_data(palette_data)
            
            # 3. Inject Palette (Safe "Blind Overwrite")
            palette_address = int(item['palette_address'], 16) if item.get('palette_address') else find_closest_palette(snes_address, ASSET_MAP)
            if palette_address:
                pal_file_offset = lorom_to_file_offset(palette_address) + header_offset
                print(f"  -> Injecting palette ({len(compressed_palette)} bytes) at file offset 0x{pal_file_offset:X}")
                rom_data[pal_file_offset : pal_file_offset + len(compressed_palette)] = compressed_palette
            else:
                print("  -> WARNING: No palette address found. Skipping palette injection.")

            # 4. Inject Graphic (Safe "Blind Overwrite")
            file_offset = lorom_to_file_offset(snes_address) + header_offset
            print(f"  -> Injecting graphic ({len(compressed_tiles)} bytes) at file offset 0x{file_offset:X}")
            rom_data[file_offset : file_offset + len(compressed_tiles)] = compressed_tiles
            print(f"  -> SUCCESS: Injected '{image_path}' at 0x{snes_address:06X}")

        except (KeyError, ValueError, RuntimeError) as e:
            print(f"Skipping item due to error: {e}"); traceback.print_exc()

    print("\n" + "="*50 + f"\nAll injections complete. Writing to '{output_path}'...")
    with open(output_path, 'wb') as f: f.write(rom_data)
    print("Successfully created modified ROM.")

if __name__ == "__main__":
    try: from PIL import Image
    except ImportError: print("Error: Pillow is required. `pip install Pillow`"); sys.exit(1)
    main()
