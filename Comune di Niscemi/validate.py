#!/usr/bin/env python3
"""
Validatore contenuti Heritage.
Uso:  python3 validate.py
Esegui dalla radice del repo del comune. Verifica:
  - tutti i JSON sono validi
  - ogni monument_id referenziato in itinerari/quiz esiste
  - ogni path di media puntato dai JSON esiste su disco
  - i campi obbligatori dei monumenti sono presenti
  - le traduzioni (i18n/<lingua>/) puntano a id esistenti, contengono solo campi
    traducibili e segnala i testi non ancora tradotti
Esce con codice 1 se trova errori.
"""
import json
import os
import re
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


def tr_obj(lang, where, tr, allowed):
    if not isinstance(tr, dict):
        ERRORS.append(f"[{lang}] {where}: atteso un oggetto")
        return {}
    extra = sorted(set(tr) - set(allowed))
    if extra:
        ERRORS.append(f"[{lang}] {where}: campi non traducibili: {', '.join(extra)}")
    return tr


def tr_keyed(lang, where, base_keys, tr):
    if not isinstance(tr, dict):
        ERRORS.append(f"[{lang}] {where}: atteso un oggetto con chiave id")
        return {}
    for k in tr:
        if k not in base_keys:
            ERRORS.append(f"[{lang}] {where}: chiave inesistente nei file base: {k}")
    return tr


def tr_missing(base, tr, fields):
    return [f for f in fields if base.get(f) and not tr.get(f)]


def report_missing(lang, where, missing):
    if missing:
        WARN.append(f"[{lang}] {where}: non tradotti: {', '.join(missing)}")


MON_TEXT = ("name", "short_description", "description", "address", "tags")


def check_monuments_tr(lang, monuments, tr):
    tr = tr_keyed(lang, "monuments", {m.get("id") for m in monuments}, tr)
    for m in monuments:
        mid = m.get("id")
        where = f"monumento '{mid}'"
        if mid not in tr:
            WARN.append(f"[{lang}] {where}: non tradotto")
            continue
        t = tr_obj(lang, where, tr[mid], MON_TEXT + ("audio", "images", "history"))
        missing = tr_missing(m, t, MON_TEXT)
        if m.get("audio") and not t.get("audio"):
            missing.append(f"audio (resta in '{m['audio'].get('language', '?')}')")
        if t.get("audio"):
            check_path(t["audio"].get("path"), f"audio {lang} {mid}")
            if t["audio"].get("language") != lang:
                WARN.append(f"[{lang}] {where}: audio.language dovrebbe essere '{lang}'")
        imgs = {i.get("path"): i for i in m.get("images", [])}
        t_imgs = tr_keyed(lang, f"{where} images", imgs, t.get("images", {}))
        for path, img in imgs.items():
            ti = tr_obj(lang, f"{where} immagine {path}", t_imgs.get(path, {}), ("title", "alt"))
            missing += [f"images[{path}].{f}" for f in tr_missing(img, ti, ("title", "alt"))]
        hist = m.get("history") or []
        t_hist = t.get("history", [])
        if not isinstance(t_hist, list) or len(t_hist) > len(hist):
            ERRORS.append(f"[{lang}] {where}: 'history' deve essere un array di al massimo "
                          f"{len(hist)} voci, nello stesso ordine dei file base")
            t_hist = []
        for i, h in enumerate(hist):
            th = tr_obj(lang, f"{where} history[{i}]", t_hist[i] if i < len(t_hist) else {},
                        ("title", "description"))
            missing += [f"history[{i}].{f}" for f in tr_missing(h, th, ("title", "description"))]
        report_missing(lang, where, missing)


def check_itineraries_tr(lang, itineraries, tr):
    tr = tr_keyed(lang, "itineraries", {i.get("id") for i in itineraries}, tr)
    for it in itineraries:
        iid = it.get("id")
        where = f"itinerario '{iid}'"
        if iid not in tr:
            WARN.append(f"[{lang}] {where}: non tradotto")
            continue
        t = tr_obj(lang, where, tr[iid], ("name", "short_name", "description", "stops"))
        missing = tr_missing(it, t, ("name", "short_name", "description"))
        stops = {s.get("monument_id"): s for s in it.get("stops", [])}
        t_stops = tr_keyed(lang, f"{where} stops", stops, t.get("stops", {}))
        for ref, s in stops.items():
            ts = tr_obj(lang, f"{where} tappa {ref}", t_stops.get(ref, {}), ("note",))
            missing += [f"stops[{ref}].note" for _ in tr_missing(s, ts, ("note",))]
        report_missing(lang, where, missing)


def check_quizzes_tr(lang, quizzes, tr):
    tr = tr_keyed(lang, "quizzes", {q.get("id") for q in quizzes}, tr)
    for quiz in quizzes:
        qzid = quiz.get("id")
        where = f"quiz '{qzid}'"
        if qzid not in tr:
            WARN.append(f"[{lang}] {where}: non tradotto")
            continue
        t = tr_obj(lang, where, tr[qzid], ("title", "description", "questions"))
        missing = tr_missing(quiz, t, ("title", "description"))
        questions = {q.get("id"): q for q in quiz.get("questions", [])}
        t_qs = tr_keyed(lang, f"{where} questions", questions, t.get("questions", {}))
        for qid, q in questions.items():
            tq = tr_obj(lang, f"{where} domanda {qid}", t_qs.get(qid, {}),
                        ("text", "options", "explanation"))
            missing += [f"{qid}.{f}" for f in tr_missing(q, tq, ("text", "explanation"))]
            opts = {o.get("id"): o for o in q.get("options", [])}
            t_opts = tr_keyed(lang, f"{where} domanda {qid} options", opts, tq.get("options", {}))
            missing += [f"{qid}.options.{oid}" for oid, o in opts.items()
                        if o.get("text") and not t_opts.get(oid)]
        report_missing(lang, where, missing)


def check_config_tr(lang, config, tr):
    t = tr_obj(lang, "config", tr, ("comune",))
    comune = config.get("comune", {})
    tc = tr_obj(lang, "config comune", t.get("comune", {}),
                ("name", "short_description", "description", "patron_saint"))
    report_missing(lang, "config", tr_missing(comune, tc, ("short_description", "description")))


def check_translations(manifest, base):
    default = manifest.get("default_language")
    langs = manifest.get("available_languages") or []
    translations = manifest.get("translations") or {}
    if default not in langs:
        ERRORS.append(f"manifest.json: default_language '{default}' non e' in available_languages")
    for lang in translations:
        if lang not in langs or lang == default:
            WARN.append(f"manifest.json: 'translations.{lang}' ignorata (lingua predefinita "
                        f"o assente da available_languages)")
    checks = {
        "config": check_config_tr,
        "monuments": check_monuments_tr,
        "itineraries": check_itineraries_tr,
        "quizzes": check_quizzes_tr,
    }
    for lang in langs:
        if lang == default:
            continue
        files = translations.get(lang)
        if not isinstance(files, dict):
            ERRORS.append(f"manifest.json: lingua '{lang}' senza voce in 'translations'")
            continue
        for key, check in checks.items():
            if not files.get(key):
                WARN.append(f"[{lang}] manifest.json: manca translations.{lang}.{key} "
                            f"(contenuti mostrati in '{default}')")
                continue
            tr = load(files[key])
            if tr is not None:
                check(lang, base[key], tr)


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
    colors = {}
    for it in itineraries:
        iid = it.get("id")
        if not it.get("short_name"):
            WARN.append(f"Itinerario '{iid}': manca 'short_name' (nome nel selettore)")
        color = it.get("color")
        if not color:
            WARN.append(f"Itinerario '{iid}': manca 'color' (colore sulla mappa)")
        elif not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            ERRORS.append(f"Itinerario '{iid}': 'color' deve essere nel formato #RRGGBB: {color}")
        elif color.upper() in colors:
            WARN.append(f"Itinerario '{iid}': stesso colore di '{colors[color.upper()]}' ({color})")
        else:
            colors[color.upper()] = iid
        for stop in it.get("stops", []):
            ref = stop.get("monument_id")
            if ref and ref not in monument_ids:
                ERRORS.append(f"Itinerario '{it.get('id')}': monument_id inesistente: {ref}")
        check_path(it.get("cover_image"), f"itinerario {it.get('id')}")
        if len(it.get("path") or []) < 2:
            WARN.append(f"Itinerario '{it.get('id')}': manca 'path' (linea retta tra le tappe). "
                        f"Esegui build_routes.py dalla radice del repo")
        for leg in it.get("legs") or []:
            if leg.get("distance_km") == 0:
                WARN.append(f"Itinerario '{it.get('id')}': {leg.get('from')} e {leg.get('to')} "
                            f"hanno le stesse coordinate")

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

    # Mappa: il config deve richiamare il file mappa globale condiviso
    if not config.get("map", {}).get("config_url"):
        WARN.append("config.json: manca 'map.config_url' (config mappa globale condivisa)")

    # Landing page unica (QR + condivisione)
    share_url = config.get("app", {}).get("share_url")
    if not share_url:
        WARN.append("config.json: manca 'app.share_url' (landing page per QR e condivisione)")
    elif not share_url.startswith("https://") or not share_url.endswith("/"):
        WARN.append(f"config.json: 'app.share_url' deve iniziare con https:// e terminare con /: {share_url}")

    check_translations(manifest, {
        "config": config,
        "monuments": monuments,
        "itineraries": itineraries,
        "quizzes": quizzes,
    })

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
