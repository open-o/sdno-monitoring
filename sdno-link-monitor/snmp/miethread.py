#!/usr/bin/env python
# -*- coding: utf_8 -*-

import threading
import time
import traceback

from xlogger import *


class MieThread(threading.Thread):

    def __init__(self, name="MieThread"):
        threading.Thread.__init__(self, name=name)
        self.event = threading.Event()

        self.state_quiting = False
        self.state_pause = False

        self.loops = 0

        self.preloops = set()
        self.pstloops = set()

        self.prebyes = set()

    def pause(self):
        self.state_pause = True

    def resume(self):
        self.state_pause = False

    def bye(self):
        self._prebye()

        self.state_quiting = True
        self.state_pause = False
        self.wakeup()

    def wakeup(self):
        self.event.set()

    def act(self):
        '''Process and return naptime

        =0 : Not wait, direct next loop
        >0 : wait before next loop
        <0 : Quit
        '''

        return 10

    def set_prebye(self, fn):
        self.prebyes.add(fn)

    def _prebye(self):
        for fn in self.prebyes:
            fn()

    def set_enterloop(self, fn):
        self.preloops.add(fn)

    def _enterloop(self):
        for fn in self.preloops:
            fn()

    def set_exitloop(self, fn):
        self.pstloops.add(fn)

    def _exitloop(self):
        for fn in self.pstloops:
            fn()

    def run(self):
        self._enterloop()

        while not self.state_quiting:
            self.loops += 1

            if not self.state_pause:
                try:
                    waittime = float(self.act())
                except:
                    waittime = 600
                    klog.e(traceback.format_exc())
            else:
                waittime = 10 * 365 * 24 * 60 * 60

            if self.state_quiting:
                break

            if waittime > 0:
                self.event.wait(waittime)
                self.event.clear()
                continue

            if waittime < 0:
                klog.n("MieThread: act makes me quit")
                break

        self._exitloop()
