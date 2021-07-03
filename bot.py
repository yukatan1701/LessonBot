import os
import re
from typing import Iterable
import discord
from discord.ext.commands.core import has_role
from discord.mentions import AllowedMentions
from dotenv import load_dotenv
from discord.ext import commands
from question import Question

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
CHANNEL_PREFIX = os.getenv('TESTING_PREFIX')

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents) 
members = dict()
question_list = []

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
  for channel in ctx.message.guild.text_channels:
    if re.match(CHANNEL_PREFIX, channel.name):
      await channel.delete()
  members.clear()
  print("Channels has been cleared successfully.")

def convertName(name: str):
  return re.sub(r'[^\w\d]+', '', name).lower()

@bot.command(name='start')
@commands.has_role('admin')
async def generateChannels(ctx):
  global members
  voiceMemberList = getVoiceMemberList(ctx)
  if voiceMemberList is None:
    await ctx.send("Please join the voice channel to start testing.")
    return
  guild = ctx.message.guild
  # member -> channel
  adminChannel = None
  for member in voiceMemberList:
    print("Processing member:", member.name)
    channel_name = CHANNEL_PREFIX + convertName(member.name)
    print("Generated name:", channel_name)
    channel = None
    for ch in guild.text_channels:
      if ch.name == channel_name:
        channel = ch
        break
    #if this channel has already been created
    if channel is None:
      overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
        ctx.message.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        member: discord.PermissionOverwrite(read_messages=True, send_messages=True)
      }
      channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
      print("Channel has been created.")
    members[member] = channel
    if member.name == ctx.message.author.name:
      adminChannel = channel
    print("Channel has been added to active members list.")
  print("Voice channel:", ', '.join([user.name for user in members.keys()]))
  return adminChannel

def getStatText(question: Question) -> str:
  stat_text = '**Статистика вопроса:**\n'
  emoji_dict = {}
  A_unicode = '\U0001f1e6'
  for idx in range(question.answer_number):
    emoji_dict[chr(ord(A_unicode) + idx)] = []
  for ans_info in question.msg_dict.values():
    user, answers = ans_info['user'], ans_info['answers']
    for ans in answers:
      emoji_dict[ans].append(user.name)
  for answer, users in emoji_dict.items():
    userlist = ', '.join([user for user in users]) if len(users) > 0 else '(пусто)'
    stat_text += f'{answer} {userlist}\n'
  return stat_text

async def sendQuestionEmbed(ctx, text: str, answers: Iterable):
  question = Question(text, len(answers))
  question_embed = ':bar_chart: **{}**\n'.format(text)
  idx = 0
  reply = ''
  for ans in answers:
    mark = ':regional_indicator_{}:'.format(chr(ord('a') + idx))
    reply += mark + ' ' + ans + '\n'
    idx += 1
  embed = discord.Embed(description=reply, color=discord.Color.blue())
  global members
  adminChannel = None
  for member, channel in members.items():
    if member.id == ctx.message.author.id:
      adminChannel = channel
    react_msg = await channel.send(question_embed, embed=embed)
    question.addInfo(react_msg, member)
    A_unicode = '\U0001f1e6'
    #if member.id != ctx.message.author.id:
    for idx in range(len(answers)):
      await react_msg.add_reaction(emoji=chr(ord(A_unicode) + idx))
  print('Reactions was added.')
  question.stat_msg = await adminChannel.send(getStatText(question))
  question_list.append(question)

@bot.command(name='poll')
@commands.has_role('admin')
async def poll(ctx, *args):
  adminChannel = await generateChannels(ctx)
  if len(args) < 2:
    await ctx.send("Not enough arguments for command `poll`.")
    return
  question, answers = args[0], args[1:]
  print("Sending question...")
  await sendQuestionEmbed(ctx, question, answers)
  print('Question was sent.')

@bot.event
async def on_reaction_add(reaction, user):
  msg = reaction.message
  if user == msg.author:
    return
  question = question_list[-1]
  question.addAnswer(msg, reaction.emoji)
  await question.stat_msg.edit(content=getStatText(question))

@bot.event
async def on_reaction_remove(reaction, user):
  msg = reaction.message
  if user == msg.author:
    return
  question = question_list[-1]
  question.removeAnswer(msg, reaction.emoji)
  await question.stat_msg.edit(content=getStatText(question))

@bot.command(name='stop')
@commands.has_role('admin')
async def stop(ctx):
  pass

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