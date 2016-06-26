"""
This connects to the rooms:lobby channel implemented in
http://www.phoenixframework.org/docs/channels#section-tying-it-all-together

"""
from __future__ import print_function

try:  # py2
    get_user_input = raw_input
except:  # py3
    get_user_input = input

from occamy.socket import Socket


socket = Socket("ws://localhost:4000/socket")
socket.connect()

channel = socket.channel("rooms:lobby", {})
channel.on("new_msg", lambda msg, x: print(msg, x))

channel.join()


while True:
    print("Channel status:", channel._state)
    print()

    msg = get_user_input(">")
    channel.push("new_msg", {"body": msg})
