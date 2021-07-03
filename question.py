class Question:
  def __init__(self, text: str, answer_number: int, stat_msg=None):
    self.text = text
    self.stat_msg = stat_msg
    self.answer_number = answer_number
    # message -> { user, answers[] }
    self.msg_dict = dict()

  def addInfo(self, msg, user):
    self.msg_dict[msg] = { 'user': user, 'answers': set() }

  def addAnswer(self, msg, answer):
    self.msg_dict[msg]['answers'].add(answer)

  def removeAnswer(self, msg, answer):
    self.msg_dict[msg]['answers'].discard(answer)