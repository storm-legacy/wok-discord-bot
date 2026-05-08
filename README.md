# Discord Soundboard Bot 🎵

Bot Discord, który wchodzi na kanał głosowy i odtwarza losowy dźwięk, gdy ktoś do niego dołącza (po raz pierwszy — nie przy przechodzeniu między kanałami).

## Wymagania

- Python 3.12+
- `ffmpeg` (do odtwarzania audio)
- Token bota Discord

## Instalacja

```bash
# 1. Zainstaluj ffmpeg (jeśli jeszcze nie masz)
brew install ffmpeg

# 2. Zainstaluj zależności Pythona przez uv
uv sync

# lub przez pip
pip install "discord.py[voice]" python-dotenv
```

## Konfiguracja

### 1. Utwórz bota na Discord Developer Portal

1. Wejdź na https://discord.com/developers/applications
2. Kliknij **New Application** → nadaj nazwę
3. Przejdź do zakładki **Bot** → kliknij **Reset Token** → skopiuj token
4. W sekcji **Privileged Gateway Intents** włącz:
   - **Server Members Intent**
   - **Message Content Intent**
5. Przejdź do **OAuth2 → URL Generator**:
   - Zaznacz scope: `bot`
   - Zaznacz uprawnienia: `Connect`, `Speak`, `View Channels`, `Send Messages`
6. Skopiuj wygenerowany URL i otwórz go w przeglądarce → dodaj bota na serwer

### 2. Ustaw token

```bash
cp .env.example .env
# Edytuj .env i wpisz swój token:
# DISCORD_TOKEN=twój_token_tutaj
```

### 3. Dodaj pliki dźwiękowe

Wrzuć pliki audio do katalogu `sounds/`:

```
sounds/
├── airhorn.mp3
├── bruh.mp3
├── wow.wav
└── epic.ogg
```

Obsługiwane formaty: `.mp3`, `.wav`, `.ogg`, `.m4a`, `.flac`

## Uruchomienie

```bash
uv run main.py
# lub
python main.py
```

## Komendy Discord

| Komenda            | Opis                                      |
| ------------------ | ----------------------------------------- |
| `!sounds`          | Lista dostępnych dźwięków                 |
| `!set <nazwa>`     | Ustaw konkretny dźwięk (bez rozszerzenia) |
| `!set`             | Wróć do trybu losowego                    |
| `!volume`          | Sprawdź aktualną głośność                 |
| `!volume 0.8`      | Ustaw głośność (0.0 – 1.0)                |
| `!watch General`   | Monitoruj tylko kanał o nazwie "General"  |
| `!unwatch General` | Przestań monitorować kanał                |
| `!channels`        | Lista monitorowanych kanałów              |

## Jak działa

- Bot nasłuchuje zdarzenia `on_voice_state_update`
- Reaguje **tylko** gdy `before.channel is None` (czyli ktoś wchodzi na kanał pierwszy raz, nie przechodzi między kanałami)
- Łączy się z kanałem i odtwarza dźwięk (losowy lub ustawiony przez `!set`)
- Jeśli bot już jest podłączony — przenosi się na odpowiedni kanał
