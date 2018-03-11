from checker import Checker, CheckerThread
from queue import Queue
from telegram_bot import TelegramBot, TelegramThread
import configparser
import os
import time

"""
import logging

logging.basicConfig(
    format='%(asctime)s - %(levelname)s: %(message)s',
    level=logging.DEBUG
)
"""

if __name__ == "__main__":
    message_queue = Queue()
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    bot = TelegramBot(config['global']['telegram_api'], config['global']['telegram_master'], message_queue)
    TelegramThread(bot).start()

    mailboxes = [mailbox for mailbox in config.sections() if mailbox != 'global']
    for mailbox in mailboxes:
        checker = Checker(config[mailbox]['server'], config[mailbox]['username'], mailbox, message_queue,
                          int(config['global']['timeout']), bool(config[mailbox]['use_ssl']))
        CheckerThread(checker).start()

    while True:
        time.sleep(1)
