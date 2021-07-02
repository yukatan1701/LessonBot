import os
import re
import discord
from discord.ext.commands.core import has_role
from dotenv import load_dotenv
from discord.ext import commands
from datetime import date, datetime

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
VOICE_ID = os.getenv('VOICE_CHANNEL_ID')
print("Voice channel ID:", VOICE_ID)
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL_PREFIX = os.getenv('TESTING_PREFIX')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents) 
members = dict()

def getVoiceMemberList(ctx):
  voice_channel = ctx.author.voice.channel
  if voice_channel is None:
    print("Failed to get member list.")
    return None
  return voice_channel.members

@bot.command(name='list')
@commands.has_role('admin')
async def channel_list(ctx):
  guild = ctx.message.guild
  for channel in guild.text_channels:
    print(channel, channel.id)

@bot.command(name='clear')
@commands.has_role('admin')
async def clear(ctx):
  guild = ctx.message.guild
  for channel in guild.text_channels:
    if re.match(CHANNEL_PREFIX, channel.name):
      await channel.delete()
  print("Channels has been cleared successfully.")

@bot.command(name='start')
@commands.has_role('admin')
async def start(ctx):
  await clear(ctx)
  global members
  memberList = getVoiceMemberList(ctx)
  if memberList is None:
    await ctx.send("Please join the voice channel to start testing.")
    return
  guild = ctx.message.guild
  # member -> channel
  for member in memberList:
    name = member.name.replace('#', '')
    channel = await guild.create_text_channel(CHANNEL_PREFIX + name)
    members[member] = channel
    await channel.set_permissions(ctx.guild.default_role, read_messages=False, send_messages=False)
    await channel.set_permissions(ctx.message.author, read_messages=True, send_messages=True)
    await channel.set_permissions(member, read_messages=True, send_messages=True)
    await channel.send('Начало тестирования:', datetime.now())
  print("Voice channel:", ', '.join([user.name for user in members.keys()]))

@bot.command(name='poll')
@commands.has_role('admin')
async def poll(ctx, *args):
  await ctx.send('Let`s start testing!')
  if len(args) < 2:
    await ctx.send("Not enough arguments for command `poll`.")
    return
  question = args[0]
  answers = args[1:]
  # TODO: what if voice channel is turned off?
  voice_channel = ctx.author.voice.channel
  print("Current users:", ', '.join([user.name for user in voice_channel.members]))

@bot.event
async def on_ready():
  print(f'{bot.user.name} has connected to Discord!')
  guild = discord.utils.get(bot.guilds, name=GUILD)
  print(
    f'{bot.user} has connected to the following guild:\n'
    f'{guild.name}(id: {guild.id})'
  )
  members = '\n - '.join([member.name for member in guild.members])
  print(f'Guild Members:\n - {members}')

@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.errors.CheckFailure):
    await ctx.send('You do not have the correct role for this command.')

# main
bot.run(TOKEN)