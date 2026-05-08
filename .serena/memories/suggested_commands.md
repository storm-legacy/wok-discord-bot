# Sugerowane komendy

## Instalacja zależności
```bash
uv sync
# lub
pip install "discord.py[voice]"
brew install ffmpeg
```

## Uruchomienie bota
```bash
export DISCORD_TOKEN="twój_token"
uv run main.py
```

## Formatowanie / linting (opcjonalnie)
```bash
uv run ruff check .
uv run ruff format .
```
