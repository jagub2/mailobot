# pylint: disable=C0111,C0301
import configparser
import getpass
import os
import keyring
from encrypted_env_keyring import EncryptedEnvKeyring


def main():
    keyring.set_keyring(EncryptedEnvKeyring())
    config = configparser.ConfigParser()
    config.read(os.path.join(os.path.dirname(__file__), 'config.ini'))
    mailboxes = [mailbox for mailbox in config.sections() if mailbox != 'global']
    for mailbox in mailboxes:
        username = config[mailbox]['username']
        mail_password = getpass.getpass(f"Please enter password for {username} @ {mailbox} mailbox: ")
        keyring.set_password(f"MailChecker-{mailbox}", username, mail_password)


if __name__ == "__main__":
    main()
