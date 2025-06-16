import discord
from discord import app_commands
from discord.ext import commands
import os
import random
import string
from dotenv import load_dotenv
import json
from datetime import datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID'))
KEYS_FILE = 'keys.json'
LOG_FILE = 'key_log.txt'

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

def load_keys():
    try:
        with open(KEYS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_keys(keys):
    with open(KEYS_FILE, 'w') as f:
        json.dump(keys, f, indent=4)

def log_action(action, key, user=None, role=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {action}: {key}"
    if role:
        log_entry += f" (Role: {role})"
    if user:
        log_entry += f" by {user}"
    log_entry += "\n"
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry)

def generate_key(length=16):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)

def create_embed(title, description, color=discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="Bot by @ShaneP3k")
    return embed

@bot.tree.command(name="gen", description="Generate keys for a specific role")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(role="The role to assign when key is redeemed", amount="Number of keys to generate (max 25)")
async def generate_keys(interaction: discord.Interaction, role: discord.Role, amount: int):
    if not interaction.user.guild_permissions.administrator:
        embed = create_embed("Permission Denied", "You need administrator permissions to use this command.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    if amount <= 0 or amount > 25:
        embed = create_embed("Invalid Amount", "Please provide an amount between 1 and 25.", discord.Color.red())
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    keys = load_keys()
    if str(role.id) not in keys:
        keys[str(role.id)] = {"used": [], "unused": []}
    
    new_keys = [generate_key() for _ in range(amount)]
    keys[str(role.id)]["unused"].extend(new_keys)
    save_keys(keys)
    
    key_list = "\n".join(new_keys)
    embed = create_embed(f"Generated {amount} Key(s) for {role.name}", f"```\n{key_list}\n```", discord.Color.green())
    
    for key in new_keys:
        log_action("Generated", key, interaction.user, role.name)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="redeem", description="Redeem a key to get a role")
@app_commands.describe(key="The key to redeem")
async def redeem_key(interaction: discord.Interaction, key: str):
    keys = load_keys()
    user = interaction.user
    
    for role_id, key_data in keys.items():
        if key in key_data["unused"]:
            key_data["unused"].remove(key)
            key_data["used"].append(key)
            save_keys(keys)
            
            role = interaction.guild.get_role(int(role_id))
            if not role:
                embed = create_embed("Error", "The role for this key no longer exists.", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            try:
                await user.add_roles(role)
                log_action("Redeemed", key, user, role.name)
                embed = create_embed("Key Redeemed!", f"You have been granted the {role.mention} role!", discord.Color.green())
                await interaction.response.send_message(embed=embed)
            except Exception as e:
                embed = create_embed("Error", f"Failed to assign role: {str(e)}", discord.Color.red())
                await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    embed = create_embed("Invalid Key", "The key you entered is invalid or has already been used.", discord.Color.red())
    await interaction.response.send_message(embed=embed, ephemeral=True)

bot.run(TOKEN)
