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
from os import environ

I3_IPCFILE = environ['I3PATH'] if 'I3PATH' in environ else '~/.config/i3/ipc.sock'
I3_IPC_MAGIC = 'i3-ipc'
I3_CHUNK_SIZE =  1024
I3_SOCKET_TIMEOUT = 0.5

I3_IPC_MESSAGE_TYPE_COMMAND = 0
I3_IPC_MESSAGE_TYPE_GET_WORKSPACES = 1
I3_IPC_MESSAGE_TYPE_SUBSCRIBE = 2
I3_IPC_MESSAGE_TYPE_GET_OUTPUTS = 3

I3_IPC_REPLY_TYPE_COMMAND = 0
I3_IPC_REPLY_TYPE_WORKSPACES = 1
I3_IPC_REPLY_TYPE_SUBSCRIBE = 2
I3_IPC_REPLY_TYPE_OUTPUTS = 3

I3_IPC_EVENT_MASK = 1 << 31
I3_IPC_EVENT_WORKSPACE = I3_IPC_EVENT_MASK | 0
I3_IPC_EVENT_OUTPUT = I3_IPC_EVENT_MASK | 1

I3_IPC_MESSAGES = (I3_IPC_MESSAGE_TYPE_COMMAND,
                   I3_IPC_MESSAGE_TYPE_GET_WORKSPACES,
                   I3_IPC_MESSAGE_TYPE_SUBSCRIBE,
                   I3_IPC_MESSAGE_TYPE_GET_OUTPUTS,)
I3_IPC_REPLIES = (I3_IPC_REPLY_TYPE_COMMAND,
                  I3_IPC_REPLY_TYPE_WORKSPACES,
                  I3_IPC_REPLY_TYPE_SUBSCRIBE,
                  I3_IPC_REPLY_TYPE_OUTPUTS,)
I3_IPC_EVENTS = (I3_IPC_EVENT_WORKSPACE,
                 I3_IPC_EVENT_OUTPUT,)
I3_IPC_ALL_REPLIES = (I3_IPC_REPLY_TYPE_COMMAND,
                      I3_IPC_REPLY_TYPE_WORKSPACES,
                      I3_IPC_REPLY_TYPE_SUBSCRIBE,
                      I3_IPC_REPLY_TYPE_OUTPUTS,
                      I3_IPC_EVENT_WORKSPACE,
                      I3_IPC_EVENT_OUTPUT,)


class MagicKeyError(Exception): pass
class EventError(Exception): pass
class TypeError(Exception): pass
class BufferError(Exception): pass


class I3Socket(object):
    def __init__(self, ipcfile=I3_IPCFILE, timeout=I3_SOCKET_TIMEOUT, chunk_size=I3_CHUNK_SIZE):
        self.__chunk_size = chunk_size
        self.__ipcfile = ipcfile
        self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__socket.settimeout(timeout)
        self.__socket.connect(expanduser(expandvars(normpath(self.__ipcfile))))
        self.__buffer = ''
        self.__event = False

    def send(self, mtype, payload=''):
        """ Format a payload based on mtype (message type) to the window manager. """
        if mtype not in I3_IPC_MESSAGES:
            raise TypeError('Mesage type ({}) does not exit.'.format(mtype))
        message = self.pack(mtype, payload)
        self.__socket.sendall(message)
        data = self.recieve()
        return self.unpack(data)

    def send_command(self, payload):
        """ Send a command to window manager. """
        return self.send(I3_IPC_MESSAGE_TYPE_COMMAND, payload)

    def get_workspaces(self):
        """ Return a list of workspaces. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES)

    def get_outputs(self):
        """ Returns a list of of available outpus. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_OUTPUTS)

    def subscribe(self, event_type, event_other=''):
        """ Subscribe to an event over this socket. Used by I3EventListener. """
        if event_type in I3_IPC_EVENTS:
            self.__event = True
            event = [ 'output' ] if event_type == I3_IPC_EVENT_OUTPUT\
                    else [ 'workspace' ] if event_type == I3_IPC_EVENT_WORKSPACE\
                    else []
            if event_other:
                event.append(event_other)
            payload = json.dumps(event)
        else:
            raise EventError("Invalid event type.")
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
                return '{}{}'.format(self.__buffer, data) if len(self.__buffer) > 0 else data
            except socket.timeout:
                return self.__buffer

    def has_unused_events(self):
        """ Return length of __unused_events. """
        return len(self.__unused_events)

    def get_unused_event(self):
        """ Return topmost unuxed event. """
        if self.has_unused_events():
            return self.__unused_events.pop(0)
        else:
            return None

    def pack(self, message_type, payload, ipc_magic=I3_IPC_MAGIC):
        """ Pack a message to send over the IPC pipe. """
        return '%s%s%s%s' % (ipc_magic,
                             struct.pack('l', len(payload)),
                             struct.pack('l', message_type),
                             payload)

    def unpack(self, data):
        """ Unpack responses from the i3 window manager. """
        fmt_header = '<{}sII'.format(len(I3_IPC_MAGIC))
        fmt_header_size = struct.calcsize(fmt_header)
        msg_magic, msg_length, msg_type = struct.unpack(fmt_header, data[:fmt_header_size])

        data_size = len(data)
        msg_size = fmt_header_size + msg_length
        if data_size < msg_size:
            self.__buffer = data
            raise BufferError("Incomplete message in buffer.")
        elif data_size == msg_size or data_size > msg_size:
            msg_payload = json.loads(data[fmt_header_size:msg_size])
            self.__buffer = data[msg_size:]
        else:
            raise Exception('Something strange is going on with the data length.')

        response = {
            'magic': msg_magic,
            'length': msg_length,
            'type': msg_type,
            'payload': msg_payload,
        }

        if response['magic'] != I3_IPC_MAGIC:
            raise MagicKeyError('Invalid key ({}).'.format(response['magic']))
        if response['type'] not in I3_IPC_ALL_REPLIES:
            raise TypeError('Invalid reply type. ({})'.format(response['type']))
        return response

    def close(self):
        """ close this socket if open. """
        self.__socket.close()


class I3EventListener(threading.Thread):
    """ Self-starting thread to listen for a single window manager event.

        callback(thread, data): when data is returned from the socket it is read
            and returned to the callback method as the second argument. The first
            argument is a copy of the thread.

        unsubscribe(): stop listening to this event. """
    def __init__(self, callback, event_type, event_other='', ipcfile=I3_IPCFILE, timeout=I3_SOCKET_TIMEOUT):
        threading.Thread.__init__(self)
        self.__event_type = event_type
        self.__event_filter = event_other
        self.__callback = callback

        self.__evsocket = I3Socket(ipcfile, timeout)
        self.__evsocket.subscribe(event_type, event_other)

        self.__elsocket = I3Socket(ipcfile, timeout)

        self.__subscribed = False
        self.start()

    def run(self):
        self.__subscribed = True

        while self.__subscribed:
            data = self.__evsocket.recieve()
            while data and self.__subscribed:
                response = self.__evsocket.unpack(data)
                if response and response['type'] in I3_IPC_EVENTS:
                    response['event_payload'] = self.__elsocket.get_outputs() if self.__event_type == I3_IPC_EVENT_OUTPUT\
                                                else self.__elsocket.get_workspaces() if self.__event_type == I3_IPC_EVENT_WORKSPACE\
                                                else None
                    self.__callback(self, response)
                data = self.__evsocket.recieve()

        self.__evsocket.close()
        self.__elsocket.close()

    def unsubscribe(self):
        """ Prevent listening to any further events for this subscription. """
        self.__subscribed = False

    def close(self):
        self.unsubscribe()

def subscribe(callback, event_id, event_other='', ipcfile=I3_IPCFILE):
    """ Create and return an event listening thread. """
    return I3EventListener(callback, event_id, event_other, ipcfile)
