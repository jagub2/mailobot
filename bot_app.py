# pylint: disable=C0111,C0301
import configparser
import os
import time
from telegram_bot import TelegramBot, TelegramThread


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    bot = TelegramBot(config['global']['telegram_api'], config['global']['telegram_master'],
                      config['global']['zmq_port'])
    TelegramThread(bot).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
