try:
  import xcb
  import xcb.xproto
except ImportError:
  pass

def unpack_prop_reply_value(prop_reply):
    '''unpack_prop_reply_value:
        This is broken out because it probably won't work in all cases.
    '''
    return str(prop_reply.value.buf())

def socket_path_from_x11():
    '''socket_path_from_x11:
        I tried to keep this as close to the actual implementation as possible.
        Note: This requires xpyb. This will not end well if you try to use it before
              importing xcb and xcb.xproto.
    '''
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
    if not atom_reply: # I don't know if ...cookie.reply() will ever be None, but if it is I'll be ready
        return None

    prop_cookie = conn.core.GetPropertyUnchecked(False, root, atom_reply.atom,
                                                 xcb.xproto.GetPropertyType.Any, 0, PATH_MAX)
    prop_reply = prop_cookie.reply()

    if not prop_reply: # I don't know if ...cookie.reply() will ever be None, but if it is I'll be ready
        return None
    if not prop_reply.value_len:
        return None

    socket_path = unpack_prop_reply_value(prop_reply)

    return socket_path
