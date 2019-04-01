import sys, logging, re

log = logging.getLogger(__name__)

class Error(Exception):
    pass

class ListenError(Error):
    def __init__(self, message: str):
        print(str(message) + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)

class ConnectError(Error):
    def __init__(self, message: str):
        print(str(message) + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)

class DBError(Error):
    def __init__(self, message: str):
        if re.search("database is locked", str(message), re.IGNORECASE):
            log.warn("Database is locked, the request has been stacked onto the request handler.")

        print(str(message) + " For support, check https://discord.gg/gDcqBJJ", file=sys.stderr)
