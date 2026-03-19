#!/usr/bin/env python3
"""Vocabulary Flashcard App - Local-first with Git sync"""

import json
import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import random

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
    created_at: str
    proficiency: int = 0


class WordCreate(BaseModel):
    spanish: str
    chinese: str
    pinyin: str
    english: str


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
            created_at=datetime.utcnow().strftime("%Y-%m-%d"),
            proficiency=0
        ))
    save_vocab(store)
    return {"status": "imported", "count": len(words)}


@app.get("/api/practice/random")
async def get_random_word():
    store = load_vocab()
    if not store.words:
        raise HTTPException(status_code=404, detail="No words available")
    word = random.choice(store.words)
    return word


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Vocab Flashcards at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
