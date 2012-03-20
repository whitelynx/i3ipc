import os
import subprocess


I3_SOCK_ENV_VAR = 'I3SOCK'
I3_SOCK_X_ATOM = 'I3_SOCKET_PATH'


def get():
    """Get the I3 socket path, trying several strategies.

    """
    for source in (from_env, from_x11, from_xdg, from_i3, default):
        try:
            path = source()
            if path is not None and os.path.exists(path):
                return path
        except:
            pass

    raise RuntimeError("Couldn't find i3 IPC socket path!")


def from_env():
    """Get the I3 socket path from an environment variable.

    """
    return os.environ.get(I3_SOCK_ENV_VAR, None)


def from_x11():
    """Get the I3 socket path through X11.

    """
    return from_xpyb() or from_python_xlib()


def from_python_xlib():
    """Get the I3 socket path using python-xlib.

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
    """Get the I3 socket path using xpyb.

    I tried to keep this as close to the actual implementation as possible.

    """
    try:
        import xcb
        import xcb.xproto
    except ImportError:
        return None

    conn = xcb.connect()

    setup = conn.get_setup()
    root = setup.roots[conn.pref_screen].root

    atom_cookie = conn.core.InternAtom(0, len(I3_SOCK_X_ATOM), I3_SOCK_X_ATOM)
    atom = atom_cookie.reply().atom

    PATH_MAX = 4096
    prop_cookie = conn.core.GetPropertyUnchecked(False, root, atom, xcb.xproto.GetPropertyType.Any, 0, PATH_MAX)
    prop_reply = prop_cookie.reply()

    return xcb_unpack_prop_reply_value(prop_reply)


def xcb_unpack_prop_reply_value(prop_reply):
    """This is broken out because it probably won't work in all cases.

    """
    return str(prop_reply.value.buf())


def from_xdg():
    """Get the I3 socket path from an environment variable.

    """
    try:
        from xdg.BaseDirectory import xdg_config_dirs
    except ImportError:
        return

    for configDir in xdg_config_dirs:
        path = '{}/i3/ipc.sock'.format(configDir)
        if os.path.exists(path):
            return path


def from_i3():
    try:
        return subprocess.check_output(["i3", "--get-socketpath"])
    except subprocess.CalledProcessError:
        return


def default():
    """Get the default I3 socket path.

    """
    return '~/.config/i3/ipc.sock'
