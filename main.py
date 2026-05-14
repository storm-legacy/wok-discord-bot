"""
Discord Soundboard Bot
======================
Bot wchodzi na kanał głosowy i odtwarza dźwięk, gdy ktoś do niego dołącza.

Komendy:
  !sounds              - lista dostępnych dźwięków
  !set <nazwa>         - ustaw konkretny dźwięk (bez rozszerzenia)
  !set                 - wróć do trybu losowego
  !watch <kanał>       - monitoruj tylko ten kanał głosowy
  !unwatch <kanał>     - przestań monitorować kanał
  !channels            - lista monitorowanych kanałów

Zmienne środowiskowe (plik .env lub export):
  DISCORD_TOKEN        - token bota (wymagany)
  SOUNDS_DIR           - ścieżka do katalogu z dźwiękami (domyślnie: sounds/)
  VOLUME               - głośność 0.0–1.0 (domyślnie: 0.5)
"""

import asyncio
import logging
import os
import random
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Konfiguracja
# ---------------------------------------------------------------------------

load_dotenv()

TOKEN: str | None = os.getenv("DISCORD_TOKEN")
SOUNDS_DIR = Path(os.getenv("SOUNDS_DIR", "sounds"))
VOLUME = float(os.getenv("VOLUME", "0.5"))

SOUNDS_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("soundbot")

# ---------------------------------------------------------------------------
# Intents & bot
# ---------------------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ---------------------------------------------------------------------------
# Stan per-serwer
# ---------------------------------------------------------------------------

# guild_id -> {"sound": str | None, "channels": set[str], "queue": Queue, "worker": Task | None}
_guild_state: dict[int, dict] = {}


def _state(guild_id: int) -> dict:
    if guild_id not in _guild_state:
        _guild_state[guild_id] = {
            "sound": None,
            "channels": set(),
            "queue": asyncio.Queue(),
            "worker": None,
        }
    return _guild_state[guild_id]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {".mp3", ".wav", ".ogg", ".m4a", ".flac"}


def list_sounds() -> list[str]:
    """Zwraca posortowaną listę nazw dźwięków (bez rozszerzenia)."""
    return sorted(
        f.stem
        for f in SOUNDS_DIR.iterdir()
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )


def get_sound_path(name: str) -> Path | None:
    """Szuka pliku dźwiękowego po nazwie (bez rozszerzenia)."""
    for ext in SUPPORTED_EXTENSIONS:
        candidate = SOUNDS_DIR / f"{name}{ext}"
        if candidate.exists():
            return candidate
    return None


def pick_sound(guild_id: int) -> Path | None:
    """Wybiera dźwięk do odtworzenia (ustawiony lub losowy)."""
    sounds = list_sounds()
    if not sounds:
        return None
    preferred = _state(guild_id)["sound"]
    if preferred and preferred in sounds:
        return get_sound_path(preferred)
    return get_sound_path(random.choice(sounds))


# ---------------------------------------------------------------------------
# Eventy
# ---------------------------------------------------------------------------


@bot.event
async def on_ready() -> None:
    log.info("Bot online: %s (id=%s)", bot.user, bot.user.id if bot.user else "?")
    log.info("Dostępne dźwięki: %s", list_sounds() or "(brak — wrzuć pliki do sounds/)")


@bot.event
async def on_voice_state_update(
    member: discord.Member,
    before: discord.VoiceState,
    after: discord.VoiceState,
) -> None:
    # Ignoruj boty i zdarzenia inne niż dołączenie do kanału
    if member.bot:
        return
    if after.channel is None:
        return
    # Dołączenie po raz pierwszy — before.channel musi być None
    # (pomijamy przejście między kanałami)
    if before.channel is not None:
        return

    state = _state(member.guild.id)
    watched = state["channels"]

    # Jeśli zdefiniowano listę kanałów — sprawdź czy ten jest na liście
    if watched and after.channel.name not in watched:
        log.debug(
            "Kanał '%s' nie jest monitorowany — pomijam.", after.channel.name
        )
        return

    sound_path = pick_sound(member.guild.id)
    if sound_path is None:
        log.warning("Brak plików dźwiękowych w '%s'.", SOUNDS_DIR)
        return

    state = _state(member.guild.id)
    await state["queue"].put((after.channel, sound_path))
    log.info("Queued '%s' for %s (queue size: %d)", sound_path.stem, member.display_name, state["queue"].qsize())

    if state["worker"] is None or state["worker"].done():
        state["worker"] = asyncio.create_task(_queue_worker(member.guild.id))


async def _queue_worker(guild_id: int) -> None:
    state = _state(guild_id)
    q: asyncio.Queue = state["queue"]
    while not q.empty():
        channel, sound_path = await q.get()
        try:
            await _play_sound(channel.guild, channel, sound_path)
        except Exception as e:
            log.exception("Worker error: %s", e)
        finally:
            q.task_done()


async def _play_sound(
    guild: discord.Guild,
    channel: discord.VoiceChannel,
    sound_path: Path,
) -> None:
    """Connects to channel, plays sound, waits for finish, then disconnects."""
    try:
        vc = guild.voice_client

        if vc and vc.is_connected():
            if vc.channel != channel:
                await vc.move_to(channel)
        else:
            vc = await channel.connect()

        if vc.is_playing():
            vc.stop()

        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(str(sound_path)),
            volume=VOLUME,
        )

        done: asyncio.Future = bot.loop.create_future()

        def _after(error: Exception | None) -> None:
            if error:
                log.error("Błąd odtwarzania: %s", error)
            bot.loop.call_soon_threadsafe(done.set_result, None)

        vc.play(source, after=_after)
        log.info("▶ Gram '%s' na #%s dla %s", sound_path.stem, channel.name, channel.guild.name)

        await done
        await vc.disconnect()

    except discord.ClientException as e:
        log.error("Błąd klienta Discord: %s", e)
    except Exception as e:
        log.exception("Nieoczekiwany błąd: %s", e)


# ---------------------------------------------------------------------------
# Komendy tekstowe
# ---------------------------------------------------------------------------


@bot.command(name="sounds")
async def cmd_sounds(ctx: commands.Context) -> None:
    """Wyświetla listę dostępnych dźwięków."""
    sounds = list_sounds()
    if sounds:
        await ctx.send(f"🎵 Dostępne dźwięki: `{'`, `'.join(sounds)}`")
    else:
        await ctx.send(f"⚠️ Brak dźwięków! Wrzuć pliki `.mp3`/`.wav`/`.ogg` do `{SOUNDS_DIR}/`")


@bot.command(name="set")
async def cmd_set(ctx: commands.Context, name: str | None = None) -> None:
    """Ustawia konkretny dźwięk lub wraca do trybu losowego."""
    if name is None:
        _state(ctx.guild.id)["sound"] = None
        await ctx.send("🎲 Tryb losowy — bot będzie grał losowy dźwięk.")
        return

    if name not in list_sounds():
        await ctx.send(f"❌ Nie znaleziono `{name}`. Użyj `!sounds` aby zobaczyć listę.")
        return

    _state(ctx.guild.id)["sound"] = name
    await ctx.send(f"✅ Ustawiono dźwięk: **{name}**")


@bot.command(name="watch")
async def cmd_watch(ctx: commands.Context, *, channel_name: str) -> None:
    """Dodaje kanał głosowy do listy monitorowanych."""
    _state(ctx.guild.id)["channels"].add(channel_name)
    await ctx.send(f"👁️ Monitoruję kanał: **{channel_name}**")


@bot.command(name="unwatch")
async def cmd_unwatch(ctx: commands.Context, *, channel_name: str) -> None:
    """Usuwa kanał głosowy z listy monitorowanych."""
    _state(ctx.guild.id)["channels"].discard(channel_name)
    await ctx.send(f"🚫 Przestałem monitorować: **{channel_name}**")


@bot.command(name="channels")
async def cmd_channels(ctx: commands.Context) -> None:
    """Wyświetla listę monitorowanych kanałów."""
    watched = _state(ctx.guild.id)["channels"]
    if watched:
        await ctx.send(f"👁️ Monitorowane kanały: `{'`, `'.join(sorted(watched))}`")
    else:
        await ctx.send("ℹ️ Monitoruję **wszystkie** kanały głosowe.")


@bot.command(name="volume")
async def cmd_volume(ctx: commands.Context, value: float | None = None) -> None:
    """Ustawia lub wyświetla aktualną głośność (0.0 – 1.0)."""
    global VOLUME
    if value is None:
        await ctx.send(f"🔊 Aktualna głośność: **{VOLUME:.0%}**")
        return
    if not 0.0 <= value <= 1.0:
        await ctx.send("❌ Głośność musi być w zakresie 0.0 – 1.0")
        return
    VOLUME = value
    await ctx.send(f"🔊 Głośność ustawiona na **{VOLUME:.0%}**")


# ---------------------------------------------------------------------------
# Punkt wejścia
# ---------------------------------------------------------------------------


def main() -> None:
    if not TOKEN:
        print(
            "Brak DISCORD_TOKEN!\n"
            "  Ustaw zmienną środowiskową:  export DISCORD_TOKEN='twój_token'\n"
            "  lub stwórz plik .env z wpisem: DISCORD_TOKEN=twój_token"
        )
        raise SystemExit(1)

    log.info("Startuje bota... katalog dźwięków: %s", SOUNDS_DIR.resolve())
    bot.run(TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
