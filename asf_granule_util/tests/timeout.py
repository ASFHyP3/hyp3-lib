import signal


class TimeoutException(Exception):
    pass


class timeout:
    def __init__(self, seconds, error_message=None):
        if error_message is None:
            error_message = 'test timed out after {}s.'.format(seconds)
        self.seconds = seconds
        self.error_message = error_message

    def handle_timeout(self, signum, frame):
        raise TimeoutException(self.error_message)

    def __enter__(self):
        signal.signal(signal.SIGALRM, self.handle_timeout)
        signal.alarm(self.seconds)

    def __exit__(self, exc_type, exc_val, exc_tb):
        signal.alarm(0)
