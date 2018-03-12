# pylint: disable=C0111
import os
from keyrings.alt.file import EncryptedKeyring


class EncryptedEnvKeyring(EncryptedKeyring):
    def _get_new_password(self):
        return os.environ['ENCRYPTION_PASSWORD']

    def _unlock(self):
        self.keyring_key = os.environ['ENCRYPTION_PASSWORD']
        try:
            ref_pw = self.get_password('keyring-setting', 'password reference')
            assert ref_pw == 'password reference value'
        except AssertionError:
            self._lock()
            raise ValueError("Incorrect Password")
