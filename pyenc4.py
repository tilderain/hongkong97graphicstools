import os
import sys
from PIL import Image
import json
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

def find_closest_palette(graphic_address: int, asset_map: list) -> int | None:
    """
    Find the palette address closest to a given graphic address.
    
    Args:
        graphic_address: The SNES address of the graphic.
        asset_map: A list of dictionaries, where each dict has 'address' and 'type'.
    
    Returns:
        The integer address of the closest palette, or None if no palettes are found.
    """
    palettes = [item['address'] for item in asset_map if item['type'] == 'PALETTE']
    
    if not palettes:
        return None
        
    closest_palette = None
    min_distance = float('inf')
    
    for pal_addr in palettes:
        distance = abs(graphic_address - pal_addr)
        if distance < min_distance:
            min_distance = distance
            closest_palette = pal_addr
            
    return closest_palette
def lorom_to_file_offset(snes_addr: int) -> int:
    """Convert SNES LoROM address to file offset."""
    bank = snes_addr >> 16
    addr_in_bank = snes_addr & 0xFFFF
    if not (0x80 <= bank <= 0xBF and 0x8000 <= addr_in_bank <= 0xFFFF):
        print(f"    Warning: Address 0x{snes_addr:06X} is outside the standard LoROM mapping area.")
    return ((bank - 0x80) * 0x8000) + (addr_in_bank - 0x8000)


def rgba_to_snes_4bpp(image_path: str, target_size: int = None) -> tuple[bytes, bytes]:
    """
    Convert a PNG image to SNES 4bpp tile data and extract a 16-color palette.
    Returns (tile_data, palette_data)
    
    Args:
        image_path: Path to the PNG image
        target_size: If specified, pad or truncate tile data to this size
    """
    img = Image.open(image_path).convert('RGBA')
    width, height = img.size
    
    # Ensure dimensions are multiples of 8
    if width % 8 != 0 or height % 8 != 0:
        raise ValueError(f"Image dimensions must be multiples of 8. Got {width}x{height}")
    
    pixels = img.load()
    
    # Extract unique colors and create palette (limit to 16 colors)
    color_set = set()
    for y in range(height):
        for x in range(width):
            color_set.add(pixels[x, y][:3])  # RGB only
    
    if len(color_set) > 16:
        print(f"Warning: Image has {len(color_set)} colors. Will be reduced to 16.")
    
    # Create palette (sorted for consistency)
    palette_list = sorted(list(color_set))[:16]
    while len(palette_list) < 16:
        palette_list.append((0, 0, 0))  # Pad with black
    
    # Create color to index mapping
    color_to_index = {color: idx for idx, color in enumerate(palette_list)}
    
    # Convert palette to SNES BGR555 format
    palette_data = bytearray()
    for r, g, b in palette_list:
        # Convert 8-bit to 5-bit
        r5 = r >> 3
        g5 = g >> 3
        b5 = b >> 3
        # SNES format: 0BBBBBGGGGGRRRRR
        color_val = (b5 << 10) | (g5 << 5) | r5
        palette_data.extend(color_val.to_bytes(2, 'little'))
    
    # Convert image to tiles
    tiles_per_row = width // 8
    tiles_per_col = height // 8
    tile_data = bytearray()
    
    for tile_y in range(tiles_per_col):
        for tile_x in range(tiles_per_row):
            base_x = tile_x * 8
            base_y = tile_y * 8
            
            # Create one 8x8 tile (32 bytes in 4bpp format)
            tile_bytes = bytearray(32)
            
            for y_in_tile in range(8):
                bp0, bp1, bp2, bp3 = 0, 0, 0, 0
                
                for x_in_tile in range(8):
                    px_x = base_x + x_in_tile
                    px_y = base_y + y_in_tile
                    
                    pixel_color = pixels[px_x, px_y][:3]
                    color_idx = color_to_index.get(pixel_color, 0)
                    
                    bit_pos = 7 - x_in_tile
                    bp0 |= ((color_idx >> 0) & 1) << bit_pos
                    bp1 |= ((color_idx >> 1) & 1) << bit_pos
                    bp2 |= ((color_idx >> 2) & 1) << bit_pos
                    bp3 |= ((color_idx >> 3) & 1) << bit_pos
                
                # Store bitplanes for this row
                tile_bytes[y_in_tile * 2] = bp0
                tile_bytes[y_in_tile * 2 + 1] = bp1
                tile_bytes[16 + y_in_tile * 2] = bp2
                tile_bytes[16 + y_in_tile * 2 + 1] = bp3
            
            tile_data.extend(tile_bytes)
    
    # Pad or truncate to target size if specified
    if target_size is not None:
        if len(tile_data) < target_size:
            print(f"  Padding tile data from {len(tile_data)} to {target_size} bytes")
            tile_data.extend(bytes(target_size - len(tile_data)))
        elif len(tile_data) > target_size:
            print(f"  Truncating tile data from {len(tile_data)} to {target_size} bytes")
            tile_data = tile_data[:target_size]
    
    return bytes(tile_data), bytes(palette_data)


def compress_data(data: bytes, debug: bool = False) -> bytes:
    """
    Compress data using the SNES compression format with simple LZ77 back-references.
    Uses only non-overlapping matches for guaranteed correctness.
    """
    if len(data) > 0xFFFF:
        raise ValueError("Data too large to compress (max 65535 bytes)")

    compressed = bytearray()
    compressed.extend(len(data).to_bytes(2, 'little'))

    output_buffer = bytearray()
    pos = 0
    literal_buffer = bytearray()
    cmd_count = 0

    def flush_literals():
        """Flush any pending literal data."""
        nonlocal literal_buffer, output_buffer, cmd_count
        if not literal_buffer:
            return

        lit_pos = 0
        while lit_pos < len(literal_buffer):
            chunk_size = min(16, len(literal_buffer) - lit_pos)
            cmd = 0xE0 | ((chunk_size - 1) & 0x0F)
            compressed.append(cmd)
            chunk_data = literal_buffer[lit_pos:lit_pos + chunk_size]
            compressed.extend(chunk_data)

            start_out = len(output_buffer)
            output_buffer.extend(chunk_data)
            end_out = len(output_buffer)

            if debug and ((start_out < 100) or (start_out >= 720 and start_out <= 750) or (end_out >= 720 and end_out <= 750)):
                print(f"  CMD {cmd_count} @ out={start_out}->{end_out}: Literal {chunk_size} bytes")
            cmd_count += 1

            lit_pos += chunk_size

        literal_buffer.clear()

    while pos < len(data):
        best_match_len = 0
        best_match_pos = -1

        # Search for non-overlapping matches in output buffer
        if len(output_buffer) >= 3 and pos + 3 <= len(data):
            # Widen search window to max supported offset for better compression
            search_start = max(0, len(output_buffer) - 4095)
            
            for check_pos in range(len(output_buffer) - 1, search_start - 1, -1):
                # Quick first-byte check
                if output_buffer[check_pos] != data[pos]:
                    continue
                
                # Count matching bytes
                match_len = 0
                max_len = min(263, len(data) - pos, len(output_buffer) - check_pos)
                
                while match_len < max_len and output_buffer[check_pos + match_len] == data[pos + match_len]:
                    match_len += 1
                
                # Update best match
                if match_len > best_match_len:
                    best_match_len = match_len
                    best_match_pos = check_pos
                    
                    # Early exit for max length matches
                    if best_match_len >= 263:
                        break
        
        # A match is only potentially useful if its length is at least 3
        if best_match_len >= 3:
            # Calculate the final offset that WOULD be used if we commit to this match.
            # This accounts for any pending literal bytes that will be written first.
            final_offset = (len(output_buffer) + len(literal_buffer)) - best_match_pos - 1

            # Check if this match, with its final_offset, can be encoded by any command.
            can_be_encoded = False
            if best_match_len <= 6 and final_offset <= 1023: # Covers Type 0 (offset <= 15) and Type 2
                can_be_encoded = True
            elif best_match_len >= 7 and best_match_len <= 22 and final_offset <= 1023: # Type 4
                can_be_encoded = True
            elif best_match_len >= 7 and best_match_len <= 263 and final_offset <= 4095: # Type 6
                can_be_encoded = True

            if can_be_encoded:
                # The match is good and can be encoded. Commit to it.
                flush_literals()
                
                # The final offset is now the actual offset.
                best_match_offset = len(output_buffer) - best_match_pos - 1
                
                if debug and (len(output_buffer) < 100 or (len(output_buffer) >= 720 and len(output_buffer) <= 750)):
                    start_out = len(output_buffer)
                    end_out = start_out + best_match_len
                    print(f"  CMD {cmd_count} @ out={start_out}: Back-ref len={best_match_len}, offset={best_match_offset}, pos={best_match_pos}")
                cmd_count += 1
                
                # Emit the back-reference command
                if best_match_len <= 6 and best_match_offset <= 15:
                    cmd = (best_match_offset << 2) | ((best_match_len - 3) & 0x03)
                    compressed.append(cmd)
                elif best_match_len <= 6 and best_match_offset <= 1023:
                    offset_high = (best_match_offset >> 8) & 0x0F
                    offset_low = best_match_offset & 0xFF
                    cmd = 0x40 | ((best_match_len - 3) & 0x03) | (offset_high << 2)
                    compressed.append(cmd)
                    compressed.append(offset_low)
                elif best_match_len <= 22 and best_match_offset <= 1023:
                    offset_high = (best_match_offset >> 8) & 0x03
                    offset_low = best_match_offset & 0xFF
                    cmd = 0x80 | (((best_match_len - 7) & 0x0F) << 2) | offset_high
                    compressed.append(cmd)
                    compressed.append(offset_low)
                elif best_match_len <= 263 and best_match_offset <= 4095:
                    length_val = best_match_len - 7
                    cmd = 0xC0 | (length_val & 0x0F)
                    if length_val >= 256:
                        cmd |= 0x10
                    offset_high = (best_match_offset >> 8) & 0x0F
                    offset_low = best_match_offset & 0xFF
                    b1 = ((length_val & 0xF0)) | offset_high
                    compressed.append(cmd)
                    compressed.append(b1)
                    compressed.append(offset_low)
                
                # Add the matched bytes to output buffer to be used for future matches
                copy_src_start = len(output_buffer) - best_match_offset - 1
                for i in range(best_match_len):
                    output_buffer.append(output_buffer[copy_src_start + i])
                
                pos += best_match_len
                continue # Restart the loop for the next position

        # If we reach here, either no match was found or it couldn't be encoded.
        # Treat the current byte as a literal.
        literal_buffer.append(data[pos])
        pos += 1
        
        # Flush if buffer is full
        if len(literal_buffer) >= 16:
            flush_literals()

    flush_literals()

    if debug:
        print(f"  Final: output={len(output_buffer)}, expected={len(data)}, compressed={len(compressed)}")
        print(f"  Input pos reached: {pos}")
    
    # Final check
    if len(output_buffer) != len(data):
        print(f"Warning: Final output buffer size ({len(output_buffer)}) does not match input data size ({len(data)}).")

    return bytes(compressed)


def decompress_data(compressed_data: bytes, debug=False) -> bytearray:
    """Decompress data using the SNES decompression algorithm."""
    if len(compressed_data) < 2:
        raise ValueError("Compressed data too short for a size header.")
    decompressed_size = int.from_bytes(compressed_data[0:2], 'little')
    if decompressed_size == 0:
        raise ValueError("Decompressed size is zero.")
    stream = compressed_data[2:]
    in_ptr = 0
    out_buffer = bytearray(decompressed_size)
    out_ptr = 0
    cmd_count = 0
    while out_ptr < decompressed_size:
        if in_ptr >= len(stream): break
        cmd = stream[in_ptr]; in_ptr += 1
        
        # Decode command byte
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
        
        if debug and cmd_count < 10:
            print(f"  CMD {cmd_count}: 0x{cmd:02X} -> first_jump={first_jump}, second_jump={second_jump}, out_ptr={out_ptr}")
        cmd_count += 1
        
        length = 0
        copy_src = 0
        try:
            if first_jump == 0:
                length, offset = (cmd & 0x03) + 3, cmd >> 2
                copy_src = out_ptr - (offset + 1)
                if debug and cmd_count <= 10:
                    print(f"    Type 0: length={length}, offset={offset}, copy_src={copy_src}")
            elif first_jump == 2:
                length = (cmd & 0x03) + 3
                offset = (((cmd >> 2) & 0x0F) << 8) | stream[in_ptr]; in_ptr += 1
                copy_src = out_ptr - (offset + 1)
                if debug and cmd_count <= 10:
                    print(f"    Type 2: length={length}, offset={offset}, copy_src={copy_src}")
            elif first_jump == 4:
                length = ((cmd >> 2) & 0x0F) + 7
                offset = ((cmd & 0x03) << 8) | stream[in_ptr]; in_ptr += 1
                copy_src = out_ptr - (offset + 1)
                if debug and cmd_count <= 10:
                    print(f"    Type 4: length={length}, offset={offset}, copy_src={copy_src}")
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
                    if debug and cmd_count <= 10:
                        print(f"    Type 6-0: length={length}, offset={offset}, copy_src={copy_src}")
                elif second_jump == 2:
                    length = (cmd & 0x0F) + 1
                    actual_len = min(length, decompressed_size - out_ptr, len(stream) - in_ptr)
                    if debug and cmd_count <= 10:
                        print(f"    Type 6-2 (LITERAL): length={length}, copying from in_ptr={in_ptr}")
                        print(f"      Data: {stream[in_ptr:in_ptr+actual_len].hex()}")
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
                    if debug and cmd_count <= 10:
                        print(f"    Type 6-4+ (LONG LITERAL): length={length}")
                    out_buffer[out_ptr:out_ptr+actual_len] = stream[in_ptr:in_ptr+actual_len]
                    out_ptr += actual_len; in_ptr += actual_len
                    length = 0
            else: raise ValueError(f"Unknown command type: first={first_jump}")
            if length > 0:
                for _ in range(min(length, decompressed_size - out_ptr)):
                    # Emulate SNES open bus behavior for invalid reads (before the buffer starts)
                    if copy_src < 0:
                        out_buffer[out_ptr] = 0xFF
                    else:
                        out_buffer[out_ptr] = out_buffer[copy_src]
                    out_ptr += 1
                    copy_src += 1
        except IndexError:
            raise RuntimeError(f"Unexpected end of stream at in_ptr=0x{in_ptr:X}, out_ptr=0x{out_ptr:X}")
        except Exception as e:
            raise RuntimeError(f"Error at in_ptr=0x{in_ptr:X}, out_ptr=0x{out_ptr:X}: {e}") from e
    return out_buffer[:decompressed_size]


def verify_compression(original_data: bytes, compressed_data: bytes, verbose: bool = False) -> bool:
    """
    Verify that compression works by decompressing and comparing.
    Returns True if data matches, False otherwise.
    """
    try:
        decompressed = decompress_data(compressed_data, debug=False)
        
        if len(decompressed) != len(original_data):
            print(f"  ⚠ Length mismatch: original={len(original_data)}, decompressed={len(decompressed)}")
            return False
        
        mismatch_count = 0
        first_mismatch = -1
        for i in range(len(original_data)):
            if original_data[i] != decompressed[i]:
                if first_mismatch == -1:
                    first_mismatch = i
                if mismatch_count < 5:  # Only show first 5 mismatches
                    print(f"  ⚠ Data mismatch at byte {i}: original=0x{original_data[i]:02X}, decompressed=0x{decompressed[i]:02X}")
                mismatch_count += 1
        
        if mismatch_count > 0:
            print(f"  ⚠ Total mismatches: {mismatch_count}")
            if verbose and first_mismatch > 0:
                print(f"\n  Context around first mismatch (byte {first_mismatch}):")
                start = max(0, first_mismatch - 10)
                end = min(len(original_data), first_mismatch + 10)
                print(f"    Original [{start}:{end}]: {original_data[start:end].hex()}")
                print(f"    Decompressed [{start}:{end}]: {bytes(decompressed[start:end]).hex()}")
            return False
        
        print(f"  ✓ Compression verified! Original: {len(original_data)} bytes → Compressed: {len(compressed_data)} bytes ({100*len(compressed_data)/len(original_data):.1f}%)")
        return True
    except Exception as e:
        print(f"  ⚠ Decompression failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def inject_compressed_graphic(rom_data: bytearray, image_path: str, snes_address: int, target_size: int = None, match_original_compressed_size: bool = False, palette_address: int = None) -> bytearray:
    """
    Inject a PNG image into a SNES ROM bytearray at the specified address.
    
    Args:
        rom_data: The ROM data as a mutable bytearray.
        image_path: Path to the PNG image to inject.
        snes_address: SNES address to write to (e.g., 0x84D516).
        target_size: Target decompressed size in bytes (will pad/truncate tile data).
        match_original_compressed_size: If True, read the original compressed size and pad to match.
        palette_address: If specified, also inject the palette at this address.
        
    Returns:
        The modified rom_data bytearray.
    """
    # Detect header
    file_size = len(rom_data)
    header_offset = 512 if file_size % 1024 == 512 else 0
    if header_offset > 0:
        print(f"Detected 512-byte header, adjusting offsets.")
    
    # Convert PNG to SNES format
    print(f"Converting '{image_path}' to SNES 4bpp format...")
    tile_data, palette_data = rgba_to_snes_4bpp(image_path, target_size=target_size)
    print(f"  Tile data: {len(tile_data)} bytes, Palette data: {len(palette_data)} bytes")
    
    # Inject palette if address specified
    if palette_address is not None:
        print(f"Compressing and injecting palette at 0x{palette_address:06X}...")
        compressed_palette = compress_data(palette_data)
        palette_file_offset = lorom_to_file_offset(palette_address) + header_offset
        rom_data[palette_file_offset:palette_file_offset + len(compressed_palette)] = compressed_palette
        print(f"  Palette injected at file offset 0x{palette_file_offset:X}")
    
    # Compress the tile data
    print("Compressing tile data...")
    compressed_data = compress_data(tile_data, debug=False)
    print(f"  Compressed size: {len(compressed_data)} bytes")
    
    # Verify compression
    print("Verifying compression...")
    if not verify_compression(tile_data, compressed_data, verbose=True):
        raise ValueError("Compression verification failed!")
    
    # Calculate file offset
    file_offset = lorom_to_file_offset(snes_address) + header_offset
    print(f"Injecting graphic at SNES address 0x{snes_address:06X} (file offset 0x{file_offset:X})...")
    
    # Check if we have enough space
    if file_offset + len(compressed_data) > len(rom_data):
        raise ValueError(f"Not enough space in ROM! Need {len(compressed_data)} bytes at offset 0x{file_offset:X}")
    
    # Inject the compressed data
    rom_data[file_offset:file_offset + len(compressed_data)] = compressed_data
    
    return rom_data


def main():
    if len(sys.argv) < 3:
        # (Usage instructions remain the same)
        print("Usage (Single Mode): python pyenc4.py <rom_path> <image_path> [snes_address] [options...]")
        print("Usage (Batch Mode):  python pyenc4.py --batch <json_file> <rom_path> [output_path]")
        sys.exit(1)

    # --- BATCH PROCESSING MODE ---
    if sys.argv[1] == '--batch':
        if len(sys.argv) < 4:
            print("Error: Batch mode requires a JSON file and a ROM path.")
            sys.exit(1)
            
        json_path = sys.argv[2]
        rom_path = sys.argv[3]
        
        # Determine the final output path
        if len(sys.argv) > 4:
            output_path = sys.argv[4]
        else:
            base, ext = os.path.splitext(rom_path)
            output_path = f"{base}_modified{ext}"

        # Validate paths
        if not os.path.isfile(json_path): print(f"Error: JSON file not found at '{json_path}'"); sys.exit(1)
        if not os.path.isfile(rom_path): print(f"Error: ROM file not found at '{rom_path}'"); sys.exit(1)

        # Read the entire ROM into memory ONCE
        print(f"Loading ROM '{rom_path}' into memory...")
        with open(rom_path, 'rb') as f:
            rom_data = bytearray(f.read())

        try:
            with open(json_path, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading or parsing JSON file: {e}"); sys.exit(1)
            
        # Process each graphic in the JSON file
        for item in config.get("graphics", []):
            try:
                print("\n" + "="*50)
                print(f"Processing: {item['image_path']}")
                print("="*50)

                image_path = item['image_path']
                if not os.path.isfile(image_path):
                    print(f"  -> ERROR: Image file not found: '{image_path}'. Skipping.")
                    continue

                snes_address = int(item['snes_address'], 16)
                target_size = item.get('target_size')
                palette_address_str = item.get('palette_address')
                palette_address = None
                
                if palette_address_str:
                    palette_address = int(palette_address_str, 16)
                    print(f"  -> Using specified palette address: 0x{palette_address:06X}")
                else:
                    print(f"  -> Auto-detecting closest palette for graphic at 0x{snes_address:06X}...")
                    palette_address = find_closest_palette(snes_address, ASSET_MAP)
                    if palette_address:
                        print(f"  -> Found closest palette at 0x{palette_address:06X}")
                    else:
                        print("  -> WARNING: No palettes found in ASSET_MAP. Cannot inject palette.")

                # Call the modified function, which updates our in-memory rom_data
                rom_data = inject_compressed_graphic(
                    rom_data=rom_data,
                    image_path=image_path,
                    snes_address=snes_address,
                    target_size=target_size,
                    palette_address=palette_address
                )
                
            except KeyError as e:
                print(f"Skipping item due to missing key: {e}. Please check your JSON.")
            except Exception as e:
                print(f"An error occurred while processing {item.get('image_path', 'an item')}: {e}")
                # Uncomment the line below to stop the batch process on the first error
                # sys.exit(1)
        
        # Write the final, fully modified ROM data to the disk ONCE
        print("\n" + "="*50)
        print(f"All injections complete. Writing to '{output_path}'...")
        with open(output_path, 'wb') as f:
            f.write(rom_data)
        print("Successfully created modified ROM.")
        return

    # (The Single Injection Mode logic below this remains unchanged)
    # --- SINGLE INJECTION MODE (Original Logic) ---
    rom_path = sys.argv[1]
    image_path = sys.argv[2]
    
    def is_hex(s):
        try:
            int(s.replace('0x', '').replace('0X', ''), 16)
            return True
        except (ValueError, AttributeError):
            return False

    if len(sys.argv) >= 4 and not sys.argv[3].startswith('--') and is_hex(sys.argv[3]):
        addr_str = sys.argv[3].replace('0x', '').replace('0X', '')
        snes_address = int(addr_str, 16)
        start_index = 4
    else:
        snes_address = 0x84D516
        start_index = 3

    target_size = None
    match_original_size = False
    palette_address = None
    test_after_inject = False
    output_path = None
    
    i = start_index
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--match-size':
            match_original_size = True
            i += 1
        elif arg == '--palette':
            if i + 1 < len(sys.argv):
                palette_addr_str = sys.argv[i + 1].replace('0x', '').replace('0X', '')
                palette_address = int(palette_addr_str, 16)
                i += 2
            else:
                print("Error: --palette requires an address")
                sys.exit(1)
        elif arg == '--test':
            test_after_inject = True
            i += 1
        elif arg.isdigit():
            target_size = int(arg)
            i += 1
        else:
            output_path = arg
            break
    
    if not os.path.isfile(rom_path):
        print(f"Error: ROM file not found at '{rom_path}'")
        sys.exit(1)
    
    if not os.path.isfile(image_path):
        print(f"Error: Image file not found at '{image_path}'")
        sys.exit(1)
    
    try:
        inject_compressed_graphic(rom_path, image_path, snes_address, output_path, target_size, match_original_size, palette_address)
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        from PIL import Image
    except ImportError:
        print("Error: The 'Pillow' library is required. Please install it with: pip install Pillow")
        sys.exit(1)
    
    main()
