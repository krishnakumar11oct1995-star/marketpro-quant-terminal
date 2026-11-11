class FinError(Exception):
    pass


class DataError(FinError):
    pass


class NetworkError(DataError):
    pass


class CacheError(DataError):
    pass


class ConfigError(FinError):
    pass


class AgentError(FinError):
    pass


class TradingError(FinError):
    pass
