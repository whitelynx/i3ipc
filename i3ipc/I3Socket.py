from os import environ
from os.path import expanduser, expandvars, normpath
import json, threading, struct, socket

try:
    from xdg.BaseDirectory import xdg_config_dirs
except ImportError:
    xdg_config_dirs = []

try:
    import xcb
    import xcb.xproto
    from util import socket_path_from_x11

    xcb_socket_path = socket_path_from_x11()
except ImportError:
    xcb_socket_path = None


I3_IPCFILE = environ['I3SOCK'] if 'I3SOCK' in environ\
             else xcb_socket_path if xcb_socket_path\
             else '{}/i3/ipc.sock'.format(xdg_config_dirs[0]) if len(xdg_config_dirs) > 0\
             else '~/.config/i3/ipc.sock'
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
class TypeError(Exception): pass
class BufferError(Exception): pass

class I3Socket(object):
    def __init__(self, ipcfile=None, timeout=I3_SOCKET_TIMEOUT, chunk_size=I3_CHUNK_SIZE):
        self.__chunk_size = chunk_size
        self.__ipcfile = ipcfile if ipcfile else I3_IPCFILE
        self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__socket.settimeout(timeout)
        self.__socket.connect(expanduser(expandvars(normpath(self.__ipcfile))))
        self.__buffer = ''
        self.__event = False
        self.__fmt_header = '<{}sII'.format(len(I3_IPC_MAGIC))
        self.__fmt_header_size = struct.calcsize(self.__fmt_header)

    def send(self, mtype, payload=''):
        """ Format a payload based on mtype (message type) to the window manager. """
        if mtype not in I3_IPC_MESSAGES:
            raise TypeError('Mesage type ({}) does not exit.'.format(mtype))
        message = self.pack(mtype, payload)
        self.__socket.sendall(message)
        data = self.receive()
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

    def receive(self):
        """ Recieve data from the socket. """
        waiting_for_data = True
        while waiting_for_data:
            try:
                data = self.__socket.recv(self.__chunk_size)
                msg_magic, msg_length, msg_type = self.unpack_header(data)
                msg_size = self.__fmt_header_size + msg_length
                while len(data) < msg_size:
                    data = '%s%s' % (data, self.__socket.recv(self.__chunk_size),)
                return '{}{}'.format(self.__buffer, data) if len(self.__buffer) > 0 else data
            except socket.timeout:
                return self.__buffer

    def pack(self, message_type, payload, ipc_magic=I3_IPC_MAGIC):
        """ Pack a message to send over the IPC pipe. """
        return '%s%s%s%s' % (ipc_magic,
                             struct.pack('l', len(payload)),
                             struct.pack('l', message_type),
                             payload)

    def unpack_header(self, data):
        """Unpack response headers from the i3 window manager.

        Returns (msg_magic, msg_length, msg_type)

        """
        return struct.unpack(self.__fmt_header, data[:self.__fmt_header_size])

    def unpack(self, data):
        """ Unpack responses from the i3 window manager. """
        msg_magic, msg_length, msg_type = self.unpack_header(data)
        data_size = len(data)
        msg_size = self.__fmt_header_size + msg_length
        if data_size < msg_size:
            self.__buffer = data
            raise BufferError("Incomplete message in buffer.")
        elif data_size == msg_size or data_size > msg_size:
            msg_payload = json.loads(data[self.__fmt_header_size:msg_size])
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
