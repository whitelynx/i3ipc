from os.path import expanduser, expandvars, normpath
import json, threading, struct, socket, time

I3_IPCFILE = '~/i3/ipc.sock'            # default location of i3 ipc socket file
I3_IPC_MAGIC = 'i3-ipc'                 # token used to identify i3 messages
I3_CHUNK_SIZE = 1024                    # default receive size
I3_EVENT_DELAY = 1                      # event thread sleep times

I3_IPC_MESSAGE_TYPE_COMMAND = 0
I3_IPC_MESSAGE_TYPE_GET_WORKSPACES = 1
I3_IPC_MESSAGE_TYPE_SUBSCRIBE = 2
I3_IPC_MESSAGE_TYPE_GET_OUTPUTS = 3

I3_IPC_REPLY_TYPE_COMMAND = 0
I3_IPC_REPLY_TYPE_WORKSPACES = 1
I3_IPC_REPLY_TYPE_SUBSCRIBE = 2
I3_IPC_REPLY_TYPE_OUTPUTS = 3



class WrongMagicKey(Exception):
    pass



def pack(message_type, payload, ipc_magic=I3_IPC_MAGIC):
    """ Pack a message to send over the IPC pipe. """
    return '%s%s%s%s' % (ipc_magic,
                         struct.pack('l', len(payload)),
                         struct.pack('l', message_type),
                         payload)

def unpack(data):
    """ Unpack responses from the i3 window manager. """
    # works on x86_64, cannot vouch for anything else at this time.
    # should probably do proper length calculations for the long integers.
    response =  {
        'magic': data[:6],
        'total_length': len(data),
        'length': struct.unpack('l', data[6:10])[0],
        'type': struct.unpack('l', data[10:14])[0],
        'payload_length': len(data[14:]),
        'payload': json.loads(data[14:]),
    }
    if response['magic'] != I3_IPC_MAGIC:
        raise WrongMagicKey()
    return response

def subscribe(callback, event_list, ipcfile=I3_IPCFILE):
    """ Create and return an event listening thread. Each time the window
    manager returns event data it is passed as a single argument to callback.
    To stop listening to events, call the unsubscribe method on the returned
    event thread. No arguments should be supplied. """
    return I3EventListener(callback, event_list, ipcfile=ipcfile)



class I3Socket:
    def __init__(self, ipcfile=I3_IPCFILE, blocking=True):
        self.__ipcfile = ipcfile
        self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.__socket.setblocking(blocking)
        self.__socket.connect(expanduser(expandvars(normpath(self.__ipcfile))))

    def send(self, mtype, payload=''):
        """ Open and sends a message to the window manager, returing a json
        parsed response.

        By setting the keepopen option to False will close the socket after send.

        By default a socket is using I3_IPCFILE. If an ipcfile argument is supplied
        the module will store the new position for future reference. So ipcfile must
        only be set once."""
        self.__socket.send(pack(mtype, payload))
        response = unpack(self.recieve())['payload']
        return response

    def send_command(self, payload):
        """ Send a command to window manager. """
        return self.send(I3_IPC_MESSAGE_TYPE_COMMAND, payload)

    def get_workspaces(self):
        """ Return a list of workspaces. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_WORKSPACES)

    def get_outputs(self):
        """ Returns a list of of available outpus. """
        return self.send(I3_IPC_MESSAGE_TYPE_GET_OUTPUTS)

    def close(self):
        """ close this socket if open. """
        self.__socket.close()

    def recieve(self):
        """ Recieve data from the socket. """
        data = self.__socket.recv(I3_CHUNK_SIZE)
        expected_length = int(struct.unpack('l', data[6:10])[0]) + 14
        while len(data) < expected_length:
            data = '%s%s' % (data, self.__socket.recv(I3_CHUNK_SIZE),)
        return data


class I3EventListener(threading.Thread):
    """ i3 callback event listening thread. """
    def __init__(self, callback, event_list, ipcfile=I3_IPCFILE):
        threading.Thread.__init__(self)
        self.__socket = I3Socket(ipcfile, False)
        self.__callback = callback
        subscription = json.dumps(event_list)
        response = self.__socket.send(I3_IPC_MESSAGE_TYPE_SUBSCRIBE, subscription)
        self.__subscribed = True
        self.start()

    def run(self):
        while self.__subscribed:
            try:
                data = self.__socket.recieve()
                response = unpack(data)['payload']
                self.__callback(response)
            except:
                pass

    def unsubscribe(self):
        self.__socket.close()
        self.__subscribed = False



if __name__ == '__main__':
    def printit(data):
        print 'response: %s' % (data,)

    ipcfile = '~/.config/i3/ipc.sock'
    i3s = I3Socket(ipcfile)
    i3e = subscribe(printit, 'workspace', ipcfile=ipcfile)
