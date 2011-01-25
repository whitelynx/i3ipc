class MagicKeyError(Exception):
    def __init__(self):
        Exception.__init__(self, "Magic key not found in response. Response tainted!")

class NotFoundError(Exception):
    def __init__(self, msg):
        Exception.__init__(self, msg)
