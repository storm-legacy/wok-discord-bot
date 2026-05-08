# Discord Soundboard Bot

## Cel projektu
Discord bot ("soundboard bot") w Pythonie - wchodzi na kanał głosowy gdy ktoś dołącza i odtwarza losowy dźwięk z katalogu `sounds/`.

## Tech stack
- Python 3.12
- `discord.py[voice]` - biblioteka do bota
- `ffmpeg` - wymagany do odtwarzania audio
- `uv` - zarządzanie zależnościami (pyproject.toml)

## Struktura projektu
```
discord-bot/
├── main.py           # główny plik bota
├── pyproject.toml    # zależności
├── .env.example      # przykładowy plik ze zmiennymi środowiskowymi
├── .python-version   # Python 3.12
└── sounds/           # katalog z plikami audio (.mp3, .wav, .ogg, .m4a)
```

## Uruchomienie
```bash
export DISCORD_TOKEN="twój_token"
uv run main.py
# lub
python main.py
```
