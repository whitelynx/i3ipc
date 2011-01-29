"""
This program is free software: you can redistribute it and/or modify it under
the terms of the GNU Lesser General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License along
with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
from os.path import expanduser, expandvars, normpath
import json, threading, struct, socket

I3_IPCFILE = '~/i3/ipc.sock'            # default location of i3 ipc socket file
I3_IPC_MAGIC = 'i3-ipc'                 # token used to identify i3 messages
I3_CHUNK_SIZE =  1024                   # default receive size
I3_SOCKET_TIMEOUT = 0.5

I3_IPC_MESSAGE_TYPE_COMMAND = 0
I3_IPC_MESSAGE_TYPE_GET_WORKSPACES = 1
I3_IPC_MESSAGE_TYPE_SUBSCRIBE = 2
I3_IPC_MESSAGE_TYPE_GET_OUTPUTS = 3
I3_IPC_MESSAGES = (I3_IPC_MESSAGE_TYPE_COMMAND, I3_IPC_MESSAGE_TYPE_GET_WORKSPACES, I3_IPC_MESSAGE_TYPE_SUBSCRIBE, I3_IPC_MESSAGE_TYPE_GET_OUTPUTS,)

I3_IPC_REPLY_TYPE_COMMAND = 0
I3_IPC_REPLY_TYPE_WORKSPACES = 1
I3_IPC_REPLY_TYPE_SUBSCRIBE = 2
I3_IPC_REPLY_TYPE_OUTPUTS = 3
I3_IPC_REPLIES = (I3_IPC_REPLY_TYPE_COMMAND, I3_IPC_REPLY_TYPE_WORKSPACES, I3_IPC_REPLY_TYPE_SUBSCRIBE, I3_IPC_REPLY_TYPE_OUTPUTS,)


class MagicKeyError(Exception): pass
class TypeError(Exception): pass


def pack(message_type, payload, ipc_magic=I3_IPC_MAGIC):
    """ Pack a message to send over the IPC pipe. """
    return '%s%s%s%s' % (ipc_magic,
                         struct.pack('l', len(payload)),
                         struct.pack('l', message_type),
                         payload)

def unpack(data):
    """ Unpack responses from the i3 window manager. """
    fmt_header = '<{}sll'.format(len(I3_IPC_MAGIC))
    fmt_header_size = struct.calcsize(fmt_header)
    fmt_payload_size = len(data) - fmt_header_size
    fmt_message = '{}{}s'.format(fmt_header, fmt_payload_size)
    msg_magic, msg_length, msg_type, msg_payload = struct.unpack(fmt_message, data)

    response =  {
        'magic': msg_magic,
        'length': msg_length,
        'type': msg_type,
        'payload': json.loads(msg_payload),
    }

    print "magic: {}\n"\
          "length: {}\n"\
          "type: {}\n"\
          "response[type]: {}\n"\
          "data:\n{}\n{}\n{}\n"\
          .format(data[:6],
                  struct.unpack('l', data[6:10])[0],
                  struct.unpack('l', data[10:14])[0],
                  response['type'],
                  '-'*40,
                  data,
                  '-'*40)

    #if response['magic'] != I3_IPC_MAGIC:
        #raise MagicKeyError('Invalid key ({}) provided.'.format(response['magic']))
    #elif response['type'] not in I3_IPC_REPLIES:
        #raise TypeError('Invalid reply type ({}) provided.'.format(response['type']))

    return response

def subscribe(callback, event_list, ipcfile=I3_IPCFILE):
    """ Create and return an event listening thread. """
    return I3EventListener(callback, event_list, ipcfile=ipcfile)



class I3Socket(object):
    def __init__(self, ipcfile=I3_IPCFILE, timeout=I3_SOCKET_TIMEOUT, chunk_size=I3_CHUNK_SIZE):
        self.__chunk_size = chunk_size
        self.__ipcfile = ipcfile
        self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        #self.__socket.settimeout(timeout)
        self.__socket.connect(expanduser(expandvars(normpath(self.__ipcfile))))

    def send(self, mtype, payload='', raw=False):
        """ Format a payload based on mtype (message type) to the window manager. """
        if mtype not in I3_IPC_MESSAGES:
            raise TypeError('Mesage type ({}) does not exit.'.format(mtype))
        message = pack(mtype, payload)
        self.__socket.sendall(message)
        data = self.recieve()
        return data if raw else unpack(data)['payload']

    def send_command(self, payload):
        """ Send a command to window manager. """
        return self.send(I3_IPC_MESSAGE_TYPE_COMMAND, payload)

    def get_workspaces(self):
        """ Return a list of workspaces. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES)

    def get_outputs(self):
        """ Returns a list of of available outpus. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_OUTPUTS)

    def subscribe(self, subscriptions):
        """ Subscribe to an event over this socket. Used by I3EventListener. """
        payload = json.dumps(subscriptions)
        return self.send(I3_IPC_MESSAGE_TYPE_SUBSCRIBE, payload)

    def recieve(self):
        """ Recieve data from the socket. """
        waiting_for_data = True
        while waiting_for_data:
            try:
                data = self.__socket.recv(self.__chunk_size)
                expected_length = int(struct.unpack('l', data[6:10])[0]) + 14
                while len(data) < expected_length:
                    data = '%s%s' % (data, self.__socket.recv(self.__chunk_size),)
                return data
            except socket.timeout:
                pass

    def close(self):
        """ close this socket if open. """
        self.__socket.close()


class I3EventListener(threading.Thread):
    """ Self-starting thread to listen for a single window manager event.

        callback(thread, data): when data is returned from the socket it is read
            and returned to the callback method as the second argument. The first
            argument is a copy of the thread.

        unsubscribe(): stop listening to this event. """
    def __init__(self, callback, event_list, ipcfile=I3_IPCFILE, timeout=I3_SOCKET_TIMEOUT, raw=False):
        threading.Thread.__init__(self)
        self.__callback = callback
        self.__socket = I3Socket(ipcfile, timeout=timeout)
        self.__socket.subscribe(event_list)
        self.__subscribed = True
        self.__raw = raw
        self.start()

    def run(self):
        while self.__subscribed:
            data = self.__socket.recieve()
            response = data if self.__raw else unpack(data)['payload']
            self.__callback(self, response)

    def unsubscribe(self):
        """ Prevent listening to any further events for this subscription. """
        self.__socket.close()
        self.__subscribed = False


if __name__ == '__main__':
    ipcfile = '~/.config/i3/ipc.sock'
    sock = I3Socket(ipcfile)

    def listener(caller, data):
        #print(data)
        pass
    evt = subscribe(listener, ['workspace'], ipcfile)
    try:
        while evt.is_alive():
            pass
    except KeyboardInterrupt:
        evt.unsubscribe()
        exit(0)
