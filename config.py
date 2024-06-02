from datetime import datetime

class SingletonTimestamp:
    _instance = None
    timestamp = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SingletonTimestamp, cls).__new__(cls)
            cls.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return cls._instance

def get_timestamp():
    return SingletonTimestamp().timestamp

