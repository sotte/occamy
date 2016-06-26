"""
This is a minimal python chat client which connects to the `rooms:lobby` topic.

The server is supposed to be
http://www.phoenixframework.org/docs/channels#section-tying-it-all-together
"""
from __future__ import print_function

try:  # py2
    get_user_input = raw_input
except:  # py3
    get_user_input = input

from occamy import Socket


socket = Socket("ws://localhost:4000/socket")
socket.connect()

channel = socket.channel("rooms:lobby", {})
channel.on("new_msg", lambda msg, x: print("> {}".format(msg["body"])))

channel.join()

print("Enter your message and press return to send the message.")
print()

while True:
    msg = get_user_input("")
    channel.push("new_msg", {"body": msg})
