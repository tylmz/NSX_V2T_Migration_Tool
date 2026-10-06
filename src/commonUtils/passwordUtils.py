# ***************************************************
# Copyright © 2020 VMware, Inc. All rights reserved.
# ***************************************************

"""
Description: Module which holds all the methods for encrypting and decrypting passwords
"""

import base64
import os
import secrets
import string
import sys
import cryptography

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet


# ---------------------------------------------------------------------------
# PATCH-7: protect the master key with Windows DPAPI
#
# The original design stores the master key in clear text on the first line of the
# password file, so anyone who can read the file can decrypt the passwords.
# On Windows the master key is now wrapped with DPAPI (CryptProtectData), which ties it
# to the Windows user account that created the file. The file format and line count are
# unchanged, and files written by older builds (plain master key) can still be read.
# ---------------------------------------------------------------------------
DPAPI_PREFIX = 'DPAPI:'
# Application specific entropy: other programs running as the same user cannot unwrap
# the key with a plain CryptUnprotectData call.
_DPAPI_ENTROPY = b'vcdNSXMigrator-passfile-v1'
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


def _dpapiAvailable():
    return sys.platform == 'win32'


def _dpapiCall(data, protect):
    """Calls CryptProtectData / CryptUnprotectData through ctypes (no extra dependency)."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [('cbData', wintypes.DWORD), ('pbData', ctypes.POINTER(ctypes.c_char))]

    def toBlob(raw):
        buffer = ctypes.create_string_buffer(raw, len(raw))
        return DATA_BLOB(len(raw), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char))), buffer

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    dataIn, _dataBuffer = toBlob(data)
    entropy, _entropyBuffer = toBlob(_DPAPI_ENTROPY)
    dataOut = DATA_BLOB()
    if protect:
        ok = crypt32.CryptProtectData(ctypes.byref(dataIn), 'vcdNSXMigrator', ctypes.byref(entropy),
                                      None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dataOut))
    else:
        ok = crypt32.CryptUnprotectData(ctypes.byref(dataIn), None, ctypes.byref(entropy),
                                        None, None, _CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(dataOut))
    if not ok:
        raise ctypes.WinError()
    try:
        return ctypes.string_at(dataOut.pbData, dataOut.cbData)
    finally:
        kernel32.LocalFree(dataOut.pbData)


def protectMasterKey(masterKey):
    """Returns the master key as stored on the first line of the password file."""
    if not _dpapiAvailable():
        return masterKey
    protected = _dpapiCall(masterKey.encode('utf-8'), protect=True)
    return DPAPI_PREFIX + base64.b64encode(protected).decode('ascii')


def unprotectMasterKey(storedValue):
    """Returns the clear master key from the first line of the password file."""
    if not storedValue.startswith(DPAPI_PREFIX):
        # Legacy file written by an unpatched build or on a non-Windows system
        return storedValue
    if not _dpapiAvailable():
        raise Exception("Password file is protected with Windows DPAPI and can only be read on the Windows "
                        "machine and user account that created it")
    try:
        return _dpapiCall(base64.b64decode(storedValue[len(DPAPI_PREFIX):]), protect=False).decode('utf-8')
    except OSError:
        raise Exception("Password file was created by a different Windows user or machine and cannot be "
                        "decrypted. Delete it and run the tool once without --passwordFile to create a new one")


class PasswordUtilities():
    def generateMasterKey(self, length=30):
        """
            Description :   Generates a random master key of random length for creation of encryption key
            Parameters  :   length    -   Length of the master key to be generated (INTEGER)
            Returns     :   Master key
        """
        randomGenerator = secrets.SystemRandom()
        masterKey = ''.join(randomGenerator.choices(string.digits + string.ascii_letters + string.punctuation, k=length))
        return masterKey

    def readPassFile(self, fileName, v2tpassfile=False):
        """
            Description :   Read the encrypted passwords and master key from file
            Parameters: fileName to be read
            Returns     :   List of the encrypted passwords
        """
        with open(fileName, 'r') as f:
            passList = f.read().split('\n')
            # passfile holds 4 values encrypted - 1. master key, 2. vcd password, 3. nsx-t password, 4. vcenter password, 5. nsx-v password

            if v2tpassfile and len(passList) != 2:
                raise Exception("Invalid password file")

            if not v2tpassfile and len(passList) != 5:
                raise Exception("Invalid password file")
            # PATCH-7: unwrap a DPAPI protected master key (legacy plain keys are returned as they are)
            passList[0] = unprotectMasterKey(passList[0])
            return passList

    def writePassFile(self, data, fileName):
        """
            Description :   Write the encrypted passwords and master key to file
            Parameters  :   data    -   passwords and master key to be stored in file (STRING)
                            fileName - File path to write data
        """
        # PATCH-7: the first line is the master key; store it DPAPI protected on Windows
        masterKey, separator, rest = data.partition('\n')
        data = protectMasterKey(masterKey) + separator + rest
        # Write file.
        with open(fileName, 'w') as f:
            f.write(data)
        # PATCH-7: on non-Windows systems at least restrict the file to the current user
        if not _dpapiAvailable():
            try:
                os.chmod(fileName, 0o600)
            except OSError:
                pass

    def generateKey(self, masterKey):
        """
            Description :   Generates a encryption key for password encryption
            Parameters  :   masterKey    -   Master key to be used for the generation of encryption key (STRING)
            Returns     :   Encryption key
        """
        # Splitting the master key into password and encryption salt
        password = masterKey[:len(masterKey)//2].encode()
        salt = masterKey[len(masterKey)//2:].encode()
        # Creating a key derive function that would be further used for encryption key generation
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=234567,
            backend=default_backend()
        )
        # Generating the encryption key
        key = base64.urlsafe_b64encode(kdf.derive(password))  # Can only use kdf once
        return key

    def encrpyt(self, key, password):
        """
            Description :   Encrypts the provided password with the key provided
            Parameters  :   key       -   Encryption key to be used for encryption (BYTE-STRING)
                            password  -   Password to be encrypted (STRING)
            Returns     :   Encrypted password
        """
        try:
            f = Fernet(key)
            encrypted = f.encrypt(password.encode())
            return encrypted
        except:
            raise

    def decrypt(self, key, encryptedPassword):
        """
            Description :   Decrypts the provided password with the key provided
            Parameters  :   key                -   Encryption key to be used for decryption (BYTE-STRING)
                            encryptedPassword  -   Password to be Decrypted (STRING)
            Returns     :   Decrypted password
        """
        try:
            f = Fernet(key)
            decrypted = f.decrypt(encryptedPassword, ttl=None).decode()
            return decrypted
        except cryptography.fernet.InvalidToken:
            return str()
        except:
            raise
