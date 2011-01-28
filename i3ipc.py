from os.path import expanduser, expandvars, normpath
import json, threading, struct, socket

I3_IPCFILE = '~/i3/ipc.sock'            # default location of i3 ipc socket file
I3_IPC_MAGIC = 'i3-ipc'                 # token used to identify i3 messages
I3_CHUNK_SIZE =  4096                   # default receive size

I3_IPC_MESSAGE_TYPE_COMMAND = 0
I3_IPC_MESSAGE_TYPE_GET_WORKSPACES = 1
I3_IPC_MESSAGE_TYPE_SUBSCRIBE = 2
I3_IPC_MESSAGE_TYPE_GET_OUTPUTS = 3

I3_IPC_REPLY_TYPE_COMMAND = 0
I3_IPC_REPLY_TYPE_WORKSPACES = 1
I3_IPC_REPLY_TYPE_SUBSCRIBE = 2
I3_IPC_REPLY_TYPE_OUTPUTS = 3



class WrongMagicKey(Exception):
    """ Exception called when the magic key does not exist. """
    pass



def pack(message_type, payload, ipc_magic=I3_IPC_MAGIC):
    """ Pack a message to send over the IPC pipe. """
    return '%s%s%s%s' % (ipc_magic,
                         struct.pack('l', len(payload)),
                         struct.pack('l', message_type),
                         payload)

def unpack(data):
    """ Unpack responses from the i3 window manager. """
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
    """ Create and return an event listening thread. """
    return I3EventListener(callback, event_list, ipcfile=ipcfile)



class I3Socket:
    def __init__(self, ipcfile=I3_IPCFILE, blocking=True, chunk_size=I3_CHUNK_SIZE):
        self.__chunk_size = chunk_size
        self.__ipcfile = ipcfile
        self.__socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        if not blocking: self.__socket.setblocking(False)
        self.__socket.connect(expanduser(expandvars(normpath(self.__ipcfile))))

    def send(self, mtype, payload=''):
        """ Format a payload based on mtype (message type) to the window manager. """
        message = pack(mtype, payload)
        self.__socket.sendall(message)
        data = self.recieve()
        response = unpack(data)
        return response['payload']

    def recieve(self):
        """ Recieve data from the socket. """
        try:
            data = self.__socket.recv(self.__chunk_size)
            expected_length = int(struct.unpack('l', data[6:10])[0]) + 14
            while len(data) < expected_length:
                data = '%s%s' % (data, self.__socket.recv(self.__chunk_size),)
            return data
        except:
            return None

    def close(self):
        """ close this socket if open. """
        self.__socket.close()

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


class I3EventListener(threading.Thread):
    """ i3 callback event listening thread. """
    def __init__(self, callback, event_list, ipcfile=I3_IPCFILE):
        threading.Thread.__init__(self)
        self.__callback = callback
        self.__socket = I3Socket(ipcfile, blocking=False)
        self.__socket.subscribe(event_list)
        self.__subscribed = True
        self.start()

    def run(self):
        while self.__subscribed:
            data = self.__socket.recieve()
            if data:
                response = unpack(data)['payload']
                self.__callback(response)

    def unsubscribe(self):
        """ Prevent listening to any further events for this subscription. """
        self.__socket.close()
        self.__subscribed = False
