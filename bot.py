import os
import re
import discord
from discord.ext.commands.core import has_role
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
last_stat = None

@bot.command(name='stat')
@commands.has_role('admin')
async def stat(ctx, clearInfo=False):
  global last_stat, question_list
  if last_stat is not None:
    await ctx.send(last_stat)
    return
  text = '**Статистика тестирования (баллы):**\n'
  if len(question_list) == 0:
    text += '(пусто)\n'
  else:
    for member in members:
      print(f"Member: {member.name}")
      score = 0.0
      for question in question_list:
        print(f'Question:{question.text}')
        score += question.getUserScore(member)
      text += '{}: {:.2f}/{}\n'.format(member.name, score, len(question_list))
  last_stat = text
  print("Sendind statistics...")
  await ctx.send(text)
  print("Statictics was sent.")
  if clearInfo:
    members.clear()
    question_list.clear()

@bot.command(name='stop')
@commands.has_role('admin')
async def stop(ctx):
  print("Collecting statistics...")
  await stat(ctx, True)
  print("Statistics was collected.")

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
  question_list.clear()
  global last_stat
  last_stat = None
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
  adminChannel, adminUser = None, None
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
      adminUser = member
    print("Channel has been added to active members list.")
  print("Voice channel:", ', '.join([user.name for user in members.keys()]))
  return adminChannel, adminUser

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
  for answer, users in sorted(emoji_dict.items()):
    userlist = ', '.join([user for user in users]) if len(users) > 0 else '(пусто)'
    sign = ':white_check_mark:' if answer in question.right_answers else ':x:'
    stat_text += f'{sign} {answer} {userlist}\n'
  return stat_text

async def sendEmbedToUser(question_embed: str, embed, channel, member, question, answerN):
  react_msg = await channel.send(question_embed, embed=embed)
  question.addInfo(react_msg, member)
  A_unicode = '\U0001f1e6'
  #if member.id != ctx.message.author.id:
  for idx in range(answerN):
    await react_msg.add_reaction(emoji=chr(ord(A_unicode) + idx))

async def sendQuestionEmbed(ctx, text: str, answers: list, adminChannel, adminUser):
  text = text[re.match(r'\s*\?', text).span()[1]:]
  question = Question(text, answers)
  question_embed = ':bar_chart: **{}**\n'.format(text)
  idx = 0
  reply = ''
  for ans in answers:
    mark = ':regional_indicator_{}:'.format(chr(ord('a') + idx))
    ans_text = ans[re.match(r'\s*(?:\+|\=)', ans).span()[1]:]
    reply += mark + ' ' + ans_text + '\n'
    idx += 1
  embed = discord.Embed(description=reply, color=discord.Color.blue())
  await sendEmbedToUser(question_embed, embed, adminChannel, adminUser, question, len(answers))
  question.stat_msg = await adminChannel.send(getStatText(question))
  global members
  for member, channel in members.items():
    print(f"Sending question to user: {member.name}")
    if member == adminUser:
      print("Skip admin.")
      continue
    await sendEmbedToUser(question_embed, embed, channel, member, question, len(answers))
  print('Reactions was added.')
  question_list.append(question)

@bot.command(name='quiz')
@commands.has_role('admin')
async def quiz(ctx, *args):
  global last_stat
  last_stat = None
  adminChannel, adminUser = await generateChannels(ctx)
  if len(args) < 2:
    await ctx.send("Not enough arguments for command `quiz`.")
    return
  question, answers = args[0], args[1:]
  if not re.match(r"\s*\?", question):
    await ctx.send("Invalid question syntax: `?` expected.")
    return
  for answer in answers:
    if not re.match(r"\s*(?:\+|\=)", answer):
      await ctx.send("Invalid answer syntax: `+` or `=` expected.")
      return
  print("Sending question...")
  await sendQuestionEmbed(ctx, question, answers, adminChannel, adminUser)
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