import sys, logging, re

log = logging.getLogger(__name__)

class Error(Exception):
    pass

class ListenError(Error):
    def __init__(self, message: str):
        print(message + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)

class ConnectError(Error):
    def __init__(self, message: str):
        print(message + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)

class DBError(Error):
    def __init__(self, message: str):
        if re.search("database is locked", message, re.IGNORECASE):
            log.warn("Database is locked, the request has been stacked onto the request handler.")

        print(message + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)