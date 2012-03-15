import os


class SocketPath(object):
    @staticmethod
    def get():
        for source in (
                SocketPath.from_env,
                SocketPath.from_x11,
                SocketPath.from_xdg,
                SocketPath.default
                ):
            path = source()
            if path is not None:
                break

    @staticmethod
    def from_env():
        if 'I3SOCK' in os.environ:
            return os.environ['I3SOCK']

    @staticmethod
    def from_x11():
        '''Gets the I3 socket path through X11.

        '''
        return SocketPath.from_xpyb() or SocketPath.from_python_xlib()

    @staticmethod
    def from_python_xlib():
        '''Gets the I3 socket path using python-xlib.

        '''

    @staticmethod
    def from_xpyb():
        """Gets the I3 socket path using xcb/xpyb.

        I tried to keep this as close to the actual implementation as possible.

        """
        try:
            import xcb
            import xcb.xproto
        except ImportError:
            return None

        PATH_MAX = 4096
        try:
            conn = xcb.connect()
        except:
            return None
        if conn == None:
            return None

        setup = conn.get_setup()

        screens = setup.roots
        root_screen = screens[conn.pref_screen]
        root = root_screen.root

        atom_cookie = conn.core.InternAtom(0, len("I3_SOCKET_PATH"), "I3_SOCKET_PATH")
        atom_reply = atom_cookie.reply()
        if not atom_reply:  # I don't know if ...cookie.reply() will ever be None, but if it is I'll be ready
            return None

        prop_cookie = conn.core.GetPropertyUnchecked(False, root, atom_reply.atom,
                xcb.xproto.GetPropertyType.Any, 0, PATH_MAX)
        prop_reply = prop_cookie.reply()

        if not prop_reply:  # I don't know if ...cookie.reply() will ever be None, but if it is I'll be ready
            return None
        if not prop_reply.value_len:
            return None

        socket_path = SocketPath.xcb_unpack_prop_reply_value(prop_reply)

        return socket_path

    @staticmethod
    def xcb_unpack_prop_reply_value(prop_reply):
        '''This is broken out because it probably won't work in all cases.

        '''
        return str(prop_reply.value.buf())

    @staticmethod
    def from_xdg():
        try:
            from xdg.BaseDirectory import xdg_config_dirs
        except ImportError:
            return

        for configDir in xdg_config_dirs:
            path = '{}/i3/ipc.sock'.format(configDir)
            if os.path.exists(path):
                return path

    @staticmethod
    def default():
        return '~/.config/i3/ipc.sock'
