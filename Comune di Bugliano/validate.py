#!/usr/bin/env python3
"""
Validatore contenuti Heritage.
Uso:  python3 validate.py
Esegui dalla radice del repo del comune. Verifica:
  - tutti i JSON sono validi
  - ogni monument_id referenziato in itinerari/quiz esiste
  - ogni path di media puntato dai JSON esiste su disco
  - i campi obbligatori dei monumenti sono presenti
Esce con codice 1 se trova errori.
"""
import json
import os
import sys

ERRORS = []
WARN = []


def load(name):
    try:
        with open(name, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        ERRORS.append(f"File mancante: {name}")
        return None
    except json.JSONDecodeError as e:
        ERRORS.append(f"JSON non valido in {name}: {e}")
        return None


def check_path(path, where):
    if not path:
        return
    if not os.path.exists(path):
        ERRORS.append(f"Media mancante ({where}): {path}")


def main():
    manifest = load("manifest.json") or {}
    config = load("config.json") or {}
    monuments = load("monuments.json") or []
    itineraries = load("itineraries.json") or []
    quizzes = load("quizzes.json") or []

    monument_ids = set()

    # Monumenti
    for m in monuments:
        mid = m.get("id")
        if not mid:
            ERRORS.append(f"Monumento senza id: {m.get('name', '???')}")
            continue
        if mid in monument_ids:
            ERRORS.append(f"id duplicato: {mid}")
        monument_ids.add(mid)
        for req in ("name", "category", "short_description", "address"):
            if not m.get(req):
                WARN.append(f"[{mid}] campo consigliato mancante: {req}")
        if m.get("audio"):
            check_path(m["audio"].get("path"), f"audio {mid}")
        for img in m.get("images", []):
            check_path(img.get("path"), f"immagine {mid}")

    # Itinerari
    for it in itineraries:
        for stop in it.get("stops", []):
            ref = stop.get("monument_id")
            if ref and ref not in monument_ids:
                ERRORS.append(f"Itinerario '{it.get('id')}': monument_id inesistente: {ref}")
        check_path(it.get("cover_image"), f"itinerario {it.get('id')}")

    # Quiz
    for q in quizzes:
        ref = q.get("monument_id")
        if ref and ref not in monument_ids:
            ERRORS.append(f"Quiz '{q.get('id')}': monument_id inesistente: {ref}")
        for question in q.get("questions", []):
            check_path(question.get("image"), f"quiz {q.get('id')}")
            corrects = [o for o in question.get("options", []) if o.get("correct")]
            if len(corrects) != 1:
                WARN.append(f"Quiz '{q.get('id')}' domanda '{question.get('id')}': "
                            f"{len(corrects)} risposte corrette (atteso 1)")

    # Report
    for w in WARN:
        print("WARN:", w)
    for e in ERRORS:
        print("ERRORE:", e)

    if ERRORS:
        print(f"\n{len(ERRORS)} errori, {len(WARN)} avvisi. Build NON pronta.")
        sys.exit(1)
    print(f"\nTutto ok ({len(monument_ids)} monumenti). {len(WARN)} avvisi.")


if __name__ == "__main__":
    main()
