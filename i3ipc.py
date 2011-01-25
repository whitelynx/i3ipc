#!/usr/bin/env python

from struct import pack, unpack
from os import path
import socket, json

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

__event_handlers = {}                   # subscribed event handlers


def get_ipcfile_path(path):
    return os.path.expanduser(os.path.expanvars(os.path.normpath(path)))

def pack_message(*args):
    package = []
    for arg in args:
        arg_type = type(arg)
        if arg_type == str: package.append(arg)
        elif arg_type == int: package.append(pack('l', arg))
    return ''.join(package)

def unpack_response(data):
    response =  {
        'magic': data[:6],
        'total_length': len(data),
        'length': unpack('l', data[6:10])[0],
        'type': unpack('l', data[10:14])[0],
        'payload_length': len(data[14:]),
        'payload': json.loads(data[14:]),
    }
    if response['magic'] != I3_IPC_MAGIC:
        raise ValueError()
    return response

def send(mtype, payload='', ipcfile=I3_IPCFILE):
    ipcfile = path.expanduser(path.expandvars(path.normpath(ipcfile)))
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    message = pack_message(I3_IPC_MAGIC, len(payload), mtype, payload)
    s.connect(ipcfile)
    s.send(message)
    def expected_length(data):
        return int(unpack('l', data[6:10])[0]) + 14
    data = s.recv(I3_CHUNK_SIZE)
    while len(data) < expected_length(data):
        data = '%s%s' % (data, s.recv(I3_CHUNK_SIZE),)
    #s.close()
    return unpack_response(data)

def send_command(payload, ipcfile=I3_IPCFILE):
    return send(I3_IPC_MESSAGE_TYPE_COMMAND, payload, ipcfile)

def get_workspaces(ipcfile=I3_IPCFILE):
    return send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES, ipcfile=ipcfile)

def get_outputs(ipcfile=I3_IPCFILE):
    return send(I3_IPC_MESSAGE_TYPE_GET_OUTPUTS, ipcfile=ipcfile)

def subscribe(event, handler, icpfile=I3_IPCFILE):
    __event_handlers[event] = handler
    pass


"""
Called when file is directly run.
Useful only for testing as this module will not have any immediate use.
"""
if __name__ == '__main__':
    ipcfile = '~/.config/i3/ipc.sock'
    
