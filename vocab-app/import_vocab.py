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
    
    # Auto-detect delimiter (comma or semicolon)
    with open(filename, "r", encoding="utf-8") as f:
        first_line = f.readline()
        delimiter = ';' if first_line.count(';') > first_line.count(',') else ','
    
    with open(filename, "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter=delimiter)
        for row in reader:
            if len(row) >= 2:
                spanish = row[0].strip() if row[0] else ""
                col_b = row[1].strip() if len(row) > 1 and row[1] else ""
                col_c = row[2].strip() if len(row) > 2 and row[2] else ""
                col_d = row[3].strip() if len(row) > 3 and row[3] else ""
                col_e = row[4].strip() if len(row) > 4 and row[4] else ""
                
                # Auto-detect: does column B have both Chinese + Pinyin?
                if auto_split and col_b:
                    has_chinese = any('\u4e00' <= c <= '\u9fff' for c in col_b)
                    col_c_is_english = col_c and not any('\u4e00' <= c <= '\u9fff' for c in col_c)
                    
                    if has_chinese and col_c_is_english:
                        # Column B has Chinese+Pinyin, column C is English
                        chinese, pinyin = split_chinese_pinyin(col_b)
                        english = col_c
                        german = col_d
                    else:
                        chinese = col_b
                        pinyin = col_c
                        english = col_d
                        german = col_e
                else:
                    chinese = col_b
                    pinyin = col_c
                    english = col_d
                    german = col_e
                
                words.append({
                    "spanish": spanish,
                    "chinese": chinese,
                    "pinyin": pinyin,
                    "english": english,
                    "german": german
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
            # Read each column explicitly (Excel cells, no delimiter)
            spanish = str(row[0]).strip() if row[0] else ""
            col_b = str(row[1]).strip() if row[1] else ""
            col_c = str(row[2]).strip() if row[2] else ""
            col_d = str(row[3]).strip() if row[3] else ""
            col_e = str(row[4]).strip() if len(row) > 4 and row[4] else ""
            
            # Auto-detect: does column B have both Chinese + Pinyin?
            # Check if column B has Chinese chars AND column C looks like English (not pinyin)
            if auto_split and col_b:
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in col_b)
                col_c_is_english = col_c and not any('\u4e00' <= c <= '\u9fff' for c in col_c)
                
                if has_chinese and col_c_is_english:
                    # Column B has Chinese+Pinyin, column C is English
                    chinese, pinyin = split_chinese_pinyin(col_b)
                    english = col_c
                    german = col_d
                else:
                    # Normal case: column B=Chinese, C=Pinyin, D=English, E=German
                    chinese = col_b
                    pinyin = col_c
                    english = col_d
                    german = col_e
            else:
                chinese = col_b
                pinyin = col_c
                english = col_d
                german = col_e
            
            words.append({
                "spanish": spanish,
                "chinese": chinese,
                "pinyin": pinyin,
                "english": english,
                "german": german
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
