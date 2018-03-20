# pylint: disable=C0111,C0301
import datetime
import socket
import ssl
import threading
import time
import keyring
import imapclient
import imapclient.exceptions
import zmq
from encrypted_env_keyring import EncryptedEnvKeyring


class Checker:
    def __init__(self, server_address: str, username: str, short_name: str, zmq_port: int, timeout: int=10,
                 use_ssl=True):
        self.server, self.ssl_context, self.zmq_context, self.zmq_socket = None, None, None, None
        self.zmq_port = zmq_port
        self.short_name = short_name
        self.timeout = timeout
        self.server_address = server_address
        self.username = username
        if use_ssl:
            self.ssl_context = ssl.create_default_context()
        self.last_sync = datetime.datetime.now()
        self.keep_running = True

    def connect(self):
        self.zmq_context = zmq.Context()
        self.zmq_socket = self.zmq_context.socket(zmq.PUB)
        self.zmq_socket.connect(f"tcp://127.0.0.1:{self.zmq_port}")
        time.sleep(0.1)
        print("Established ZMQ connection")

        keyring.set_keyring(EncryptedEnvKeyring())
        self.server = imapclient.IMAPClient(self.server_address, ssl_context=self.ssl_context)
        self.server.login(self.username, keyring.get_password(f"MailChecker-{self.short_name}", self.username))
        self.server.select_folder('inbox')
        print(f"Connected to mailbox {self.short_name}")

    def timestamps_difference(self, timestamp):
        delta = timestamp - self.last_sync
        return delta.days * 24*60 + (delta.seconds + delta.microseconds / 10e6) / 60

    def check_for_unread_messages(self):
        new_messages = 0
        new_messages += len(self.server.search(['UNSEEN']))
        if new_messages > 0:
            self.zmq_socket.send_string(f"unread messages: {self.short_name}: {new_messages}")
            print(f"Sent notification regarding {self.short_name}")

    def idle_loop(self):
        self.server.idle()
        while self.keep_running:
            try:
                current_sync = datetime.datetime.now()
                responses = self.server.idle_check(timeout=30)
                if isinstance(responses, list) and list(filter(lambda x: b'EXISTS' in x, responses)):
                    print(f"{self.short_name}: got responses: {responses}")
                    self.server.idle_done()
                    self.check_for_unread_messages()
                    self.server.noop()
                    self.server.idle()
                if self.timestamps_difference(current_sync) > self.timeout:  # renew idle command every 10 minutes
                    self.server.idle_done()
                    self.server.noop()
                    self.server.idle()
                    self.last_sync = current_sync
            except (imapclient.exceptions.IMAPClientError, imapclient.exceptions.IMAPClientAbortError,
                    socket.error, socket.timeout, ssl.SSLError, ssl.SSLEOFError, zmq.ZMQError) as exception:
                print(f"Checker: Got exception @ {self.short_name}: {exception}")
                self.zmq_socket.close()
                self.connect()
                self.idle_loop()

    def halt(self):
        self.keep_running = False
        self.server.logout()


class CheckerThread(threading.Thread):
    def __init__(self, checker_instance: Checker):
        self.checker_instance = checker_instance
        threading.Thread.__init__(self)

    def run(self):
        self.checker_instance.connect()
        self.checker_instance.check_for_unread_messages()
        self.checker_instance.idle_loop()

    def halt(self):
        self.checker_instance.halt()
