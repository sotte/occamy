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
from occamy.channel import Channel


socket = Socket("ws://localhost:4000/socket")
socket.connect()

channel = Channel("rooms:lobby", {}, socket)
channel.on("new_msg", lambda msg: print(msg))
# The js syntax is not supported
# channel.on("new_msg", lambda msg: print(msg))\
#     .receive("ok", lambda resp: print("Joined successfully:", resp))\
#     .receive("error", lambda resp: print("Unable to join", resp))

channel.join()

while True:
    print("Channel status:", channel._state)

    msg = get_user_input(">")
    channel.push("new_msg", {"body": msg})
