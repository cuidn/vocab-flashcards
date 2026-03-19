#!/usr/bin/env python3
"""Import vocabulary from Excel/CSV to vocab.json"""

import json
import csv
import sys
from pathlib import Path
from datetime import datetime

# Try to import openpyxl for Excel, fallback to csv
try:
    import openpyxl
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

DATA_FILE = Path(__file__).parent / "data" / "vocab.json"


def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"words": [], "last_updated": datetime.utcnow().isoformat()}


def save_vocab(data):
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_csv(filename):
    words = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                words.append({
                    "spanish": row[0].strip(),
                    "chinese": row[1].strip(),
                    "pinyin": row[2].strip() if len(row) > 2 else "",
                    "english": row[3].strip() if len(row) > 3 else ""
                })
    return words


def import_excel(filename):
    if not HAS_EXCEL:
        print("openpyxl not installed. Install with: pip install openpyxl")
        sys.exit(1)
    
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    
    words = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
        if row[0]:
            words.append({
                "spanish": str(row[0]).strip(),
                "chinese": str(row[1]).strip() if row[1] else "",
                "pinyin": str(row[2]).strip() if row[2] else "",
                "english": str(row[3]).strip() if row[3] else ""
            })
    return words


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_vocab.py <file.csv|file.xlsx>")
        sys.exit(1)
    
    filename = sys.argv[1]
    path = Path(filename)
    
    if not path.exists():
        print(f"File not found: {filename}")
        sys.exit(1)
    
    # Import based on extension
    if path.suffix == ".csv":
        new_words = import_csv(path)
    elif path.suffix in [".xlsx", ".xls"]:
        new_words = import_excel(path)
    else:
        print("Unsupported format. Use .csv or .xlsx")
        sys.exit(1)
    
    if not new_words:
        print("No words found in file")
        sys.exit(1)
    
    # Load existing and merge
    data = load_existing()
    new_id = max([w["id"] for w in data["words"]], default=0)
    
    for w in new_words:
        new_id += 1
        w["id"] = new_id
        w["created_at"] = datetime.utcnow().strftime("%Y-%m-%d")
        w["proficiency"] = 0
        data["words"].append(w)
    
    save_vocab(data)
    print(f"✓ Imported {len(new_words)} words (total: {len(data['words'])})")


if __name__ == "__main__":
    main()
