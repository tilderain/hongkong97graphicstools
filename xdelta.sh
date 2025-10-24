#!/bin/bash

# ==============================================================================
# create_patches.sh
#
# This script generates xdelta patches for the Cave Story '97 ROM hack.
# It requires the xdelta3 command-line utility to be installed.
#
# It creates two patches:
#   1. cavestory97.xdelta:       Menu patch + Font patch
#   2. cavestory97-ogsong.xdelta: Menu patch + Font patch + Original Song
#
# Both patches are created from the clean, original "hongkong97.smc" ROM.
# ==============================================================================

# --- Configuration ---
ORIGINAL_ROM="hongkong97.smc"
PATCHED_ROM_A="cavestory97.smc"
PATCHED_ROM_B="cavestory97-ogsong.smc"

PATCH_FILE_A="cavestory97.xdelta"
PATCH_FILE_B="cavestory97-ogsong.xdelta"

# --- Colors for output ---
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}--- Cave Story '97 Patch Creator ---${NC}"

# --- Pre-flight Checks ---

# 1. Check if xdelta3 is installed
if ! command -v xdelta3 &> /dev/null; then
    echo -e "${RED}Error: 'xdelta3' command not found.${NC}"
    echo "Please install xdelta3 to continue. On Debian/Ubuntu, use: sudo apt install xdelta3"
    exit 1
fi

# 2. Check for required ROM files
REQUIRED_FILES=("$ORIGINAL_ROM" "$PATCHED_ROM_A" "$PATCHED_ROM_B")
ALL_FILES_FOUND=true

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: Required file not found: $file${NC}"
        ALL_FILES_FOUND=false
    fi
done

if [ "$ALL_FILES_FOUND" = false ]; then
    echo "Aborting due to missing files."
    exit 1
fi

echo "All required files and tools are present. Starting patch creation..."
echo

# --- Patch Creation ---

# 1. Create the standard patch
echo "Creating patch for '$PATCHED_ROM_A'..."
if xdelta3 -e -s "$ORIGINAL_ROM" "$PATCHED_ROM_A" "$PATCH_FILE_A"; then
    echo -e " -> ${GREEN}Success:${NC} Created '$PATCH_FILE_A'"
else
    echo -e " -> ${RED}Failure:${NC} Could not create '$PATCH_FILE_A'"
    exit 1
fi
echo

# 2. Create the "Original Song" patch
echo "Creating patch for '$PATCHED_ROM_B'..."
if xdelta3 -e -s "$ORIGINAL_ROM" "$PATCHED_ROM_B" "$PATCH_FILE_B"; then
    echo -e " -> ${GREEN}Success:${NC} Created '$PATCH_FILE_B'"
else
    echo -e " -> ${RED}Failure:${NC} Could not create '$PATCH_FILE_B'"
    exit 1
fi
echo

echo -e "${GREEN}All patches created successfully!${NC}"
exit 0
