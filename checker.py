import datetime
import imapclient
import imapclient.exceptions
import keyring
import queue
import socket
import ssl
import threading

ssl_context = ssl.create_default_context()


class Checker:
    def __init__(self, server_address: str, username: str, short_name: str, message_queue: queue.Queue,
                 timeout: int=10, use_ssl=True):
        self.server = None
        self.message_queue = message_queue
        self.short_name = short_name
        self.timeout = timeout
        self.server_address = server_address
        self.username = username
        self.use_ssl = use_ssl
        self.last_sync = datetime.datetime.now()
        self.keep_running = True

    def connect(self):
        self.server = imapclient.IMAPClient(self.server_address, ssl_context=ssl_context if self.use_ssl else None)
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
            self.message_queue.put(f"{self.short_name}: unread messages: {new_messages}")

    def idle_loop(self):
        self.server.idle()
        while self.keep_running:
            try:
                current_sync = datetime.datetime.now()
                responses = self.server.idle_check(timeout=30)
                if responses:
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
                    socket.error, socket.timeout, ssl.SSLError, ssl.SSLEOFError):
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
