from threading import Lock, Timer


class RepeatedTimer(object):

    def __init__(self, timeout_ms, function, *args, **kwargs):
        self._timer = None
        self._timeout_ms = timeout_ms
        self._function = function
        self._args = args
        self._kwargs = kwargs
        self._is_running = False
        self._timeouts = 0
        self._lock = Lock()

    def _run(self):
        with self._lock:
            self._timeouts += 1
            self._is_running = False
            self._start_locked()
        self._function(*self._args, **self._kwargs)

    def _start_locked(self):
        if not self._is_running:
            self._is_running = True
            self._timer = Timer(self._timeout(), self._run)
            # Daemon threads don't work correctly in 2.7. Do we care?
            # http://bugs.python.org/issue1856
            # http://bugs.python.org/issue21963
            self._timer.daemon = True
            self._timer.start()

    def start(self):
        with self._lock:
            self._start_locked()

    def cancel(self):
        with self._lock:
            self._timeouts = 0
            if self._timer:
                self._timer.cancel()
            self._is_running = False

    def _timeout(self):
        if hasattr(self._timeout_ms, '__call__'):
            return self._timeout_ms(self._timeouts) / 1000.0
        else:
            return self._timeout_ms / 1000.0
