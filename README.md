# Wiktionary Translation Extractor
 Extracts translations from dumps of English Wiktionary and outputs it to an SQLite database

## Usage
> $python3 wiktionary_translation_extractor.py path/to/dump/en_wiktionary_dump.xml

## Output Schema
```sql
CREATE TABLE Translations (
    word STRING NON NULL,        -- The root word that is translated
    meaning STRING,              -- The related meaning or sense of the word, for the translation
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
```

## License
This program is licensed under MIT. Output of this program is under the license of whatever input you use (so almost definitely Wikimedia/Wiktionary's license).

See LICENSE.md for the full license.