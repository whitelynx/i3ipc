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
from . import i3path


I3_IPCFILE = i3path.get()

I3_IPC_MAGIC = 'i3-ipc'
I3_CHUNK_SIZE = 1024
I3_SOCKET_TIMEOUT = 0.5


class Messages(object):
    COMMAND = 0
    GET_WORKSPACES = 1
    SUBSCRIBE = 2
    GET_OUTPUTS = 3
    GET_TREE = 4
    GET_MARKS = 5
    GET_BAR_CONFIG = 6

    @classmethod
    def all(cls):
        return tuple(
                getattr(cls, name)
                for name in dir(cls)
                if name.isupper() and not name.startswith('_')
                )


class Events(object):
    _MASK = 1 << 31
    WORKSPACE = _MASK | 0
    OUTPUT = _MASK | 1

    @classmethod
    def all(cls):
        return tuple(
                getattr(cls, name)
                for name in dir(cls)
                if name.isupper() and not name.startswith('_')
                )


all_replies = Messages.all() + Events.all()


class MagicKeyError(Exception):
    pass


class EventError(Exception):
    pass
