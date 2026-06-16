# YouTube Automation Pipeline — 100% gratuit & open-source

Pipeline complet qui genere des videos YouTube *faceless* automatiquement, de la
detection du sujet jusqu'a l'upload programme. **Aucun service payant requis** :
toutes les briques sont gratuites (et certaines fonctionnent 100% en local).

```
Trends -> Script IA -> Voix off -> Images -> Montage -> Sous-titres -> Miniature -> Upload
```

---

## 1. Prerequis systeme

| Outil | Version | Role |
|-------|---------|------|
| Python | 3.11+ | Execution du pipeline |
| FFmpeg | recent | Montage video & incrustation des sous-titres |
| ImageMagick | optionnel | Texte a l'ecran via MoviePy `TextClip` |
| Ollama | optionnel | Generation de script 100% locale (sans cle API) |

**Installer FFmpeg :**

```bash
# Ubuntu / Debian
sudo apt-get install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg
```

---

## 2. Installation pas a pas

```bash
git clone <votre-repo>
cd youtube_auto

# Environnement virtuel (recommande)
python -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate

pip install -r requirements.txt

# Configuration
cp .env.example .env             # puis renseignez vos cles
# Ajustez config.yaml (niche, langue, voix, horaire...)
```

> **Police de titres** : deposez une police TrueType dans
> `assets/fonts/title.ttf` pour des miniatures/slides homogenes. A defaut, le
> pipeline utilise une police systeme (DejaVu/Arial) puis la police Pillow par
> defaut.
>
> **Musique de fond** : deposez des fichiers `.mp3`/`.wav` libres de droits dans
> `assets/music/` (ex. depuis [lofimusic.app](https://lofimusic.app)). Si le
> dossier est vide, la video est produite sans musique.

---

## 3. Obtenir les cles API gratuites

| Service | Lien | Limite gratuite | Variable `.env` |
|---------|------|-----------------|-----------------|
| **Pexels** | https://www.pexels.com/api/ | 200 req/heure | `PEXELS_API_KEY` |
| **Pixabay** | https://pixabay.com/api/docs/ | 100 req/heure | `PIXABAY_API_KEY` |
| **Anthropic (Claude)** | https://console.anthropic.com | Free tier | `ANTHROPIC_API_KEY` |
| **YouTube Data API v3** | https://console.cloud.google.com | 10 000 unites/jour | `client_secrets.json` |

### YouTube Data API (OAuth)
1. Creez un projet sur [Google Cloud Console](https://console.cloud.google.com).
2. Activez **YouTube Data API v3**.
3. Creez des identifiants **OAuth 2.0 (application de bureau)**.
4. Telechargez le `client_secrets.json` et placez-le a la racine de `youtube_auto/`.
5. Au premier upload, une fenetre de consentement s'ouvre ; le token est ensuite
   mis en cache dans `token.pickle`.

### Generation de script sans cle (100% local)
Pas de cle Claude ? Installez [Ollama](https://ollama.com), puis dans `config.yaml` :

```yaml
api:
  use_ollama: true
  ollama_model: "llama3"
```

```bash
ollama pull llama3   # ou mistral
```

---

## 4. Utilisation

```bash
# Generation immediate avec un sujet impose
python main.py --topic "Les 5 metiers qui vont disparaitre avec l'IA"

# Generation immediate avec detection automatique du sujet tendance
python main.py

# Scheduler quotidien (publie chaque jour a 09:00)
python main.py --schedule --time 09:00

# Production en lot (5 videos d'affilee sur les meilleurs sujets)
python main.py --batch 5

# Avec un fichier de config alternatif
python main.py --config /chemin/vers/config.yaml
```

Lancer les tests :

```bash
pip install pytest
pytest tests/
```

---

## 5. Le dossier `output/`

Chaque execution cree un sous-dossier horodate `output/AAAAMMJJ_HHMMSS/` :

| Fichier | Description |
|---------|-------------|
| `video_raw.mp4` | Video assemblee (avant sous-titres) |
| `video_final.mp4` | Video finale avec sous-titres incrustes |
| `subtitles.srt` | Sous-titres generes par Whisper |
| `thumbnail.png` | Miniature 1280x720 |
| `tmp/` | Fichiers intermediaires (audio, images) — **supprime** en fin de run |

Les journaux detailles sont ecrits dans `logs/AAAA-MM-JJ.log`.

---

## 6. Limitations connues & workarounds

- **Quota YouTube** : un upload coute ~1600 unites ; le quota gratuit (10 000/j)
  autorise donc ~6 uploads/jour. Demandez une augmentation de quota si besoin.
- **Pytrends** non officiel : Google peut renvoyer des erreurs `429`. Le pipeline
  bascule alors automatiquement sur des sujets de repli bases sur la niche.
- **Texte a l'ecran (`texte_ecran`)** : `TextClip` de MoviePy requiert
  ImageMagick. S'il est absent, le texte est simplement ignore (la video est
  quand meme produite).
- **Sous-titres FFmpeg** : si l'incrustation echoue, la video sans sous-titres est
  conservee et le `.srt` reste disponible pour un import manuel.
- **edge-tts** : peut etre bloque sur certains reseaux ; repli automatique sur
  `gTTS` (voix moins naturelle mais fonctionnelle).
- **Performances Whisper** : le modele `small` tourne sur CPU mais reste lent sur
  de longues videos. Passez a `tiny`/`base` (`production.whisper_model`) pour
  accelerer, ou `medium`/`large-v3` pour plus de precision avec un GPU.
- **Premiere execution** : le telechargement des modeles Whisper et l'init de
  MoviePy peuvent prendre quelques minutes.

---

## Architecture

```
youtube_auto/
├── main.py                  # Orchestrateur (CLI : --topic / --schedule / --batch)
├── config.yaml              # Niche, langue, voix, horaire, APIs
├── .env.example             # Template des cles API
├── requirements.txt
├── modules/
│   ├── config_loader.py     # Chargement YAML + resolution ${ENV}
│   ├── trend_finder.py      # Detection des sujets tendance (pytrends)
│   ├── script_generator.py  # Script + timestamps (Claude / Ollama)
│   ├── tts_engine.py        # Voix off (edge-tts -> gTTS)
│   ├── image_fetcher.py     # Images libres de droits (Pexels/Pixabay -> Pillow)
│   ├── video_builder.py     # Montage MoviePy + Ken Burns + musique
│   ├── subtitle_engine.py   # SRT (faster-whisper) + burn FFmpeg
│   ├── thumbnail_maker.py   # Miniature CTR (Pillow)
│   └── youtube_uploader.py  # Upload + scheduling (YouTube Data API)
├── assets/ (fonts/ music/ backgrounds/)
├── output/                  # Videos generees
├── logs/                    # Journaux quotidiens
└── tests/                   # Tests unitaires
```

Toutes les classes sont type-hintees, documentees, et chaque etape du pipeline
dispose d'un repli gracieux pour ne jamais bloquer la production.
