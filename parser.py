import re

class Question:
  def __init__(self):
    self.text = None
    self.answers = []
    self.image_paths = []

  def isEmpty(self):
    return self.text is None and \
           len(self.answers) == 0 and \
           len(self.image_paths) == 0
  
  def __str__(self):
    s = f'<Question:\n\'{self.text}\';\nAnswers:\n'
    i = 1
    for ans in self.answers:
      s += f'{i}. {ans}\n'
      i += 1
    s += ">"
    return s

def getQuestionList(text: str):
  qlist = []
  question = Question()
  while len(text) > 0:
    sentence = re.match(r'(?:\"(?P<phrase>[^\"]*)\"|(?P<dollar>\$))\s*', text)
    if len(sentence.groupdict()) < 1:
      break
    gd = sentence.groupdict()
    if gd['phrase'] is not None:
      phrase = gd['phrase']
      if question.text is None:
        question.text = phrase
      else:
        question.answers.append(phrase)
    else: # '$' found
      qlist.append(question)
      question = Question()
    text = text[sentence.span()[1]:]
  if not question.isEmpty():
    qlist.append(question)
  return qlist

def parseQuestions(filename: str):
  file = open(filename, 'r')
  text = ''
  for line in file.readlines():
    if re.fullmatch("\s+", line) is not None:
      continue
    text += line
  print(text)
  file.close()
  return getQuestionList(text)

qlist = parseQuestions('questions.txt')
print(*qlist)