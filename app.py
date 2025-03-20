import discord
from discord.ext import commands
import json
import os
import subprocess
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

data = {}
players = []
university_mapping = {
    "cu": "CU_",
    "mum": "MUM_",
    "suts": "SUTS_",
    "uow": "UOW_"
}

UNIVERSITY_ALIASES = {
    "curtin": "CU",
    "monash": "MUM",
    "swinburne": "SUTS",
    "wollongong": "UOW"
}

UNIVERSITY_NAME_MAPPING = {
    "CU": "Curtin University Malaysia",
    "MUM": "Monash University",
    "SUTS": "Swinburne University of Technology",
    "UOW": "University of Wollongong"
}

def update_data():
    global data, players 

    with open("output.json", "r") as file:
        data = json.load(file)

    players = [ 
        {
            "position": player["position"],
            "reputation_points": player["reputation_points"],
            "avatar_name": player["avatar_name"]
        }
        for player in data.get("players", [])
    ]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

PLAYERS_PER_PAGE = 10
pagination_sessions = {}


def create_embed(page, filtered_players, is_filtered, university_name=None):
    university_full_name = "Global"

    if is_filtered: university_full_name = UNIVERSITY_NAME_MAPPING[filtered_players[0]["avatar_name"].split("_")[0]]

    title = f"{university_full_name} Leaderboard"
    
    embed = discord.Embed(
        title=title,
        color=discord.Color.gold()
    )

    start = page * PLAYERS_PER_PAGE
    end = start + PLAYERS_PER_PAGE

    medal_icons = {1: "🥇", 2: "🥈", 3: "🥉"}

    for player in filtered_players[start:end]:
        # Determine local or global rank
        rank = player['local_position'] if is_filtered else player['position']
        rank_display = f"{medal_icons.get(rank, f'{rank}.')}" 

        global_rank_info = f"\n(Global Rank: #{player['position']})" if is_filtered else ""

        embed.add_field(
            name=f"{rank_display} {player['avatar_name']}",
            value=f"Reputation Points: {player['reputation_points']}{global_rank_info}",
            inline=False
        )

    embed.set_footer(text=f"Page {page + 1} of {(len(filtered_players) // PLAYERS_PER_PAGE) + 1}")
    return embed


@bot.command()
async def update(ctx):
    try:
        await ctx.send("⏳ Running update... Please wait.")
        result = subprocess.run(["bash", "run.sh"], capture_output=True, text=True)

        if result.returncode != 0:
            await ctx.send("❌ Update failed! Edison probably forgot to replace the token or something... 🤦")
            return 

        await ctx.send(f"✅ Update successful!")
        update_data()

        await leaderboard(ctx)

    except Exception as e:
        await ctx.send(f"⚠️ An error occurred: {e}")



@bot.command(name="leaderboard", aliases=["lb"])
async def leaderboard(ctx, university_query=None):
    update_data()

    """Command to display the leaderboard, optionally filtered by university"""
    if not players:
        await ctx.send("No players found in the leaderboard.")
        return

    if university_query:
        university_query = university_query.lower()
        university_prefix = UNIVERSITY_ALIASES.get(university_query, university_query.upper())

        filtered_players = [p for p in players if p["avatar_name"].startswith(university_prefix)]

        if not filtered_players:
            await ctx.send(f"No players found for '{university_query.title()}'.")
            return

        # Assign local positions based on new filtered list
        for i, player in enumerate(filtered_players, start=1):
            player["local_position"] = i
    else:
        filtered_players = players

    page = 0
    embed = create_embed(page, filtered_players, bool(university_query))
    message = await ctx.send(embed=embed)

    await message.add_reaction("⬅️")
    await message.add_reaction("➡️")

    pagination_sessions[message.id] = {"page": page, "ctx": ctx, "filtered_players": filtered_players, "is_filtered": bool(university_query)}




@bot.command(name="playerinfo", aliases=["pinfo", "info"])
async def player_info(ctx, avatar_name: str):
    update_data()
    
    player = next((p for p in players if p["avatar_name"].lower() == avatar_name.lower()), None)

    if not player:
        await ctx.send(f"Player '{avatar_name}' not found in the leaderboard.")
        return

    embed = discord.Embed(title=f"Player Info: {player['avatar_name']}", color=discord.Color.blue())
    embed.add_field(name="Position", value=player["position"], inline=True)
    embed.add_field(name="Reputation Points", value=player["reputation_points"], inline=True)

    await ctx.send(embed=embed)


@bot.event
async def on_reaction_add(reaction, user):
    """Handles leaderboard pagination"""
    if user.bot:
        return

    message = reaction.message
    if message.id not in pagination_sessions:
        return

    session = pagination_sessions[message.id]
    page = session["page"]

    if reaction.emoji == "➡️" and (page + 1) * PLAYERS_PER_PAGE < len(players):
        session["page"] += 1
    elif reaction.emoji == "⬅️" and page > 0:
        session["page"] -= 1

    new_embed = create_embed(session["page"])
    await message.edit(embed=new_embed)
    await message.remove_reaction(reaction, user)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    if message.id not in pagination_sessions:
        return

    session = pagination_sessions[message.id]
    ctx = session["ctx"]
    page = session["page"]
    filtered_players = session["filtered_players"]
    is_filtered = session.get("is_filtered", False)  # Check if filtering was applied

    if reaction.emoji == "➡️" and (page + 1) * PLAYERS_PER_PAGE < len(filtered_players):
        session["page"] += 1
    elif reaction.emoji == "⬅️" and page > 0:
        session["page"] -= 1

    new_embed = create_embed(session["page"], filtered_players, is_filtered)
    await message.edit(embed=new_embed)
    await message.remove_reaction(reaction, user)


@bot.event
async def on_ready():
    """Prints a message when bot is ready"""
    print(f"Logged in as {bot.user}")

bot.run(TOKEN)

