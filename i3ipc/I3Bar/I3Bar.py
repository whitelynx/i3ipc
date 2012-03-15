import subprocess
from i3ipc import subscribe, I3Socket, I3_IPCFILE, I3_IPC_EVENT_WORKSPACE


class I3Bar(object):
    FMT_BAR = "^p(_LEFT) {}^p(_RIGHT) \n"
    FMT_BTN = "^bg({})^ca(1,i3ipc -s {})[ {} ]^ca()"

    def __init__(self, dzen=None, font=None, ipcfile=I3_IPCFILE):
        dzen_args = [dzen, '-dock']
        if font:
            dzen_args.append('-fn {}'.format(font))
        self.dzen = subprocess.Popen(dzen_args, stdin=subprocess.PIPE)
        self.ipcfile = ipcfile
        self.barfmt = I3Bar.FMT_BAR
        self.btnfmt = I3Bar.FMT_BTN

        # initial display
        i3 = I3Socket(ipcfile=self.ipcfile)
        self.init(self, i3.get_workspaces())
        i3.close()

    def listener(self, caller, data):
        getattr(self, data['payload']['change'])(caller, data['event_payload'])

    def init(self, caller, data):
        self.bar = '^pa(_LEFT)'

        for ws in data['payload']:
            bgcolor = '#AA3333' if ws['urgent'] else '#333333' if ws['visible'] else ''
            wsnumber = ws['name'].split(':')[0] if ':' in ws['name'] else ws['name']

            wsbtn = self.btnfmt.format(bgcolor, wsnumber, ws['name'])
            self.bar = "{}{}".format(self.bar, wsbtn)

        self.dzen.stdin.write(self.barfmt.format(self.bar))

    def focus(self, event, data):
        self.init(event, data)

    def urgent(self, event, data):
        self.init(event, data)

    def empty(self, event, data):
        pass

    def loop(self):
        self.i3ev = subscribe(self.listener, I3_IPC_EVENT_WORKSPACE)
        while self.i3ev.is_alive():
            pass

    def close(self, *args):
        self.i3ev.unsubscribe()
        self.dzen.kill()
