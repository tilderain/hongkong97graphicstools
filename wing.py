import io

def create_translation_map():
    """
    Creates a one-to-one mapping from the English character set to the Kanji set.
    """
    # The source string of characters to be replaced
    english_chars = ".,!?'\"-/()ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

    # The ordered Kanji to be used for replacement
    kanji_lines = [
"内軟日如任年脳巴"#wingdings
"馬売薄発版犯販秘"
"紐不府武幅文兵平"
"便舗報方亡望本幕"
"亦抹密民無明面問"
"遊容用來頼絡利李"
"陸留龍了力連論和"
"來們售國將專很扣"
"權痰發盡詢賣製造"
"販売版權所有翻印"
    ]
    
    # Combine all Kanji into a single string
    kanji_chars = "".join(kanji_lines)

    # The English set has 72 characters. We will use the first 72 Kanji.
    # The remaining Kanji will be ignored as per the "in order" mapping rule.
    if len(kanji_chars) < len(english_chars):
        raise ValueError("Not enough Kanji characters provided to map to the English character set.")

    # Create the dictionary mapping from English to Kanji
    translation_map = dict(zip(english_chars, kanji_chars))
    
    return translation_map

def translate_text(text, translation_map):
    """
    Translates a given text using the provided character map.
    Spaces are converted to full-width spaces.
    Newlines and other unmapped characters are preserved.
    """
    # Use a string builder for efficiency
    translated_builder = io.StringIO()
    
    for char in text:
        if char == ' ':
            translated_builder.write('　')  # Full-width space
        elif char in translation_map:
            translated_builder.write(translation_map[char])
        else:
            translated_builder.write(char) # Preserve unmapped characters (like newlines)
            
    return translated_builder.getvalue()

# 1. Define the text to be translated
input_text = """
Webdings

What kind of place is this
Why are we here
Just to suffer
Every night i feel it
In my legs
My comrades

you are gay

You prob can't
read this but Hi to
anyone who can

Blah stuff here
bye hav a nic
day. lol

So how are u doin?
Good? Nice. Eatn a
sandwic rn.

I think i might have
waste my time make
this

WDGast
Ur Mom
"""

# 2. Create the character map
cipher_map = create_translation_map()

# 3. Translate the text
translated_output = translate_text(input_text, cipher_map)

# 4. Print the final result
print("--- Python Translation Script ---")
# To show the script itself, we can print its source code
with open(__file__, 'r') as f:
    print(f.read())
print("\n--- Translated Output ---")
print(translated_output)
