from socket import socket, AF_UNIX
from os.path import expanduser, expandvars, normpath
from struct import pack, unpack
import json

from exceptions import *

I3_IPCFILE = '~/i3/ipc.sock'            # default location of i3 ipc socket file
I3_IPC_MAGIC = 'i3-ipc'                 # token used to identify i3 messages
I3_CHUNK_SIZE = 1024                    # default receive size

I3_IPC_MESSAGE_TYPE_COMMAND = 0
I3_IPC_MESSAGE_TYPE_GET_WORKSPACES = 1
I3_IPC_MESSAGE_TYPE_SUBSCRIBE = 2
I3_IPC_MESSAGE_TYPE_GET_OUTPUTS = 3

I3_IPC_REPLY_TYPE_COMMAND = 0
I3_IPC_REPLY_TYPE_WORKSPACES = 1
I3_IPC_REPLY_TYPE_SUBSCRIBE = 2
I3_IPC_REPLY_TYPE_OUTPUTS = 3


class I3Socket:
    def __init__(self, ipcfile=I3_IPCFILE):
        self.__ipcfile = expanduser(expandvars(normpath(ipcfile)))
        self.__socket = socket(AF_UNIX)
        self.__socket.connect(self.__ipcfile)

    def __pack_message(self, message_type, payload):
        package = [I3_IPC_MAGIC]
        package.append(pack('l', len(payload)))
        package.append(pack('l', message_type))
        package.append(payload)
        return ''.join(package)

    def __unpack_response(self, data):
        response =  {
            'magic': data[:6],
            'total_length': len(data),
            'length': unpack('l', data[6:10])[0],
            'type': unpack('l', data[10:14])[0],
            'payload_length': len(data[14:]),
            'payload': json.loads(data[14:]),
        }
        if response['magic'] != I3_IPC_MAGIC:
            raise MagicKeyError()
        self.__last_response = response
        return response

    def close(self):
        """ Close the socket. """
        self.__socket.close()

    def send(self, mtype, payload=''):
        """ Send a raw message to the window manager. """
        message = self.__pack_message(mtype, payload)
        self.__socket.send(message)
        def expected_length(data):
            return int(unpack('l', data[6:10])[0]) + 14
        data = self.__socket.recv(I3_CHUNK_SIZE)
        while len(data) < expected_length(data):
            data = '%s%s' % (data, self.__socket.recv(I3_CHUNK_SIZE),)
        return self.__unpack_response(data)

    def send_command(self, payload):
        """ Send a command to window manager. """
        return self.send(I3_IPC_MESSAGE_TYPE_COMMAND, payload)

    def get_workspaces(self, workspace=None, raw=False):
        """ Return a list of workspaces. """
        response = self.send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES)
        return response if raw else response['payload']

    def get_workspace(self, index):
        """ Query workspaces by index (zero-based) or name (unicode string). """
        workspaces = self.send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES)['payload']
        index_type = type(index)
        if index_type == int:
            if index < len(workspaces):
                return response['payload'][workspace]
            else:
                raise NotFoundError("Index %s not in range of %s." % (index, len(workspaces),))
        elif index_type == str:
            for workspace in workspaces:
                if workspace['name'].endswith(": %s" % (index,)):
                    return workspace
            raise NotFoundError("Workspace '%s' does not exist." % (index,))

    def get_outputs(self, raw=False):
        """ Returns a list of of available outpus. """
        response = self.send(I3_IPC_MESSAGE_TYPE_GET_OUTPUTS)
        return response if raw else response['payload']



if __name__ == '__main__':
    # test location for XDG_CONFIG_HOME
    i3s = I3Socket('~/.config/i3/ipc.sock')
