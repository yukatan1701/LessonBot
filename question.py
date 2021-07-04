import re

class Question:
  def __init__(self, text: str, answers: list, stat_msg=None):
    self.text = text
    self.stat_msg = stat_msg
    self.answer_number = len(answers)
    self.right_answers = set()
    A_unicode = '\U0001f1e6'
    for i in range(len(answers)):
      if re.match("\s*\+", answers[i]):
        self.right_answers.add(chr(ord(A_unicode) + i))
    # message -> { user, answers[] }
    self.msg_dict = dict()

  def addInfo(self, msg, user):
    self.msg_dict[msg] = { 'user': user, 'answers': set() }

  def addAnswer(self, msg, answer):
    self.msg_dict[msg]['answers'].add(answer)

  def removeAnswer(self, msg, answer):
    self.msg_dict[msg]['answers'].discard(answer)

  def getUserScore(self, user) -> float:
    for msg in self.msg_dict.values():
      if msg['user'] == user:
        answers = msg['answers']
        intersection = answers.intersection(self.right_answers)
        rightN = len(self.right_answers)
        return len(intersection) / rightN if rightN > 0 else 0
    return 0