import logging
import urllib
import json
from occamy.channel import Channel
from threading import Lock
from repeated_timer import RepeatedTimer
from ws4py.client.threadedclient import WebSocketClient


class WebSocketObserver:
    def opened(self):
        pass

    def closed(self, code, reason):
        pass

    def received_message(self, msg):
        pass

    def unhandled_error(self, error):
        pass


class WebSocketImpl(WebSocketClient):
    def __init__(self, observers=[], *args, **kwargs):
        super(WebSocketImpl, self).__init__(*args, **kwargs)
        self._observers = observers
        self._lock = Lock()

    def add_observer(self, observer):
        with self._lock:
            self._observers.append(observer)

    def remove_observer(self, observer):
        with self._lock:
            self._observers = filter(lambda o: o != observer, self._observers)

    def remove_observers(self):
        observers = []
        with self._lock:
            observers = self._observers
            self._observers = []
        return observers

    def opened(self):
        for observer in self._get_observers():
            observer.opened()

    def closed(self, code, reason):
        for observer in self._get_observers():
            observer.closed(code, reason)

    def received_message(self, msg):
        for observer in self._get_observers():
            observer.received_message(msg)

    def unhandled_error(self, error):
        for observer in self._get_observers():
            observer.unhandled_error(error)

    def _get_observers(self):
        with self._lock:
            return self._observers[:]


class Socket(WebSocketObserver):
    DEFAULT_TIMEOUT_MS    = 10000
    HEARTBEAT_INTERVAL_MS = 30000
    RECONNECT_AFTER_MS    = 5000
    VSN                   = "1.0.0"

    def __init__(self,
                 endpoint,
                 params={},
                 timeout=DEFAULT_TIMEOUT_MS,
                 heartbeat_interval_ms=HEARTBEAT_INTERVAL_MS,
                 reconnect_after_ms=None):
        self._endpoint_url = Socket._endpoint_url("{endpoint}/websocket".format(endpoint=endpoint), params)
        self._websocket_impl = WebSocketImpl([self], self._endpoint_url)
        self._logger = logging.getLogger()
        self._timeout = timeout
        self._lock = Lock()
        self._opened = False
        self._channels = []
        self._send_buffer = []
        self._ref = 0
        self._heartbeat_timer = RepeatedTimer(heartbeat_interval_ms, self._send_heartbeat)
        self._reconnect_after_ms = reconnect_after_ms or Socket._reconnect_after_ms
        self._reconnect_timer = RepeatedTimer(self._reconnect_after_ms, self._reconnect)

    # Observer API
    def opened(self):
        self._logger.debug("transport connected to {url}".format(url=self._endpoint_url))
        with self._lock:
            self._opened = True
            self._reconnect_timer.cancel()
            self._heartbeat_timer.start()
            self._flush_send_buffer_locked()

    def closed(self, code, reason):
        self._logger.debug("transport closed with {code}, reason {reason}".format(code=code, reason=reason))
        channels = []
        with self._lock:
            self._opened = False
            self._heartbeat_timer.cancel()
            self._reconnect_timer.start()
            channels = self._channels[:]
        for channel in channels:
            channel.trigger(Channel.EVENTS['error'])

    def received_message(self, msg):
        msg = json.loads(str(msg))
        if not all(k in msg for k in ('payload', 'topic', 'event')):
            return

        ref = msg.get('ref')
        event = msg.get('event')
        topic = msg.get('topic')
        payload = msg.get('payload')
        status = payload.get('status')

        self._logger.debug("receive status: {status} topic: {topic} event: {event} {ref}".format(
            status=status,
            topic=topic,
            event=event,
            ref=ref))

        channels = []
        with self._lock:
            channels = filter(lambda ch: ch.is_member(topic), self._channels)

        for channel in channels:
            channel.trigger(event, payload, ref)

    def unhandled_error(self, error):
        self._logger.debug("transport error {error}".format(error=error))
        channels = []
        with self._lock:
            self._opened = False
            channels = self._channels[:]
        for channel in channels:
            channel.trigger(Channel.EVENTS['error'])

    def reconnect_after_ms(self):
        return self._reconnect_after_ms

    def timeout(self):
        return self._timeout

    def is_connected(self):
        return self._opened == True

    def connect(self):
        self._websocket_impl.connect()

    def disconnect(self, callback=None, code=1000, reason=''):
        self._websocket_impl.close(code, reason)

    def remove(self, channel):
        with self._lock:
            self._channels = filter(lambda ch: not ch.is_member(channel.topic), self._channels)

    def channel(self, topic, params):
        channel = Channel(topic, params, self)
        with self._lock:
            self._channels.append(channel)
        return channel

    def push(self, data):
        with self._lock:
            self._send_buffer.append(json.dumps(data))
            if not self._flush_send_buffer_locked():
                self._logger.debug("push topic: {topic} event: {event} ref: {ref}".format(
                    topic=data['topic'],
                    event=data['event'],
                    ref=data['ref']))

    def on(self, observer):
        self._websocket_impl.add_observer(observer)

    def off(self, observer):
        self._websocket_impl.remove_observer(observer)

    def make_ref(self):
        with self._lock:
            self._ref += 1
            return str(self._ref)

    def _flush_send_buffer_locked(self):
        if self._websocket_impl and self.is_connected():
            for data in self._send_buffer:
                self._logger.debug("flush {data}".format(data=data))
                self._websocket_impl.send(data)
                self._send_buffer = []
            return True
        else:
            return False

    def _reconnect(self):
        with self._lock:
            observers = self._websocket_impl.remove_observers()
            self._websocket_impl = WebSocketImpl(observers, self._endpoint_url)
            self._websocket_impl.connect()

    def _send_heartbeat(self):
        self.push(dict(topic="phoenix", event="heartbeat", payload={}, ref=self.make_ref()))

    @staticmethod
    def _reconnect_after_ms(timeouts):
        try:
            return [1000, 2000, 5000, 10000][timeouts]
        except:
            return 10000

    @staticmethod
    def _endpoint_url(endpoint, params, protocol='wss'):
        params = params.copy()
        params.update(dict(vsn = Socket.VSN))
        prefix = '&' if '?' in endpoint else '?'
        uri = endpoint + prefix + urllib.urlencode(params)
        if uri[0] != '/':
            return uri
        elif uri[1] == '/':
            return protocol + ":" + uri
        else:
            raise RuntimeError("expected endpoint to include domain")
