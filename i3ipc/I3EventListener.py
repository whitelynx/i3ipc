import threading
from I3Socket import I3Socket,\
                     I3_SOCKET_TIMEOUT,\
                     I3_IPCFILE,\
                     I3_IPC_EVENTS,\
                     I3_IPC_EVENT_OUTPUT,\
                     I3_IPC_EVENT_WORKSPACE


class EventError(Exception): pass

class I3EventListener(threading.Thread):
    """ Self-starting thread to listen for a single window manager event.

        callback(thread, data): when data is returned from the socket it is read
            and returned to the callback method as the second argument. The first
            argument is a copy of the thread.

        unsubscribe(): stop listening to this event. """
    def __init__(self, callback, event_type, event_other=None, ipcfile=I3_IPCFILE, timeout=I3_SOCKET_TIMEOUT):
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
                    if response['payload']['change'] == self.__event_filter or not self.__event_filter:
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
