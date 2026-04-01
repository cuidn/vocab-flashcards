#!/usr/bin/env python3
"""Vocabulary Flashcard App - Local-first with Git sync"""

import json
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import random
import re
import io

# Config
DATA_FILE = Path(__file__).parent / "data" / "vocab.json"
app = FastAPI(title="Vocab Flashcards")

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Models
class Word(BaseModel):
    id: int
    spanish: str
    chinese: str
    pinyin: str
    english: str
    german: str = ""
    created_at: str
    proficiency: int = 0


class WordCreate(BaseModel):
    spanish: str
    chinese: str
    pinyin: str
    english: str
    german: str = ""


class VocabStore(BaseModel):
    words: List[Word]
    last_updated: str


def load_vocab() -> VocabStore:
    if not DATA_FILE.exists():
        return VocabStore(words=[], last_updated=datetime.utcnow().isoformat())
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return VocabStore(**data)


def save_vocab(store: VocabStore):
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    store.last_updated = datetime.utcnow().isoformat()
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(store.model_dump(), f, ensure_ascii=False, indent=2)


# Routes
@app.get("/")
async def root():
    index_file = static_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "Vocab Flashcard App - Go to /static/index.html"}


@app.get("/api/words")
async def get_words():
    store = load_vocab()
    return store


@app.post("/api/words")
async def add_word(word: WordCreate):
    store = load_vocab()
    new_id = max([w.id for w in store.words], default=0) + 1
    new_word = Word(
        id=new_id,
        spanish=word.spanish,
        chinese=word.chinese,
        pinyin=word.pinyin,
        english=word.english,
        german=word.german,
        created_at=datetime.utcnow().strftime("%Y-%m-%d"),
        proficiency=0
    )
    store.words.append(new_word)
    save_vocab(store)
    return new_word


@app.delete("/api/words/{word_id}")
async def delete_word(word_id: int):
    store = load_vocab()
    store.words = [w for w in store.words if w.id != word_id]
    save_vocab(store)
    return {"status": "deleted", "id": word_id}


@app.post("/api/words/{word_id}/practice")
async def practice_word(word_id: int, correct: bool):
    store = load_vocab()
    for word in store.words:
        if word.id == word_id:
            if correct:
                word.proficiency = min(word.proficiency + 1, 5)
            else:
                word.proficiency = max(word.proficiency - 1, 0)
            break
    save_vocab(store)
    return {"status": "updated"}


@app.post("/api/import")
async def import_words(words: List[WordCreate]):
    store = load_vocab()
    new_id = max([w.id for w in store.words], default=0)
    for word in words:
        new_id += 1
        store.words.append(Word(
            id=new_id,
            spanish=word.spanish,
            chinese=word.chinese,
            pinyin=word.pinyin,
            english=word.english,
            german=word.german,
            created_at=datetime.utcnow().strftime("%Y-%m-%d"),
            proficiency=0
        ))
    save_vocab(store)
    return {"status": "imported", "count": len(words)}


@app.post("/api/import/xlsx")
async def import_xlsx(file: UploadFile = File(...)):
    """Import vocabulary from an xlsx file.

    Expected columns: Spanish, Chinese, English, German
    The Chinese column contains Chinese characters + Pinyin combined.
    """
    import openpyxl

    if not file.filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Only .xlsx and .xls files are supported")

    try:
        contents = await file.read()
        wb = openpyxl.load_workbook(io.BytesIO(contents))
        ws = wb.active
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel file: {e}")

    store = load_vocab()
    new_id = max([w.id for w in store.words], default=0)
    rows_added = 0

    # Pattern: Chinese characters (one or more) followed by space and Pinyin
    # e.g. "提前完成工作 Tí qián wán chéng gōng zuò"
    chinese_pinyin_pattern = re.compile(
        r'^([\u4e00-\u9fff]+)\s+([a-zA-Z\u00c0-\u024f\u0100\u0128]+.*)$',
        re.UNICODE
    )

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row[0]:
            continue

        spanish = str(row[0]).strip() if row[0] else ""
        col_b = str(row[1]).strip() if row[1] else ""
        english = str(row[2]).strip() if row[2] else ""
        german = str(row[3]).strip() if row[3] else "" if len(row) > 3 else ""

        if not spanish or not col_b:
            continue

        # Split Chinese + Pinyin from column B
        match = chinese_pinyin_pattern.match(col_b)
        if match:
            chinese = match.group(1)
            pinyin = match.group(2)
        else:
            chinese = col_b
            pinyin = ""

        new_id += 1
        store.words.append(Word(
            id=new_id,
            spanish=spanish,
            chinese=chinese,
            pinyin=pinyin,
            english=english,
            german=german,
            created_at=datetime.utcnow().strftime("%Y-%m-%d"),
            proficiency=0
        ))
        rows_added += 1

    save_vocab(store)
    return {"status": "imported", "count": rows_added}


@app.get("/api/practice/random")
async def get_random_word():
    store = load_vocab()
    if not store.words:
        raise HTTPException(status_code=404, detail="No words available")
    word = random.choice(store.words)
    return word


# CLI Commands
import click

DATA_FILE = Path(__file__).parent / "data" / "vocab.json"


@click.group()
def cli():
    """Vocab Flashcard App CLI"""
    pass


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind")
@click.option("--port", default=8000, help="Port to bind")
def serve(host, port):
    """Start the web server"""
    import uvicorn
    click.echo(f"🚀 Starting Vocab Flashcards at http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


@cli.command()
@click.option("--spanish", required=True, help="Spanish word")
@click.option("--chinese", required=True, help="Chinese word")
@click.option("--pinyin", required=True, help="Pinyin pronunciation")
@click.option("--english", required=True, help="English translation")
@click.option("--german", default="", help="German translation (optional)")
def add(spanish, chinese, pinyin, english, german):
    """Add a new vocabulary word"""
    store = load_vocab()
    new_id = max([w.id for w in store.words], default=0) + 1
    new_word = Word(
        id=new_id,
        spanish=spanish,
        chinese=chinese,
        pinyin=pinyin,
        english=english,
        german=german,
        created_at=datetime.utcnow().strftime("%Y-%m-%d"),
        proficiency=0
    )
    store.words.append(new_word)
    save_vocab(store)
    click.echo(f"✅ Added word #{new_id}: {spanish} - {chinese}")


@cli.command()
@click.argument("word_id", type=int)
def delete(word_id):
    """Delete a vocabulary word by ID"""
    store = load_vocab()
    word = next((w for w in store.words if w.id == word_id), None)
    if not word:
        click.echo(f"❌ Word #{word_id} not found")
        return
    store.words = [w for w in store.words if w.id != word_id]
    save_vocab(store)
    click.echo(f"🗑️  Deleted word #{word_id}: {word.spanish}")


@cli.command()
@click.option("--format", default="table", type=click.Choice(["table", "json", "csv"]), help="Output format")
def list(format):
    """List all vocabulary words"""
    store = load_vocab()
    if not store.words:
        click.echo("📭 No words yet. Add some first!")
        return
    
    if format == "json":
        import json
        click.echo(json.dumps([w.model_dump() for w in store.words], ensure_ascii=False, indent=2))
    elif format == "csv":
        click.echo("ID,Spanish,Chinese,Pinyin,English,German,Proficiency,Created")
        for w in store.words:
            click.echo(f"{w.id},{w.spanish},{w.chinese},{w.pinyin},{w.english},{w.german},{w.proficiency},{w.created_at}")
    else:
        click.echo(f"\n📚 Vocabulary ({len(store.words)} words)\n")
        click.echo(f"{'ID':>3}  {'Spanish':<15} {'Chinese':<10} {'Pinyin':<15} {'English':<12} {'German':<10} {'Lv':>2}")
        click.echo("-" * 80)
        for w in store.words:
            click.echo(f"{w.id:>3}  {w.spanish:<15} {w.chinese:<10} {w.pinyin:<15} {w.english:<12} {w.german:<10} {w.proficiency:>2}")


@cli.command()
def stats():
    """Show vocabulary statistics"""
    store = load_vocab()
    if not store.words:
        click.echo("📭 No words yet.")
        return
    
    total = len(store.words)
    with_german = len([w for w in store.words if w.german])
    avg_prof = sum(w.proficiency for w in store.words) / total
    
    prof_dist = {}
    for w in store.words:
        prof_dist[w.proficiency] = prof_dist.get(w.proficiency, 0) + 1
    
    click.echo(f"\n📊 Vocabulary Statistics\n")
    click.echo(f"  Total words:     {total}")
    click.echo(f"  With German:      {with_german}")
    click.echo(f"  Avg proficiency:  {avg_prof:.1f}")
    click.echo(f"\n  Proficiency distribution:")
    for level in range(6):
        count = prof_dist.get(level, 0)
        bar = "█" * count
        click.echo(f"    {level}: {bar} ({count})")


@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--format", "fmt", default="auto", type=click.Choice(["auto", "csv", "xlsx"]), help="File format")
def import_file(file, fmt):
    """Import words from CSV or Excel file"""
    from import_vocab import import_excel, import_csv
    
    store = load_vocab()
    initial_count = len(store.words)
    
    try:
        if fmt == "xlsx" or file.endswith(".xlsx"):
            new_words = import_excel(file)
        else:
            new_words = import_csv(file)
        
        new_id = max([w.id for w in store.words], default=0)
        for w in new_words:
            new_id += 1
            w.id = new_id
            w.created_at = datetime.utcnow().strftime("%Y-%m-%d")
            w.proficiency = 0
            store.words.append(w)
        
        save_vocab(store)
        added = len(store.words) - initial_count
        click.echo(f"✅ Imported {added} words from {file}")
    except Exception as e:
        click.echo(f"❌ Import failed: {e}")


if __name__ == "__main__":
    cli()
