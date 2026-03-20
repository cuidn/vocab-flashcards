#!/usr/bin/env python3
"""Import vocabulary from Excel/CSV to vocab.json"""

import json
import csv
import sys
import re
from pathlib import Path
from datetime import datetime

# Try to import openpyxl for Excel, fallback to csv
try:
    import openpyxl
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

DATA_FILE = Path(__file__).parent / "data" / "vocab.json"


def split_chinese_pinyin(text):
    """Split '窗户 Chuāng Hù' into ('窗户', 'Chuāng Hù')"""
    if not text:
        return "", ""
    
    text = text.strip()
    
    # Pattern: Chinese characters (one or more) followed by space and Pinyin
    # Matches Unicode range for Chinese chars, then space, then Latin/Pinyin
    match = re.match(r'^([\u4e00-\u9fff]+)\s+([a-zA-Z\u00c0-\u024f\u0100\u0128]+.*)$', text, re.UNICODE)
    if match:
        return match.group(1), match.group(2)
    
    # If no space found or no clear split, assume it's all Chinese (no pinyin)
    return text, ""


def load_existing():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"words": [], "last_updated": datetime.utcnow().isoformat()}


def save_vocab(data):
    data["last_updated"] = datetime.utcnow().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def import_csv(filename, auto_split=True):
    words = []
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 3:
                chinese_raw = row[1].strip()
                
                # Auto-split Chinese + Pinyin if needed
                if auto_split and len(row) >= 3 and row[2].strip() == "":
                    chinese, pinyin = split_chinese_pinyin(chinese_raw)
                else:
                    chinese = chinese_raw
                    pinyin = row[2].strip() if len(row) > 2 else ""
                
                words.append({
                    "spanish": row[0].strip(),
                    "chinese": chinese,
                    "pinyin": pinyin,
                    "english": row[3].strip() if len(row) > 3 else "",
                    "german": row[4].strip() if len(row) > 4 else ""
                })
    return words


def import_excel(filename, auto_split=True):
    if not HAS_EXCEL:
        print("openpyxl not installed. Install with: pip install openpyxl")
        sys.exit(1)
    
    wb = openpyxl.load_workbook(filename)
    ws = wb.active
    
    words = []
    for row in ws.iter_rows(min_row=2, values_only=True):  # Skip header
        if row[0]:
            chinese_raw = str(row[1]).strip() if row[1] else ""
            
            # Auto-split Chinese + Pinyin if needed (column B has both)
            if auto_split and len(row) >= 3:
                # If column C (pinyin) is empty, try to split column B
                pinyin_col = str(row[2]).strip() if row[2] else ""
                if not pinyin_col:
                    chinese, pinyin = split_chinese_pinyin(chinese_raw)
                else:
                    chinese = chinese_raw
                    pinyin = pinyin_col
            else:
                chinese = chinese_raw
                pinyin = str(row[2]).strip() if row[2] else ""
            
            words.append({
                "spanish": str(row[0]).strip(),
                "chinese": chinese,
                "pinyin": pinyin,
                "english": str(row[3]).strip() if row[3] else "",
                "german": str(row[4]).strip() if len(row) > 4 and row[4] else ""
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
