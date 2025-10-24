#!/bin/bash

# -----------------------------------------------------------------------------
# This script automates the build process for the Hong Kong 97 patch.
# It runs a series of Python scripts in order, renaming files as needed,
# and launches the final ROM in the higan emulator.
#
# If any step fails, the script will stop immediately.
# -----------------------------------------------------------------------------

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Define filenames for clarity ---
SOURCE_ROM="hongkong97.smc"
REPLACEMENTS_FILE="replacements.json"
TEXT_PATCH_FILE="new_text.txt"
FONT_FILE="hk97font16.png"

# Intermediate files that will be created
STEP1_OUTPUT="hongkong97_modified.smc"
STEP2_OUTPUT="hongkong97_patched.smc"
STEP3_OUTPUT="hongkong97_font_patched.smc"
STEP4_OUTPUT="cavestory97.smc"

# Final output ROM to be launched
FINAL_ROM="cavestory97-song.smc"


# --- Pre-flight Checks ---
echo "--- Starting Build Process ---"
echo "Checking for required files..."

# Check if all necessary files exist before starting
if ! [ -f "$SOURCE_ROM" ]; then echo "Error: Source ROM '$SOURCE_ROM' not found!"; exit 1; fi
if ! [ -f "pyenc5.py" ]; then echo "Error: Script 'pyenc5.py' not found!"; exit 1; fi
if ! [ -f "$REPLACEMENTS_FILE" ]; then echo "Error: Replacements file '$REPLACEMENTS_FILE' not found!"; exit 1; fi
if ! [ -f "textpatch3.py" ]; then echo "Error: Script 'textpatch3.py' not found!"; exit 1; fi
if ! [ -f "$TEXT_PATCH_FILE" ]; then echo "Error: Text patch file '$TEXT_PATCH_FILE' not found!"; exit 1; fi
if ! [ -f "$FONT_FILE" ]; then echo "Error: Font file '$FONT_FILE' not found!"; exit 1; fi
if ! [ -f "menupatch.py" ]; then echo "Error: Script 'menupatch.py' not found!"; exit 1; fi
if ! [ -f "spc.py" ]; then echo "Error: Script 'spc.py' not found!"; exit 1; fi

echo "All required files found. Starting build..."
echo ""


# --- Step 1: Apply JSON replacements ---
echo "Step 1/5: Running pyenc5.py..."
python3 pyenc5.py --batch "$REPLACEMENTS_FILE" "$SOURCE_ROM"
echo " -> Created $STEP1_OUTPUT"
echo ""


# --- Step 2: Apply text patches ---
# NOTE: This assumes textpatch3.py reads 'hongkong97_modified.smc'
# and writes to 'hongkong97_patched.smc' by default.
echo "Step 2/5: Running textpatch3.py to apply text patches..."
python3 textpatch3.py patch "$TEXT_PATCH_FILE"
echo " -> Created $STEP2_OUTPUT"
echo ""


# --- Step 3: Insert new font ---
# NOTE: This assumes textpatch3.py reads 'hongkong97_patched.smc'
# and writes to 'hongkong97_font_patched.smc' by default.
echo "Step 3/5: Running textpatch3.py to insert new font..."
python3 textpatch3.py insertfont "$FONT_FILE"
echo " -> Created $STEP3_OUTPUT"
echo ""


# --- Step 4: Apply menu patch and rename for final step ---
echo "Step 4/5: Running final menu patch..."
python3 menupatch.py "$STEP3_OUTPUT"

# --- Step 5: Run SPC script and launch in higan ---
echo "Step 5/5: Running spc.py"
python3 spc.py
echo ""


# --- Completion ---
echo "--- Build process complete! ---"
echo "Final ROM is '$FINAL_ROM'."

python3 ips.py
# --- Optional Cleanup ---
# Uncomment the following lines if you want to automatically
# delete the intermediate files after a successful build.
# -----------------------------------------------------------
# echo "Cleaning up intermediate files..."
# rm "$STEP1_OUTPUT"
# rm "$STEP2_OUTPUT"
# rm "$STEP3_OUTPUT"
# echo "Cleanup complete."
