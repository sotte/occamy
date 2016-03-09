import logging
import functools
from threading import Lock, Timer

class Push:
    def __init__(self, channel, event, payload, timeout):
        self._lock = Lock()
        self._logger = logging.getLogger()
        self._channel = channel
        self._event = event
        self._payload = payload or {}
        self._received_resp = None
        self._timeout = timeout
        self._timer = None
        self._recv_hooks = []
        self._sent = False
        self._ref_event = None

    def resend(self, timeout):
        with self._lock:
            self._timeout = timeout
            self._cancel_ref_event()
            self._ref = None
            self._ref_event = None
            self._received_resp = None
            self._sent = False
            self._send_locked()

    def send(self):
        with self._lock:
            self._send_locked()

    def receive(self, status, callback):
        response = None
        with self._lock:
            if not self._has_received(status):
                self._recv_hooks.append(dict(status=status, callback=callback))
                return self
            else:
                response = self._received_resp['response']
        callback(response)
        return self

    def start_timeout(self):
        with self._lock:
            self._start_timeout_locked()

    def trigger(self, status, response):
        self._channel.trigger(self._ref_event, (status, response))

    def timeout(self):
        return self._timeout

    def _send_locked(self):
        if self._has_received("timeout"):
            return

        self._start_timeout_locked()
        self._sent = True
        self._channel.socket().push(dict(topic=self._channel.topic(),
                                         event=self._event,
                                         payload=self._payload,
                                         ref=self._ref))

    def _received_response(self, payload, ref):
        status = payload.get('status')
        response = payload.get('response')
        ref = payload.get('ref')
        self._logger.debug("received status {status} response {response} ref {ref}".format(
            status=status,
            response=response,
            ref=ref))
        hooks = []
        with self._lock:
            self._cancel_ref_event()
            self._timer.cancel()
            self._timer = None
            self._received_resp = payload
            hooks = filter(lambda hook: hook['status'] == status, self._recv_hooks)

        for hook in map(lambda hook: hook['callback'], hooks):
            hook(response)

    def _start_timeout_locked(self):
        if self._timer:
            return
        self._ref = self._channel.socket().make_ref()
        self._ref_event = self._channel.reply_event_name(self._ref)
        self._channel.on(self._ref_event, self._received_response)
        self._timer = Timer(self._timeout, self._timed_out)
            
    def _timed_out(self):
        with self._lock:
            self._timer = None
        self.trigger("timeout", {})
    
    def _cancel_ref_event(self):
        if not self._ref_event:
            return
        self._channel.off(self._ref_event)

    def _has_received(self, status):
        return self._received_resp and self._received_resp['status'] == status
