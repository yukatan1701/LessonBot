import asyncio
import os
import re
import discord
import logging
from datetime import datetime
from discord import file
from discord.ext.commands.core import has_role
from discord.permissions import make_permission_alias
from dotenv import load_dotenv
from discord.ext import commands
from question import Question

def terminate():
  exit(1)

logging.basicConfig(filename='history.log', filemode='w', level=logging.DEBUG,
  format='[%(asctime)s][%(levelname)s] %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
stdout_handler = logging.StreamHandler()
stdout_handler.setLevel(logging.INFO)

logging.getLogger().addHandler(stdout_handler)
logging.debug("Loading environment...")
try:
  load_dotenv()
  TOKEN = os.getenv('DISCORD_TOKEN')
  GUILD = os.getenv('DISCORD_GUILD')
  CHANNEL_PREFIX = os.getenv('TESTING_PREFIX')
  ADMIN_CHANNEL_PREFIX = os.getenv('TESTING_ADMIN_PREFIX')
  CATEGORY_NAME = os.getenv('TESTING_CATEGORY')
  STAT_PATH = os.getenv('STAT_FILE_PATH')
  STAT_FILENAME = 'statistics.txt'
  if os.path.isfile(STAT_PATH):
    logging.debug("STAT_FILE_PATH is a file.")
  elif os.path.isdir(STAT_PATH):
    logging.debug("STAT_FILE_PATH is a directory.")
    STAT_PATH = os.path.join(STAT_PATH, STAT_FILENAME)
  else:
    STAT_PATH = STAT_FILENAME
    logging.error("Invalid syntax of statistics file path. Use defaults.")
  logging.info(f"STAT_FILE_PATH: {STAT_PATH}")
except Exception as e:
  logging.critical(f'Failed to load environment: {e}')
  terminate()
logging.debug("Environment has been loaded successfully.")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='/', intents=intents) 
members = dict()
question_list = []
last_stat = None

@bot.command(name='stat')
@commands.has_role('admin')
async def stat(ctx, filename=None):
  def writeStat(text, filename):
    if filename is None:
      return
    try:
      with open(filename, 'a') as file:
        file.write(f'[{datetime.now()}]\n{text}\n')
      logging.info(f"Statistics was saved to file `{filename}`.")
    except Exception as e:
      logging.error(f"Failed to write to statistics file: {str(e)}.")
      if filename != STAT_FILENAME:
        logging.error(f'Trying to write to default file {STAT_FILENAME}.')
        writeStat(text, STAT_FILENAME)
  global last_stat, question_list
  if last_stat is not None:
    writeStat(last_stat, filename)
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
    for member, score in sorted(memberScore.items(), key=lambda item: item[1],\
      reverse=True):  
      text += '{}: {:.2f}/{}\n'.format(member.display_name, score,\
        len(question_list))
  last_stat = text
  writeStat(text, filename)
  print("Sendind statistics...")
  await ctx.send(text)
  print("Statictics was sent.")

@bot.command(name='stop')
@commands.has_role('admin')
async def stop(ctx):
  print("Collecting statistics...")
  await stat(ctx, STAT_PATH)
  members.clear()
  question_list.clear()
  print("Statistics was collected.")

def getVoiceMembers(ctx):
  """Get a voice channel of the ctx author and return members of this channel.
  """
  if ctx.author.voice is None:
    logging.debug(f"Failed to get voice of user {ctx.author.name}.")
    return None
  voice_channel = ctx.author.voice.channel
  if voice_channel is None:
    logging.debug(f"Failed to get voice channel of user {ctx.author.name}.")
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
  """Generate private text channel for every member of a voice channel and
  extend `members` dictionary with new members of a voice channel.
  Return `(admin_user, admin_channel)`.
  """
  global members
  voice_members = getVoiceMembers(ctx)
  if voice_members is None or len(voice_members) == 0:
    logging.info('Failed to start testing due to empty voice channel.')
    await ctx.send("Подключитесь к голосовому каналу, чтобы начать тестирование.")
    return None
  guild = ctx.message.guild
  # Find category channel with name CATEGORY_NAME. Return this channel if found,
  # create new channel otherwise.
  for category in guild.categories:
    if category.name == CATEGORY_NAME:
      category_channel = category
      logging.debug(f"Category channel {CATEGORY_NAME} has already been created.")
      break
  else:
    category_channel = await guild.create_category_channel(CATEGORY_NAME)
    logging.debug(f"Create new category channel {CATEGORY_NAME}.")
  # member -> channel
  admin_channel, admin_user = None, None
  logging.debug("Voice channel members:" +\
    ', '.join([user.display_name for user in members.keys()]))
  logging.debug("Processing members in a voice channel...")
  for member in voice_members:
    logging.debug(f"Processing member: {member.display_name} ({member.name})")
    if member.display_name != ctx.message.author.display_name:
      channel_name = CHANNEL_PREFIX + convertName(member.display_name)
    else:
      channel_name = ADMIN_CHANNEL_PREFIX + convertName(member.display_name)
    logging.debug(f"Generated name: {channel_name}")
    # Check if this text channel has already been created
    channel = None
    for ch in guild.text_channels:
      if ch.name == channel_name:
        channel = ch
        logging.debug("Use existing text channel.")
        break
    if channel is None:
      logging.debug("Create new text channel.")
      overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(
          read_messages=False, send_messages=False),
        ctx.message.author: discord.PermissionOverwrite(
          read_messages=True, send_messages=True),
        member: discord.PermissionOverwrite(
          read_messages=True, send_messages=True)
      }
      channel = await guild.create_text_channel(channel_name,\
        overwrites=overwrites, category=category_channel)
      logging.debug("Channel has been created.")
    members[member] = channel
    if member.id == ctx.message.author.id:
      admin_channel = channel
      admin_user = member
    logging.debug("Pair (Member, Channel) was saved.")
  if admin_channel is None or admin_user is None:
    logging.error("Failed to get admin user and admin channel.")
    return None
  return (admin_user, admin_channel)

@bot.command(name='start')
@commands.has_role('admin')
async def start(ctx):
  await ctx.send('Генерирую каналы...')
  logging.info('Generating channels...')
  result = await generateChannels(ctx)
  if result:
    logging.info('Bot is ready for testing.')
    await ctx.send('Бот готов к проведению тестирования.')
  

def getStatText(question: Question) -> str:
  logging.debug("Generating statistics message...")
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
  logging.debug("Statistics message was generated.")
  return stat_text

async def sendEmbedToUser(question_embed: str, embed, member, channel,\
  question, answerN):
  react_msg = await channel.send(question_embed, embed=embed)
  question.addInfo(react_msg, member)
  A_unicode = '\U0001f1e6'
  #if member.id != ctx.message.author.id:
  for idx in range(answerN):
    await react_msg.add_reaction(emoji=chr(ord(A_unicode) + idx))
  logging.debug(f"Reactions was added for member {member.display_name}")

async def sendQuestionEmbed(ctx, text: str, answers: list, admin_user,\
  admin_channel):
  question = Question(text[1:], answers)
  question_ftext = ':bar_chart: **{}**\n'.format(question.text)
  reply = ''
  for idx, ans in enumerate(answers):
    mark = ':regional_indicator_{}:'.format(chr(ord('a') + idx))
    reply += f'{mark} {ans[1:]}\n'
  embed = discord.Embed(description=reply, color=discord.Color.blue())
  # send embed to admin first
  await sendEmbedToUser(question_ftext, embed, admin_user, admin_channel,\
    question, len(answers))
  question.stat_msg = await admin_channel.send(getStatText(question))
  global members
  logging.info("Sending questions...")
  for member, channel in members.items():
    logging.info(f"Sending question to member: {member.display_name}")
    if member == admin_user:
      continue
    await sendEmbedToUser(question_ftext, embed, member, channel, question,\
      len(answers))
  logging.info("Questions were sent.")
  question_list.append(question)

async def updateStatMessage():
  while True:
    if question_list:
      question = question_list[-1]
      await question.stat_msg.edit(content=getStatText(question))
    await asyncio.sleep(0.2)

@bot.command(name='quiz')
@commands.has_role('admin')
async def quiz(ctx, *args):
  global last_stat
  last_stat = None
  result = await generateChannels(ctx)
  if result is None:
    logging.error("Failed to generate channels.")
    return
  admin_user, admin_channel = result[0:2]
  if len(args) < 2:
    await ctx.send("Недостаточно аргументов для команды `quiz`.")
    return
  question, answers = args[0], args[1:]
  logging.info("Sending question...")
  await sendQuestionEmbed(ctx, question, answers, admin_user, admin_channel)
  logging.info("Question was sent.")
@bot.event
async def on_message(message):
  if match := re.match(r'(/quiz\s+)', message.content):
    ctx = await bot.get_context(message)
    if not ctx.valid:
      logging.error("Failed to get message context of the /quiz command.")
      return
    arg_list = []
    msg = message.content[match.span()[1]:]
    expr = re.compile(r'(\?\:|\+\:|\=\:)')
    match = re.search(expr, msg)
    if match is None:
      pref_list = '?:, +:, =:'
      logging.error(f'Cannot find any prefix ({pref_list}) to parse command \
        arguments.')
      await ctx.send(f'Не найдено ни одного префикса ({pref_list}) для разделения \
        аргументов команды.')
      return
    start = match.group(0).strip()
    msg = msg[match.span()[1]:]
    while match:
      match2 = re.search(expr, msg)
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
      arg_list.append(result)
      if match2:
        start = match2.group(0).strip()
        msg = msg[match2.span()[1]:]
      match = match2
    logging.info('Quiz arguments:\n' + '\n'.join(arg for arg in arg_list))
    try:
      await ctx.invoke(bot.get_command('quiz'), *arg_list)
    except TypeError as te:
      logging.error("Failed to invoke quiz:" + str(te))
  else:
    await bot.process_commands(message)

@bot.event
async def on_reaction_add(reaction, user):
  msg = reaction.message
  if user == msg.author:
    return
  question = question_list[-1]
  question.addAnswer(msg, user, reaction.emoji)
  await question.stat_msg.edit(content=getStatText(question))

@bot.event
async def on_reaction_remove(reaction, user):
  msg = reaction.message
  if user == msg.author:
    return
  question = question_list[-1]
  question.removeAnswer(msg, user, reaction.emoji)
  await question.stat_msg.edit(content=getStatText(question))

@bot.event
async def on_ready():
  bot_name = bot.user.name
  logging.info(f'{bot_name} has connected to Discord!')
  bot.loop.create_task(updateStatMessage())
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
  if len(guild_members) == 0 or (len(guild_members) == 1 and\
    guild_members[0].name == bot_name):
    logging.warning(f'Server does not contain members or the list cannot be loaded.')
  else:
    logging.info(f'Member list was loaded successfully.')

@bot.event
async def on_command_error(ctx, error):
  if isinstance(error, commands.errors.CheckFailure):
    msg = 'You do not have the correct role for this command.'
    logging.info(msg)
    await ctx.send(msg)
  else:
    logging.error(error)

# main
logging.debug("Connecting to bot...")
bot.run(TOKEN)