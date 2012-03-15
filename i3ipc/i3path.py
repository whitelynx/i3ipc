import os


I3_SOCK_ENV_VAR = 'I3SOCK'
I3_SOCK_X_ATOM = 'I3_SOCKET_PATH'


def get():
    for source in (from_env, from_x11, from_xdg, default):
        try:
            path = source()
            if path is not None:
                return path
        except:
            pass

    raise RuntimeError("Couldn't find i3 IPC socket path!")


def from_env():
    env_path = os.environ.get(I3_SOCK_ENV_VAR, None)
    if env_path is not None and os.path.exists(env_path):
        return env_path


def from_x11():
    """Gets the I3 socket path through X11.

    """
    return from_xpyb() or from_python_xlib()


def from_python_xlib():
    """Gets the I3 socket path using python-xlib.

    """
    try:
        from Xlib.display import Display
    except ImportError:
        return None

    display = Display(os.environ.get('DISPLAY', ':0.0'))
    screen = display.screen()
    atom = display.intern_atom(I3_SOCK_X_ATOM, True)
    utf8_string = display.intern_atom('UTF8_STRING', True)
    response = screen.root.get_full_property(atom, utf8_string)
    return response.value


def from_xpyb():
    """Gets the I3 socket path using xpyb.

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

    atom_cookie = conn.core.InternAtom(0, len(I3_SOCK_X_ATOM), I3_SOCK_X_ATOM)
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

    socket_path = xcb_unpack_prop_reply_value(prop_reply)

    if os.path.exists(socket_path):
        return socket_path


def xcb_unpack_prop_reply_value(prop_reply):
    """This is broken out because it probably won't work in all cases.

    """
    return str(prop_reply.value.buf())


def from_xdg():
    try:
        from xdg.BaseDirectory import xdg_config_dirs
    except ImportError:
        return

    for configDir in xdg_config_dirs:
        path = '{}/i3/ipc.sock'.format(configDir)
        if os.path.exists(path):
            return path


def default():
    defaultPath = '~/.config/i3/ipc.sock'
    if os.path.exists(defaultPath):
        return defaultPath
