import telegram

class Telegram:
	def __init__ (self, token):
		self.token = token
		self.bot = telegram.Bot(token = token)
		
	def show_messages (self):
		updates = self.bot.getUpdates()
		for u in updates:
			print(u.message)
	
	def updates (self):
		return self.bot.getUpdates()
		
	def send (self, msg, chat_id = None):
		self.bot.sendMessage (
			chat_id or self.updates ()[-1].message.chat.id, 
			msg
		)
