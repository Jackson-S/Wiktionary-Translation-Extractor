'''
Takes an XML backup of English Wiktionary (all articles and pages) and outputs an
SQLite database of all translations with the schema:

CREATE TABLE Translations (
    word STRING NON NULL,        -- The root word that is translated
    meaning STRING NON NULL,     -- The related meaning or sense of the word, for the translation
    language STRING NON NULL,    -- The language of the translation as an ISO code
    translation STRING NON NULL, -- The actual translation, in the native script
    isEquivalent BOOL NON NULL,  -- Specifies if the translation is direct or if it is a phrase equivalent
    gender STRING,               -- The gender of the translation, if any
    scriptCode STRING,           -- The script the translation is in as an ISO code
    transliteration STRING,      -- The transliteration of the translation into latin characters, or for
    alternate STRING,            -- Alternate forms of the translation, i.e. kana for a kanji translation in Japanese
    literal STRING,              -- The literal meaning of a translation in English
    qualifier STRING             -- Any qualifiers or extra information relating to a translation
)

The progress bar only offers an approximation of the time taken, based on the size of the 2019/11/20 Wiktionary dump.
Dumps can be obtained from here https://dumps.wikimedia.org/enwiktionary/

Note that wiktionary dumps are huge (>6gb of pure text) and will probably break any text editor that tries to open them.
'''

from typing import List, Optional, Dict
from collections import defaultdict
from dataclasses import dataclass
from tqdm import tqdm

import sqlite3
import sys
import re


@dataclass
class Translation:
    language_code: str
    translation: str
    is_equivalent_term: bool = True
    gender: Optional[str] = None
    script_code: Optional[str] = None
    transliteration: Optional[str] = None
    alternate_form: Optional[str] = None
    literal_translation: Optional[str] = None
    qualifier: Optional[str] = None


@dataclass
class TranslationGroup:
    meaning: str
    translations: List[Translation]


def generate_arguments(arguments: List[str]) -> (List[str], Dict[str, str]):
    '''
    Generate Lua positional and keyword arguments from a list
    '''
    positional_arguments = list()
    keyword_arguments = dict()
    
    # Track if any positional arguments occur after keyword arguments (illegal)
    keywords = False
    
    for argument in arguments:
        if "=" in argument:
            keywords = True
            split_index = argument.index("=")
            keyword_arguments[argument[:split_index]] = argument[split_index+1:]
        elif not keywords:
            positional_arguments.append(argument)
        else:
            raise TypeError("arguments is not of correct format")

    return positional_arguments, keyword_arguments


def decode_term(arguments: List[str]) -> Translation:
    '''
    Take in an argument of format [t, jp, 日本語, ...] given by doing .split("|") 
    on the input and return a collection of outputs
    '''
    type = arguments[0]

    if type not in ["t", "t+", "t-simple", "tt", "tt+"]:
        raise TypeError("Incorrect list type")

    positional, keyword = generate_arguments(arguments[1:])
    
    if len(positional) < 2:
        raise TypeError("Missing required positional arguments")

    result = Translation(positional[0], positional[1])

    # Check to see if the given translation is a phrase, with individually linked words
    if "[[" and "]]" in arguments[1]:
        result.is_equivalent_term = False
        result.translation = result.translation.replace("[[", "").replace("]]", "")

    # Add gender
    if len(positional) >= 3:
        result.gender = positional[2]

    # Add keyword arguments
    if "sc" in keyword:
        result.script_code = keyword["sc"]
    if "tr" in keyword:
        result.transliteration = keyword["tr"]
    if "alt" in keyword:
        result.alternate_form = keyword["alt"]
    if "lit" in keyword:
        result.literal_translation = keyword["lit"]
    if "g" in keyword:
        result.gender = keyword["g"]

    return result


translations = defaultdict(list)

with open(sys.argv[1]) as in_file:
    page_title = None
    recording = False
    group = None

    for line in tqdm(in_file, total=209_373_622):
        if "<title>" in line:
            # Get the page title
            page_title = line.strip()[7:-8]
            # Special handling for translation pages (common for pages with many translations)
            if page_title.endswith("/translations"):
                page_title = page_title[:-13]

        elif "{{trans-top|" in line:
            # Begin parsing translations and get the meaning
            recording = True
            meaning = line.strip()[12:-2]
            group = TranslationGroup(meaning, [])

        elif "{{trans-bottom}}" in line:
            # Finish parsing translations
            recording = False
            translations[page_title].append(group)
        
        elif "{{trans-mid}}" in line:
            # Mid is useless to us, defines layout on Wiktionary
            pass

        elif recording:
            for translation in line.split(","):
                qualifier = None
                
                # Find all the Lua codeblocks in the line, split them and remove the enclosing {{ }}
                for codeblock in map(lambda x: x.group(0)[2:-2].split("|"), re.finditer(r"{{.*?}}", translation)):
                    if codeblock[0] == "qualifier" and len(codeblock) > 1:
                        # Run a join just in case the qualifier included a "|" for some reason...
                        qualifier = "|".join(codeblock[1:])
                    else:
                        try:
                            new_entry = decode_term(codeblock)
                            new_entry.qualifier = qualifier
                            group.translations.append(new_entry)
                        except TypeError as e:
                            continue

db = sqlite3.connect("database.db")
cursor = db.cursor()

cursor.execute("""
CREATE TABLE Translations (
    word STRING NON NULL,        -- The root word that is translated
    meaning STRING NON NULL,     -- The related meaning or sense of the word, for the translation
    language STRING NON NULL,    -- The language of the translation as an ISO code
    translation STRING NON NULL, -- The actual translation, in the native script
    isEquivalent BOOL NON NULL,  -- Specifies if the translation is direct or if it is a phrase equivalent
    gender STRING,               -- The gender of the translation, if any
    scriptCode STRING,           -- The script the translation is in as an ISO code
    transliteration STRING,      -- The transliteration of the translation into latin characters, or for
    alternate STRING,            -- Alternate forms of the translation, i.e. kana for a kanji translation in Japanese
    literal STRING,              -- The literal meaning of a translation in English
    qualifier STRING             -- Any qualifiers or extra information relating to a translation
)
""")

for word, meaning_group in translations.items():
    for group in meaning_group:
        for translation in group.translations:
            parameters = (
                word,
                group.meaning,
                translation.language_code,
                translation.translation,
                translation.is_equivalent_term,
                translation.gender,
                translation.script_code,
                translation.transliteration,
                translation.alternate_form,
                translation.literal_translation,
                translation.qualifier
            )
            cursor.execute("INSERT INTO Translations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", parameters)

cursor.close()
db.commit()
db.close()
