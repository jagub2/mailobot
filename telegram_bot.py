# pylint: disable=C0111,C0301
import time
import threading
import telegram.bot
import zmq
from telegram.error import TelegramError, TimedOut, NetworkError
from telegram.ext import CommandHandler, Updater, messagequeue


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

    def __init__(self, api_key: str, master: int, zmq_port: int):
        self.updater, self.dispatcher, self.message_queue, self.bot, self.zmq_context, self.zmq_socket = \
            None, None, None, None, None, None
        self.api_key = api_key
        self.master, TelegramBot.MASTER = master, master
        self.zmq_port = zmq_port
        self.keep_running = True

    def connect(self):
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.SUB)
        self.zmq_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.zmq_socket.bind(f"tcp://127.0.0.1:{self.zmq_port}")

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
                data = self.zmq_socket.recv()
                self.dispatcher.bot.send_message(chat_id=self.master, text=data)
            except (TimedOut, NetworkError, TelegramError, zmq.ZMQError):
                self.zmq_socket.close()
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
