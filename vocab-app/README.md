# Vocab Flashcards 🎴

Local-first flashcard app for Spanish/Chinese/English/German vocabulary.

## Quick Start

```bash
git clone https://github.com/cuidn/vocab-flashcards.git
cd vocab-flashcards
pip install -r requirements.txt
python app.py
```

Then open http://localhost:8000 in your browser.

## Features

- **Practice**: Random flashcards with flip animation
- **Multiple directions**: ES↔ZH, ES↔EN, ZH↔EN, ES↔DE, EN↔DE, ZH↔DE (randomized)
- **Track progress**: Proficiency level (0-5) per word
- **Add words**: Manual entry (Spanish, Chinese, Pinyin, English, German)
- **Import**: Paste CSV/TSV or use import script
- **Git sync**: Just commit `vocab-app/data/vocab.json`

## Import from Excel/CSV

1. Export your Excel sheet as CSV
2. Run: `python import_vocab.py yourfile.csv`

Format: `spanish, chinese, pinyin, english, german` (no header)

Or paste directly in the Import tab in the web UI.

## Git Sync

```bash
# Get latest words from colleagues
git fetch origin
git rebase origin/master

# After adding words locally
git add vocab-app/data/vocab.json
git commit -m "Add new words"
git push origin master
```

## Data Format

```json
{
  "words": [
    {
      "id": 1,
      "spanish": "Mantenimiento",
      "chinese": "维护",
      "pinyin": "Wéi hù",
      "english": "maintenance",
      "german": "Wartung",
      "created_at": "2026-03-20",
      "proficiency": 2
    }
  ],
  "last_updated": "2026-03-20T00:00:00Z"
}
```
