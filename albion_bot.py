import discord
from discord.ext import tasks
import requests
import json
import asyncio
import os
from datetime import datetime, timezone

# =============================================
#   INSTÄLLNINGAR - ÄNDRA DESSA
# =============================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
KANAL_ID = 1516573139155554384
MIN_SPELARE = 20
KOLL_INTERVALL_MINUTER = 5
# =============================================

# Guild-medlemmar
SPELARE = [
    "Isselele", "Goldenhexx", "SnileMB", "FeroxTR", "inferge",
    "DxKills", "nalz", "Golle", "I0WA", "Raphyr", "herm1one",
    "Zzzhhang", "verypersen", "Wahkan", "kolimax", "reyvnx3",
    "Cynical", "Samus225", "Ertug", "parknim", "wexima",
    "omar789", "methxi", "realkiwii", "Cobr1no", "popice",
    "Recklesss", "xDcottonpickerxD", "Tjenick", "Anirsman",
    "JeyPex", "Pecenje", "bluez", "Croatica", "DuanDuan",
    "HYDR4", "SultanZahel", "Walver", "batazgul", "alx",
    "zhuangzhuangma", "JadeOrLeSmegma", "Fishday0", "TangoPlayer12",
    "Luisito", "sphynxy", "fidales", "sampogoloviy", "lifecursed",
    "Adik", "Gnomekkk", "Hone1", "ElectedSh", "meilanzhuju", "M4RtyneQ"
]

SPELARE_LOWER = {p.lower(): p for p in SPELARE}

# Håller koll på battles vi redan skickat
redan_skickade = set()

intents = discord.Intents.default()
client = discord.Client(intents=intents)


def hamta_senaste_battles():
    """Hämtar senaste battles från Albion API"""
    try:
        # Hämta senaste battles (de 50 senaste)
        url = "https://gameinfo-ams.albiononline.com/api/gameinfo/battles?offset=0&limit=50&sort=recent"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Fel vid hämtning av battles: {e}")
        return []


def analysera_battle(battle):
    """Kollar om en battle har minst MIN_SPELARE av våra spelare"""
    if "players" not in battle:
        return None

    hittade_spelare = {}
    for key, value in battle["players"].items():
        namn = value.get("name", "").lower()
        if namn in SPELARE_LOWER:
            riktigt_namn = SPELARE_LOWER[namn]
            hittade_spelare[riktigt_namn] = {
                "kills": value.get("kills", 0),
                "deaths": value.get("deaths", 0),
                "kill_fame": value.get("killFame", 0)
            }

    if len(hittade_spelare) >= MIN_SPELARE:
        return hittade_spelare
    return None


def bygg_embed(battle, spelare_stats):
    """Bygger ett snyggt Discord embed med statistiken"""
    battle_id = battle.get("id", "?")
    total_kills = sum(s["kills"] for s in spelare_stats.values())
    total_deaths = sum(s["deaths"] for s in spelare_stats.values())
    total_fame = sum(s["kill_fame"] for s in spelare_stats.values())

    # Sortera efter kill fame
    sorterade = sorted(spelare_stats.items(), key=lambda x: x[1]["kill_fame"], reverse=True)

    embed = discord.Embed(
        title=f"⚔️ Battle Rapport — ID: {battle_id}",
        color=0xFF4500,
        timestamp=datetime.now(timezone.utc)
    )

    embed.add_field(
        name="📊 Sammanfattning",
        value=(
            f"**Spelare med:** {len(spelare_stats)}\n"
            f"**Totala kills:** {total_kills}\n"
            f"**Totala deaths:** {total_deaths}\n"
            f"**Total kill fame:** {total_fame:,}"
        ),
        inline=False
    )

    # Spelarstatistik (max 20 i ett fält annars för långt)
    spelare_text = ""
    for namn, stats in sorterade[:25]:
        spelare_text += f"**{namn}** — {stats['kills']}K / {stats['deaths']}D / {stats['kill_fame']:,} fame\n"

    if spelare_text:
        embed.add_field(name="👥 Spelarstatistik", value=spelare_text, inline=False)

    embed.set_footer(text=f"Albion Battle Tracker • Battle {battle_id}")

    return embed


@tasks.loop(minutes=KOLL_INTERVALL_MINUTER)
async def kolla_battles():
    await client.wait_until_ready()
    kanal = client.get_channel(KANAL_ID)
    if not kanal:
        print(f"Kunde inte hitta kanalen med ID {KANAL_ID}")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Kollar efter nya battles...")
    battles = hamta_senaste_battles()

    for battle in battles:
        battle_id = battle.get("id")
        if not battle_id or battle_id in redan_skickade:
            continue

        spelare_stats = analysera_battle(battle)
        if spelare_stats:
            print(f"Battle {battle_id} hittad med {len(spelare_stats)} spelare — skickar till Discord!")
            embed = bygg_embed(battle, spelare_stats)
            await kanal.send(embed=embed)
            redan_skickade.add(battle_id)


@client.event
async def on_ready():
    print(f"Bot inloggad som {client.user}")
    print(f"Kollar efter battles var {KOLL_INTERVALL_MINUTER}:e minut")
    print(f"Minst {MIN_SPELARE} spelare krävs för att skicka")
    kolla_battles.start()


client.run(BOT_TOKEN)
