# Heritage — Architettura white-label per comune

Questo repo è l'**architettura white-label** dell'app turistica Heritage. L'app nativa ha 6
sezioni principali — **Home, Itinerario, Tappe, Tour (360°), Quiz, Info** — e legge i
contenuti da file JSON + media associati. Aggiornando i contenuti, l'app si aggiorna da
remoto senza ripubblicare sugli store.

Ogni comune ha la propria **sottocartella** `Comune di <Nome>/`, completa e autonoma. Per
aggiungere un comune si **clona** una sottocartella esistente e se ne adattano i contenuti.

---

## Struttura del repo

```
/
├── README.md                    # Questa guida (architettura white-label)
├── map.config.json              # Config mappa globale condivisa (provider + chiave Carto)
│
├── Comune di Bugliano/          # Istanza comune (contenuti template di riferimento)
│   ├── manifest.json            # Punto d'ingresso: versione + elenco dei file
│   ├── config.json              # Info comune, branding white-label, base_url media, share_url
│   ├── monuments.json           # Punti di interesse (POI) → sezioni Tappe / Tour 360°
│   ├── itineraries.json         # Itinerari turistici sulla mappa → sezione Itinerario
│   ├── quizzes.json             # Quiz → sezione Quiz
│   ├── validate.py              # Validatore contenuti (eseguire dentro la cartella)
│   └── media/                   # Tutti gli asset (relativi a media.base_url)
│       ├── images/
│       │   ├── flat/            # Foto standard
│       │   ├── 360/             # Immagini equirettangolari per tour 360°
│       │   └── itineraries/     # Copertine degli itinerari
│       ├── audio/
│       │   └── it/              # Audioguide in italiano
│       └── branding/            # Logo e splash dell'app
│
└── Comune di Niscemi/           # Altra istanza (stessa struttura, contenuti propri)
    └── …
```

> **Ogni `Comune di <Nome>/` è autonoma e clonabile:** contiene tutti i JSON, i media e il
> validatore. In fase di build si punta alla sottocartella del comune desiderato. Quando un
> comune va in produzione, la sua cartella può essere estratta in un repo dedicato
> (es. `niscemi-heritage`) aggiornando solo `media.base_url`.

> **Config mappa condivisa:** oltre alle cartelle comune esiste un file globale
> `map.config.json` (nella radice di questo repo) con provider e chiave della mappa Carto,
> letto da tutte le build. Ogni `config.json` lo richiama via `map.config_url`. Vedi
> *Mappa: configurazione globale condivisa*.

> **Landing page e QR:** la pagina "scarica l'app" di ogni comune **non** sta in questo
> repo ma nel repo dedicato `heritage-pages` (GitHub Pages). Ogni `config.json` la
> richiama via `app.share_url`. Vedi *Landing page e QR code*.

---

## Regola d'oro: i path

`config.json` definisce **un solo** `media.base_url`. Ogni path di immagine o audio negli
altri file è **relativo** a quel base_url.

L'app costruisce l'URL completo così:

```
url_completo = config.media.base_url + path_relativo
```

Esempio: con `base_url = "https://raw.githubusercontent.com/Magnetico-Associazione-Culturale/Heritage/main/Comune%20di%20Bugliano/"`
e `path = "media/images/flat/chiesa-san-giovanni.jpg"`, l'app scarica
`https://raw.githubusercontent.com/Magnetico-Associazione-Culturale/Heritage/main/Comune%20di%20Bugliano/media/images/flat/chiesa-san-giovanni.jpg`.

Il `base_url` deve terminare con `/` e gli spazi nel nome della cartella vanno scritti come `%20`.

**Vantaggio:** per spostare l'hosting (es. da GitHub a un CDN) cambi *una sola riga* in
`config.json`. Non toccare mai gli altri file.

---

## Mappa: configurazione globale condivisa

La mappa usa i basemap **Carto** (stile *voyager*), che richiedono una **chiave**. La chiave
**non è contenuto del comune** ma infrastruttura a livello di app, uguale per tutti. Per
questo **non** sta nei singoli `config.json`, ma in **un unico file remoto condiviso** —
`map.config.json` nella radice di questo repo — che ogni build scarica all'avvio:

```
https://raw.githubusercontent.com/Magnetico-Associazione-Culturale/Heritage/main/map.config.json
```

```json
{
  "provider": "carto",
  "style": "voyager",
  "tile_url": "https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key={key}",
  "api_key": "LA_CHIAVE_QUI",
  "attribution": "© OpenStreetMap contributors © CARTO",
  "min_zoom": 0,
  "max_zoom": 20
}
```

Ogni `config.json` di comune **richiama** questo file tramite `map.config_url` (l'URL è lo
stesso per tutti — è solo un puntatore, non la chiave). All'avvio l'app:

```
map_config      = fetch(config.map.config_url)          // file globale condiviso
tile_url_finale = map_config.tile_url
                    .replace("{key}", map_config.api_key) // poi {z}/{x}/{y} per ogni tile
```

**Vantaggio:** quando la chiave scade o cambia, si aggiorna **solo il campo `api_key` di
questo file** e la modifica si propaga a **tutti i comuni da remoto**, senza ripubblicare
sugli store e senza toccare nessuna sottocartella comune. Le cartelle `Comune di <Nome>/`
restano autonome: la chiave non è duplicata al loro interno.

> **Sicurezza:** la chiave viaggia nel traffico di rete dell'app, non è un segreto.
> Proteggila lato Carto (restrizioni per bundle-id/dominio, limiti di quota), non con la
> segretezza del file.

---

## Landing page e QR code

Per ora **non** si usa un QR per monumento: ogni comune ha **un solo QR** (da stampare su
cartellonistica, brochure, ecc.) che punta a una **landing page** con i pulsanti per
scaricare l'app da App Store e Google Play.

Le landing page sono servite da **GitHub Pages** sul repo dedicato
[`heritage-pages`](https://github.com/Magnetico-Associazione-Culturale/heritage-pages),
con una sottocartella per comune:

```
heritage-pages/
├── Niscemi/
│   └── index.html      → https://magnetico-associazione-culturale.github.io/heritage-pages/Niscemi/
└── <Nome>/
    └── index.html      → https://magnetico-associazione-culturale.github.io/heritage-pages/<Nome>/
```

**Convenzione URL:**

```
https://magnetico-associazione-culturale.github.io/heritage-pages/<Nome>/
```

- `<Nome>` è il nome del comune con l'**iniziale maiuscola** (es. `Niscemi`, `Bugliano`).
  GitHub Pages distingue maiuscole e minuscole: `niscemi/` **non** funziona.
- L'URL termina sempre con `/`.

L'URL è salvato in `config.json` → `app.share_url` ed è usato dal **pulsante "Condividi
l'app"**: l'app apre il foglio di condivisione nativo (WhatsApp, messaggi, email…) con
questo link, così chi lo riceve arriva alla landing con i pulsanti degli store. È anche
l'URL da codificare nel QR: un'unica fonte di verità per entrambi.

> **Il QR non va mai rigenerato:** punta a un URL stabile. Se cambiano i link agli store o
> la grafica, si aggiorna solo `index.html` nel repo `heritage-pages`. Se in futuro si
> torna ai QR per monumento, basterà aggiungere un campo per POI in `monuments.json`.

---

## manifest.json

| Campo | Tipo | Descrizione |
|---|---|---|
| `schema_version` | string | Versione della struttura JSON. Cambiala solo se cambi i campi. |
| `content_version` | string | Data/versione dei contenuti. Aggiornala a ogni modifica per invalidare la cache. |
| `comune_id` | string | Slug del comune (minuscolo, senza spazi). |
| `default_language` | string | Lingua predefinita (`it`). |
| `available_languages` | string[] | Lingue disponibili. |
| `files` | object | Nomi dei file di contenuto (così l'app sa cosa caricare). |

---

## config.json

Contiene le info del comune, il branding dell'app (white-label) e il `base_url` dei media.
`comune.map_center` + `default_zoom` definiscono dove **centrare** la mappa all'avvio.
`app.theme` contiene i colori e il logo per personalizzare l'aspetto della build.
`app.share_url` è il link condiviso dal pulsante "Condividi l'app": punta alla landing page
"scarica l'app" del comune, la stessa del QR unico (vedi *Landing page e QR code*).
`map.config_url` **richiama** il file mappa globale condiviso: provider e chiave (Carto)
**non** stanno qui (vedi *Mappa: configurazione globale condivisa*).

---

## monuments.json

Array di POI. **Compatibile con la struttura attuale di Regalbuto** (lat/lon flat, audio,
images, history). Campi:

| Campo | Tipo | Obbl. | Note |
|---|---|---|---|
| `id` | string | sì | Slug univoco. Usato come riferimento da itinerari e quiz. |
| `name` | string | sì | Nome visualizzato. |
| `category` | string | sì | `chiesa`, `palazzo`, `civico`, `tecnologia`, `museo`, `monumento`, ... |
| `short_description` | string | sì | Una riga per la lista. |
| `description` | string | no | Testo lungo per la scheda di dettaglio. |
| `lat`, `lon` | number\|null | sì | Coordinate. `null` se sconosciute (il pin non viene mostrato). |
| `address` | string | sì | Indirizzo testuale. |
| `tags` | string[] | no | Per filtri/ricerca. |
| `audio` | object\|null | no | Audioguida (vedi sotto). `null` se assente. |
| `images` | object[] | sì | Vedi sotto. |
| `history` | object[] | no | Voci storiche con periodo e `agents`. |

### audio
```json
{
  "path": "media/audio/it/01_chiesa.mp3",
  "duration": 180,
  "language": "it",
  "title": "Audioguida - ...",
  "description": "..."
}
```

### images
```json
{
  "role": "thumbnail",      // opzionale; "thumbnail" = immagine principale in lista
  "format": "standard",     // "standard" = foto normale | "360" = tour panoramico
  "path": "media/images/flat/x.jpg",
  "title": "...",
  "alt": "..."              // testo alternativo per accessibilità
}
```

> **Tour 360°:** le immagini panoramiche stanno *dentro* l'array `images` del monumento con
> `format: "360"`. Devono essere equirettangolari (rapporto 2:1, es. 4096×2048). L'app le
> rileva dal campo `format` e le apre nel viewer panoramico.

---

## itineraries.json

Array di percorsi. Le tappe **non duplicano** i dati del monumento: lo referenziano con
`monument_id`.

| Campo | Note |
|---|---|
| `id`, `name`, `description` | Identificativi e testi. |
| `difficulty` | `easy` / `medium` / `hard`. |
| `distance_km` | Distanza reale del percorso (generata da `build_routes.py`). |
| `duration_minutes` | Stima della durata complessiva, **visite incluse** (manuale). |
| `travel_mode` | `walking` / `driving` / `bicycling`. Determina il profilo di routing. |
| `cover_image` | Copertina (path relativo). |
| `stops` | Lista ordinata: `{ order, monument_id, note }`. |
| `path` | Lista di `{lat, lon}` che segue le strade reali, da disegnare come polilinea. **Generata** da `build_routes.py`. Se assente, l'app collega le tappe in linea retta. |
| `legs` | **Generata.** Un elemento per ogni tratto tra tappe consecutive: `{ from, to, distance_km, travel_minutes }`. Serve per mostrare "prossima tappa: 350 m, 5 min". |

### Tracciato stradale degli itinerari

Il percorso reale tra le tappe **non va disegnato a mano**: si calcola offline con OSRM
(dati OpenStreetMap, stessi della basemap Carto) e si salva nel JSON. L'app non deve
chiamare nessun servizio di routing a runtime: disegna `path` sopra i tile Carto.

```
python3 build_routes.py                       # tutti i comuni
python3 build_routes.py "Comune di Niscemi"   # un solo comune
```

Va rieseguito ogni volta che si cambiano le tappe di un itinerario o le coordinate di un
monumento. Lo script aggiorna `path`, `distance_km` e `legs`; non tocca `duration_minutes`.

**In automatico:** la GitHub Action `.github/workflows/build-routes.yml` lo esegue a ogni
push su `main` che modifica `itineraries.json` o `monuments.json`, poi lancia `validate.py`
su ogni comune e committa i percorsi aggiornati. Si può avviare anche a mano da
*Actions → Genera percorsi itinerari → Run workflow*. Dopo ogni push fai `git pull` prima
di modificare di nuovo, perché l'Action aggiunge un suo commit.

---

## quizzes.json

Array di quiz. `monument_id` può essere `null` (quiz generale) o l'id di un monumento
(quiz contestuale alla sua scheda).

```json
{
  "id": "quiz-generale",
  "title": "...",
  "monument_id": null,
  "questions": [
    {
      "id": "q1",
      "text": "...",
      "image": "media/images/flat/x.jpg",   // o null
      "options": [
        { "id": "a", "text": "...", "correct": true },
        { "id": "b", "text": "...", "correct": false }
      ],
      "explanation": "Mostrata dopo la risposta."
    }
  ]
}
```

---

## Checklist per un nuovo comune

1. **Clona** una sottocartella esistente (es. `Comune di Bugliano/`) e rinominala `Comune di <Nome>/`.
2. In `config.json`: aggiorna `comune`, `app.display_name`, i colori, **`media.base_url`** (deve puntare al repo/host del nuovo comune) e **`app.share_url`** (`…/heritage-pages/<Nome>/`, iniziale maiuscola).
3. In `manifest.json`: aggiorna `comune_id` e `content_version`.
4. Compila `monuments.json`, `itineraries.json`, `quizzes.json`.
5. Carica i media nelle cartelle `media/...` con gli stessi path indicati nei JSON.
6. **Mappa:** verifica che `config.json` abbia `map.config_url` (lo stesso per tutti i
   comuni). Non duplicare la chiave: provider e chiave sono globali in `map.config.json`
   (radice di questo repo).
7. In build → indica la sottocartella del comune.
8. Pubblica sugli store sotto *Magnetico Associazione Culturale*.
9. **Landing page:** nel repo `heritage-pages` clona `Niscemi/` in `<Nome>/`, adatta testi,
   colori (gli stessi di `app.theme`) e link agli store dell'app appena pubblicata.
10. **QR:** genera il QR da `app.share_url`, aprilo da smartphone e verifica che la pagina
    si carichi prima di mandarlo in stampa.

## Validazione consigliata

Prima di pubblicare, **entra nella cartella del comune** ed esegui `python3 validate.py`:
verifica che ogni `path` esista davvero e che ogni `monument_id` referenziato in
itinerari/quiz corrisponda a un id presente in `monuments.json`. Un piccolo script di
validazione evita schermate vuote nell'app.

```
cd "Comune di Niscemi"
python3 validate.py
```
