class Error(Exception):
    pass

class ListenError(Error):
    def __init__(self, message: str):
        pass

class ConnectError(Error):
    def __init__(self, message: str):
        pass

class OptionError(Error):
    def __init__(self, message: str):
        pass