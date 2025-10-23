"""
Hong Kong 97 Text Dumper and Patcher Utility

This script can both extract (dump) and insert (patch) text in the game
'Hong Kong 97' for the Super Famicom/SNES.

--- USAGE ---

1. DUMPING TEXT:
   To extract all the game's text into a file for editing, run:
   python textpatch2.py dump > new_text.txt

2. EDITING TEXT:
   Open 'new_text.txt' in a text editor. You can change the text within the
   double quotes. Do NOT change the SNES addresses, coordinate numbers, or
   '[UN:XXXX]' tags.

3. PATCHING TEXT:
   After you have finished editing, save your changes and run the patcher:
   python textpatch2.py patch new_text.txt

   This will create a new ROM file named 'hongkong97_patched.smc'.

"""
import struct
import sys
import os
import re

# --- Configuration ---
ROM_FILENAME = 'hongkong97_modified.smc'
PATCHED_ROM_FILENAME = 'hongkong97_patchedreal.smc'
SMC_HEADER_SIZE = 512

# --- CRITICAL ---
# This game uses a LoROM memory map.
ROM_TYPE = 'LOROM'  # Can be 'LOROM' or 'HIROM'

# Enable this to see hex data before and after patching for verification.
DEBUG = True

# These are the SNES addresses for all text data blocks.
# English text blocks
ENGLISH_TEXT_BLOCKS = [
    0x8098A7,  # "GAMES WANTED!"
    0x809A6F,  # "Would you like to sell our products..."
    0x809805,  # "HAPPY SOFTWARE LTD."
    0x809431,  # "The year 1997 has arrived..."
    0x8094F1,  # "Crime rate skyrockeded!"
    0x8095EB,  # "for the massacre of the reds."
    0x8096CD,  # "However, in mainland China..."
]

# Japanese text blocks
JAPANESE_TEXT_BLOCKS = [
    0x808B05,  #mainmenu
    0x808BB9,  #address
    0x809045,  #address2
    0x808C1D,  #profits
    0x808D7B,  #sellourgames
    0x808F89,  #killermachine1.2
    0x808FE7,  #secretweapon
    0x80909B,  #CNsellgames
    0x80925B,  
    0x8092EF,  #Credits1
    0x809399,  #Credits2
    0x80918F,  
    0x809233,  
]
TEXT_BLOCK_ADDRESSES = ENGLISH_TEXT_BLOCKS + JAPANESE_TEXT_BLOCKS

# --- Font Mapping ---
# English/ASCII characters (used in English blocks)
FONT_MAP_STRING_ALPHA = ".,!?'\"-/()ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

# Japanese font map (kana and kanji)
FONT_MAP_STRING_JP = (
"　，。．・？！〒"
"々一＂（）＋－／"
"０１２３４５６７"
"８９ＡＢＣＤＥＦ"
"ＧＨＩＪＫＬＭＮ"
"ＯＰＱＲＳＴＵＶ"
"ＷＸＹＺａｂｃｄ"
"ｅｆｇｈｉｊｋｌ"
"ｍｎｏｐｑｒｓｔ"
"ｕｖｗｘｙｚぁ＃"
"あぃいぅうぇえぉ"
"おかがきぎくぐけ"
"げこごさざしじす"
"ずせぜそぞただち"
"ぢっつづてでとど"
"なにぬねのはばぱ"
"ひびぴふぶぷへべ"
"ぺほぼぽまみむめ"
"もゃやゅゆょよら"
"りるれろゎわゐ゙ゑ"
"をんァアィイゥウ"
"ェエォオカガキギ"
"クグケゲコゴサザ"
"シジスズセゼソゾ"
"タダチヂッツヅテ"
"デトドナニヌネノ"
"ハバパヒビピフブ"
"プヘベペホボポマ"
"ミムメモャヤュユ"
"ョヨラリルレロヮ"
"ワヰヱヲンヴヵヶ"
"案以依委易一因引"
"英益汚押億音下何"
"可家果過我画改絵"
"外害割閲割館喜器"
"寄希気記貴戯吉求"
"究巨挙京供協響九"
"区過群経計軽権研"
"原個呼後交公構港"
"行香合国黒此査在"
"罪作殺残使司子死"
"事字持磁而自七取"
"酬宿純所書召小詳"
"上情侵審新親進入"
"随趨是制政生西請"
"戚籍折説絶先川曽"
"送造他多太体代大"
"託但断地着中注者"
"嘆庁懲陳提訂の店"
"電吐鄧都度東等到"
"内軟日如任年脳巴"
"馬売薄発版犯販秘"
"紐不府武幅文兵平"
"便舗報方亡望本幕"
"亦抹密民無明面問"
"遊容用來頼絡利李"
"陸留龍了力連論和"
"來們售國將專很扣"
"權痰發盡詢賣製造"
"販売版權所有翻印"
"必究日本語ヤュユ"
)

# --- Dual-Offset System for Japanese ---
# The game uses a different offset for Kana vs Kanji, creating a split encoding system.
JP_KANA_OFFSET = 24
JP_KANJI_OFFSET = 23
# The index of the first Kanji in the font map. This determines the boundary.
FIRST_KANJI_INDEX = FONT_MAP_STRING_JP.find('案')
# The raw character code in the ROM at which we switch from Kana to Kanji logic.
JP_KANJI_START_CODE = FIRST_KANJI_INDEX + JP_KANJI_OFFSET  # 171 + 23 = 194

# Build English character map
CHAR_MAP_EN = {0x00: ' '}
for i, char in enumerate(FONT_MAP_STRING_ALPHA):
    CHAR_MAP_EN[i + 1] = char
for i in range(10):
    CHAR_MAP_EN[0x40 + i] = str(i)

# Build Japanese character map
CHAR_MAP_JP = {}
for i, char in enumerate(FONT_MAP_STRING_JP):
    CHAR_MAP_JP[i] = char

# Build encode maps for patching
ENCODE_MAP_EN = {char: code for code, char in CHAR_MAP_EN.items()}
ENCODE_MAP_JP = {char: code for code, char in CHAR_MAP_JP.items()}
# Allow standard space ' ' to be used in Japanese blocks; map it to the full-width space '　'.
ENCODE_MAP_JP[' '] = ENCODE_MAP_JP['　']
# --- End Configuration ---

def is_english_block(snes_addr: int) -> bool:
    """Determine if a block uses English or Japanese encoding."""
    return snes_addr in ENGLISH_TEXT_BLOCKS


def snes_to_pc(snes_addr: int) -> int:
    """Converts a SNES address to a PC file offset based on ROM_TYPE."""
    if ROM_TYPE.upper() == 'LOROM':
        # LoROM mapping for banks 0x80 and higher
        if (snes_addr & 0xF00000) < 0x700000 and (snes_addr & 0x8000) == 0:
            return -1 # Invalid LoROM address
        return ((snes_addr & 0x7F0000) >> 1) | (snes_addr & 0x7FFF)
    elif ROM_TYPE.upper() == 'HIROM':
        # HiROM mapping (original formula from your script)
        return (snes_addr & 0x7F0000) >> 1 | (snes_addr & 0x7FFF)
    else:
        raise ValueError(f"Unknown ROM_TYPE: '{ROM_TYPE}'")

def get_block_size(rom_data: bytes, start_offset: int) -> int:
    """Calculates the total size in bytes of a text block, including all terminators."""
    offset = start_offset
    if offset >= len(rom_data): return 0
    try:
        while True:
            x_coord = struct.unpack('<H', rom_data[offset:offset+2])[0]
            if x_coord == 0xFFFF:
                offset += 2
                break
            offset += 4
            while True:
                char_code = struct.unpack('<H', rom_data[offset:offset+2])[0]
                offset += 2
                if char_code == 0xFFFF:
                    break
        return offset - start_offset
    except IndexError:
        print(f"Warning: Reached end of ROM while calculating block size at offset 0x{start_offset:X}", file=sys.stderr)
        return len(rom_data) - start_offset

def dump_all_text(rom_data: bytes, header_offset: int):
    """Dumps all known text blocks to stdout in an editable format."""
    print("# Hong Kong 97 Text Dump", file=sys.stderr)
    print("# Edit the text within the quotes. Do not change coordinates or addresses.", file=sys.stderr)
    for snes_addr in TEXT_BLOCK_ADDRESSES:
        print(f"\n> 0x{snes_addr:X}")
        pc_address = snes_to_pc(snes_addr)
        if pc_address == -1:
            print(f"# Address 0x{snes_addr:X} is invalid for LoROM.", file=sys.stderr)
            continue
        final_offset = pc_address + header_offset
        if final_offset >= len(rom_data):
            print(f"# Address 0x{snes_addr:X} is out of ROM bounds.", file=sys.stderr)
            continue
        
        # Select appropriate character map
        is_english = is_english_block(snes_addr)
        char_map = CHAR_MAP_EN if is_english else CHAR_MAP_JP
        encoding_type = "EN" if is_english else "JP"
        print(f"# Encoding: {encoding_type}", file=sys.stderr)
        
        offset = final_offset
        while True:
            if offset + 2 > len(rom_data): break
            x_coord = struct.unpack('<H', rom_data[offset:offset+2])[0]
            if x_coord == 0xFFFF: break
            if offset + 4 > len(rom_data): break
            y_coord = struct.unpack('<H', rom_data[offset+2:offset+4])[0]
            offset += 4
            decoded_string = ""
            while True:
                if offset + 2 > len(rom_data): break
                char_code = struct.unpack('<H', rom_data[offset:offset+2])[0]
                offset += 2
                if char_code == 0xFFFF: break
                
                if not is_english:
                    # This game uses a split offset for Kana and Kanji
                    if char_code >= JP_KANJI_START_CODE:
                        lookup_code = char_code - JP_KANJI_OFFSET
                    else:
                        lookup_code = char_code - JP_KANA_OFFSET
                else:
                    lookup_code = char_code

                decoded_string += char_map.get(lookup_code, f'[UN:{char_code:04X}]')
            print(f'{x_coord},{y_coord},"{decoded_string}"')

def parse_input_file(filename: str) -> dict:
    """Parses the user-edited text file and returns a dictionary of text blocks."""
    blocks, current_addr = {}, None
    line_parser = re.compile(r'^\s*(\d+)\s*,\s*(\d+)\s*,"(.*)"\s*$')
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            if line.startswith('>'):
                current_addr = int(line[1:], 16)
                blocks[current_addr] = []
            elif current_addr is not None:
                match = line_parser.match(line)
                if match:
                    x, y, text = match.groups()
                    blocks[current_addr].append((int(x), int(y), text))
                else:
                    print(f"Warning: Skipping malformed line: {line}", file=sys.stderr)
    return blocks

def encode_text_block(sub_blocks: list, snes_addr: int) -> bytearray:
    """Encodes a list of (x, y, text) tuples into a binary text block."""
    # Select appropriate encode map
    is_english = is_english_block(snes_addr)
    encode_map = ENCODE_MAP_EN if is_english else ENCODE_MAP_JP
    
    block_data = bytearray()
    for x, y, text in sub_blocks:
        block_data.extend(struct.pack('<HH', x, y))
        i = 0
        while i < len(text):
            if text[i:i+4] == '[UN:':
                end_index = text.find(']', i)
                if end_index != -1:
                    hex_code_str = text[i+4:end_index]
                    try:
                        char_code = int(hex_code_str, 16)
                        block_data.extend(struct.pack('<H', char_code))
                        i = end_index + 1
                        continue
                    except ValueError: pass
            char = text[i]
            if char not in encode_map:
                raise ValueError(f"Character '{char}' not found in font map!")
            
            char_index = encode_map[char]
            final_code = char_index # Default for English blocks
            
            # Apply offset for Japanese text when encoding
            if not is_english:
                # Japanese text uses a split offset based on character index
                if char_index >= FIRST_KANJI_INDEX:
                    final_code = char_index + JP_KANJI_OFFSET
                else:
                    final_code = char_index + JP_KANA_OFFSET
            
            block_data.extend(struct.pack('<H', final_code))
            i += 1
        block_data.extend(b'\xFF\xFF')
    block_data.extend(b'\xFF\xFF')
    return block_data

def patch_rom(rom_data: bytes, header_offset: int, input_filename: str):
    """Patches the ROM with text from the input file."""
    print(f"Parsing input file: '{input_filename}'")
    try:
        new_text_blocks = parse_input_file(input_filename)
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.", file=sys.stderr)
        sys.exit(1)
    
    patched_data, total_blocks, patched_blocks, errors = bytearray(rom_data), len(new_text_blocks), 0, 0

    print("Starting patching process...")
    for snes_addr, sub_blocks in new_text_blocks.items():
        pc_address = snes_to_pc(snes_addr)
        if pc_address == -1:
             print(f"  -> Skipping invalid LoROM address 0x{snes_addr:X}...")
             continue
        final_offset = pc_address + header_offset
        encoding_type = "EN" if is_english_block(snes_addr) else "JP"
        print(f"  -> Processing block at SNES 0x{snes_addr:X} (PC 0x{final_offset:X}) [{encoding_type}]...")

        try:
            original_size = get_block_size(rom_data, final_offset)
            if original_size == 0:
                print("     Warning: Original block size is zero. Skipping.", file=sys.stderr)
                continue
            
            new_data = encode_text_block(sub_blocks, snes_addr)
            if len(new_data) > original_size:
                print("     ERROR: New text is too large to fit in the ROM!", file=sys.stderr)
                print(f"     Address: 0x{snes_addr:X}, Original Size: {original_size} bytes, New Size: {len(new_data)} bytes", file=sys.stderr)
                errors += 1
                continue
            
            if DEBUG:
                print(f"     Original data: {rom_data[final_offset:final_offset + original_size].hex(' ')}")
                print(f"     New data     : {new_data.hex(' ')}")

            patched_data[final_offset : final_offset + len(new_data)] = new_data
            padding_size = original_size - len(new_data)
            if padding_size > 0:
                padding_start = final_offset + len(new_data)
                patched_data[padding_start : padding_start + padding_size] = b'\x00' * padding_size
            patched_blocks += 1
        except ValueError as e:
            print(f"     ERROR encoding block 0x{snes_addr:X}: {e}", file=sys.stderr)
            errors += 1
        except Exception as e:
            print(f"     An unexpected error occurred at 0x{snes_addr:X}: {e}", file=sys.stderr)
            errors += 1
            
    print("-" * 20)
    if errors > 0:
        print(f"Patching finished with {errors} error(s).")
        print("The patched ROM was NOT written.")
    else:
        print(f"Successfully patched {patched_blocks}/{total_blocks} blocks.")
        with open(PATCHED_ROM_FILENAME, 'wb') as f:
            f.write(patched_data)
        print(f"New ROM saved as '{PATCHED_ROM_FILENAME}'")

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ['dump', 'patch']:
        print(__doc__)
        sys.exit(1)
    if not os.path.exists(ROM_FILENAME):
        print(f"Error: ROM file '{ROM_FILENAME}' not found.", file=sys.stderr)
        sys.exit(1)
    with open(ROM_FILENAME, 'rb') as f:
        rom_data = f.read()
    header_offset = 0
    if len(rom_data) % 1024 == SMC_HEADER_SIZE:
        header_offset = SMC_HEADER_SIZE
        print(f"Detected {SMC_HEADER_SIZE}-byte SMC header. Applying offset.", file=sys.stderr)
    mode = sys.argv[1]
    if mode == 'dump':
        dump_all_text(rom_data, header_offset)
    elif mode == 'patch':
        if len(sys.argv) < 3:
            print("Error: Please specify the input text file for patching.", file=sys.stderr)
            print("Usage: python textpatch2.py patch <filename.txt>", file=sys.stderr)
            sys.exit(1)
        patch_rom(rom_data, header_offset, sys.argv[2])

if __name__ == '__main__':
    main()