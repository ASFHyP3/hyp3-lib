"""Custom Exceptions for hyp3lib"""


class GranuleError(Exception):
    """Error to be raised for incompatible or missing granules"""


class ExecuteError(Exception):
    """Error to be raised when executes (managed subprocesses) fail"""
