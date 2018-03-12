# pylint: disable=C0111,C0301
import configparser
import os
import time
from checker import Checker, CheckerThread


def main():
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    mailboxes = [mailbox for mailbox in config.sections() if mailbox != 'global']
    for mailbox in mailboxes:
        checker = Checker(config[mailbox]['server'], config[mailbox]['username'], mailbox, config['global']['zmq_port'],
                          int(config['global']['timeout']), bool(config[mailbox]['use_ssl']))
        CheckerThread(checker).start()

    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
