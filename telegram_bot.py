from telegram.error import TelegramError, TimedOut, NetworkError
from telegram.ext import CommandHandler, Updater, messagequeue
import queue
import telegram.bot
import time
import threading


# https://github.com/python-telegram-bot/python-telegram-bot/wiki/Avoiding-flood-limits
class MQBot(telegram.bot.Bot):
    '''A subclass of Bot which delegates send method handling to MQ'''
    def __init__(self, *args, is_queued_def=True, mqueue=None, **kwargs):
        super(MQBot, self).__init__(*args, **kwargs)
        # below 2 attributes should be provided for decorator usage
        self._is_messages_queued_default = is_queued_def
        self._msg_queue = mqueue or messagequeue.MessageQueue()

    def __del__(self):
        try:
            self._msg_queue.stop()
        except:
            pass
        super(MQBot, self).__del__()

    @messagequeue.queuedmessage
    def send_message(self, *args, **kwargs):
        '''Wrapped method would accept new `queued` and `isgroup`
        OPTIONAL arguments'''
        return super(MQBot, self).send_message(*args, **kwargs)


class TelegramBot:
    MASTER = None

    def __init__(self, api_key: str, master: int, incoming_message_queue: queue.Queue=None):
        self.api_key = api_key
        self.incoming_message_queue = incoming_message_queue
        self.master, TelegramBot.MASTER = master, master
        self.updater, self.dispatcher, self.message_queue, self.bot = None, None, None, None
        self.keep_running = True

    def connect(self):
        self.message_queue = messagequeue.MessageQueue(all_burst_limit=3, all_time_limit_ms=3000)
        self.bot = MQBot(token=self.api_key, mqueue=self.message_queue)
        self.updater = Updater(bot=self.bot)
        self.dispatcher = self.updater.dispatcher
        self.dispatcher.add_handler(CommandHandler('ping', TelegramBot.ping))
        self.updater.start_polling()
        self.dispatcher.bot.send_message(chat_id=self.master, text="MailoBot started!")

    def queue_loop(self):
        while self.keep_running:
            time.sleep(0.1)
            try:
                while not self.incoming_message_queue.empty():
                    data = self.incoming_message_queue.get()
                    self.dispatcher.bot.send_message(chat_id=self.master, text=data)
            except (TimedOut, NetworkError, TelegramError):
                self.connect()
                self.queue_loop()

    def halt(self):
        self.keep_running = False
        self.updater.stop()

    @staticmethod
    def ping(bot, update):
        if update.message.chat_id == TelegramBot.MASTER:
            bot.send_message(chat_id=update.message.chat_id, text="pong")


class TelegramThread(threading.Thread):
    def __init__(self, bot_instance: TelegramBot):
        self.bot_instance = bot_instance
        threading.Thread.__init__(self)

    def run(self):
        self.bot_instance.connect()
        self.bot_instance.queue_loop()

    def halt(self):
        self.bot_instance.halt()
