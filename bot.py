import asyncio
import os
import re
import discord
import logging
from discord.ext.commands.core import has_role
from discord.permissions import make_permission_alias
from dotenv import load_dotenv
from discord.ext import commands
from question import Question

def terminate():
  exit(1)

logging.basicConfig(filename='history.log', level=logging.DEBUG,
  format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.INFO)
logging.getLogger().addHandler(stream_handler)
logging.debug("Loading environment...")
try:
  load_dotenv()
  TOKEN = os.getenv('DISCORD_TOKEN')
  GUILD = os.getenv('DISCORD_GUILD')
  CHANNEL_PREFIX = os.getenv('TESTING_PREFIX')
  ADMIN_CHANNEL_PREFIX = os.getenv('TESTING_ADMIN_PREFIX')
  CATEGORY_NAME = os.getenv('TESTING_CATEGORY')
except Exception as e:
  logging.critical(f'Failed to load environment: {e}')
  terminate()
logging.debug("Environment has been loaded successfully.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents) 
members = dict()
question_list = []
last_stat = None
timerStarted = False

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
    memberScore = dict()
    for member in members:
      print(f"Member: {member.display_name}")
      score = 0.0
      for question in question_list:
        print(f'Question:{question.text}')
        score += question.getUserScore(member)
      memberScore[member] = score
    for member, score in sorted(memberScore.items(), key=lambda item: item[1], reverse=True):  
      text += '{}: {:.2f}/{}\n'.format(member.display_name, score, len(question_list))
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
  for category in ctx.message.guild.categories:
    if category.name == CATEGORY_NAME:
      await category.delete()
  for channel in ctx.message.guild.text_channels:
    if re.match(CHANNEL_PREFIX, channel.name) or re.match(ADMIN_CHANNEL_PREFIX, channel.name):
      await channel.delete()
  members.clear()
  question_list.clear()
  global last_stat
  last_stat = None
  print("Channels has been cleared successfully.")

def convertName(name: str):
  return re.sub(r'[^\w\d]+', '', name).lower()

async def generateChannels(ctx):
  global members, timerStarted
  timerStarted = False
  voiceMemberList = getVoiceMemberList(ctx)
  if voiceMemberList is None:
    await ctx.send("Please join the voice channel to start testing.")
    return
  guild = ctx.message.guild
  # member -> channel
  adminChannel, adminUser = None, None
  for category in guild.categories:
    if category.name == CATEGORY_NAME:
      categoryChannel = category
      break
  else:
    categoryChannel = await guild.create_category_channel(CATEGORY_NAME)
  for member in voiceMemberList:
    print("Processing member:", member.display_name)
    if member.display_name != ctx.message.author.display_name:
      channel_name = CHANNEL_PREFIX + convertName(member.display_name)
    else:
      channel_name = ADMIN_CHANNEL_PREFIX + convertName(member.display_name)
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
      channel = await guild.create_text_channel(channel_name, overwrites=overwrites, category=categoryChannel)
      print("Channel has been created.")
    members[member] = channel
    if member.display_name == ctx.message.author.display_name:
      adminChannel = channel
      adminUser = member
    print("Channel has been added to active members list.")
  print("Voice channel:", ', '.join([user.display_name for user in members.keys()]))
  return adminChannel, adminUser

@bot.command(name='start')
@commands.has_role('admin')
async def start(ctx):
  await ctx.send('Бот готов к проведению тестирования.')
  await generateChannels(ctx)

def getStatText(question: Question) -> str:
  stat_text = '**Статистика вопроса:**\n'
  emoji_dict = {}
  A_unicode = '\U0001f1e6'
  for idx in range(question.answer_number):
    emoji_dict[chr(ord(A_unicode) + idx)] = []
  answered, notAnswered = str(), str()
  for ans_info in question.msg_dict.values():
    user, answers = ans_info['user'], ans_info['answers']
    if len(answers) > 0:
      answered += f'{user.display_name}\n'
    else:
      notAnswered += f'{user.display_name}\n'
    for ans in answers:
      emoji_dict[ans].append(user.display_name)
  for answer, users in sorted(emoji_dict.items()):
    userlist = ', '.join([user for user in users]) if len(users) > 0 else '(пусто)'
    sign = ':white_check_mark:' if answer in question.right_answers else ':x:'
    stat_text += f'{sign} {answer} {userlist}\n'
  stat_text += '\n**Ответили:**\n' + answered
  stat_text += '**Не ответили:**\n' + notAnswered
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
    print(f"Sending question to user: {member.display_name}")
    if member == adminUser:
      print("Skip admin.")
      continue
    await sendEmbedToUser(question_embed, embed, channel, member, question, len(answers))
  print('Reactions was added.')
  question_list.append(question)

@bot.command(name='quiz')
@commands.has_role('admin')
async def quiz(ctx, *args):
  global timerStarted
  timerStarted = False
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
  timerStarted = True
  while timerStarted:
    await asyncio.sleep(0.3)
    question = question_list[-1]
    await question.stat_msg.edit(content=getStatText(question))

@bot.event
async def on_message(message):
  if match := re.match(r'(/quiz\s+)', message.content):
    ctx = await bot.get_context(message)
    arg_list = []
    msg = message.content[match.span()[1]:]
    expr = re.compile(r'(\?\:|\+\:|\=\:)')
    match = re.search(expr, msg)
    if match is None:
      ctx.send('Syntax error.')
      return
    start = match.group(0).strip()
    msg = msg[match.span()[1]:]
    print(f'${msg}$')
    while match:
      #match = re.match(r'(?:\?\:|\+\:|\=\:)([^(?:\?\:|\+\:|\=\:)]+)', msg)
      match2 = re.search(expr, msg)
      #print(match2)
      if match2:
        result = msg[:match2.span()[0]]
      else:
        result = msg
      result = result.strip()
      if start == "?:":
        result = "?" + result
      elif start == "+:":
        result = "+" + result
      else:
        result = "=" + result
      #print(result)
      arg_list.append(result)
      if match2:
        start = match2.group(0).strip()
        msg = msg[match2.span()[1]:]
      match = match2
    print(*arg_list)
    await ctx.invoke(bot.get_command('quiz'), *arg_list)
  else:
    await bot.process_commands(message)

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
  bot_name = bot.user.name
  logging.info(f'{bot_name} has connected to Discord!')
  guild = discord.utils.get(bot.guilds, name=GUILD)
  if guild is None:
    logging.critical(f"Failed to connect to guild `{GUILD}`.")
    terminate()
  logging.info(
    f'{bot.user} has connected to the following guild:\n'
    f'{guild.name}(id: {guild.id})'
  )
  guild_members = guild.members
  members = '\n - '.join([member.display_name for member in guild_members])
  logging.info(f'Guild Members:\n - {members}')
  if len(guild_members) == 0 or (len(guild_members) == 1 and guild_members[0].name == bot_name):
    logging.warning(f'Server does not contain members or the list cannot be loaded.')
  else:
    logging.info(f'Member list was loaded successfully.')

@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.errors.CheckFailure):
    msg = 'You do not have the correct role for this command.'
    logging.info(msg)
    await ctx.send(msg)

# main
logging.debug("Connecting to bot...")
bot.run(TOKEN)