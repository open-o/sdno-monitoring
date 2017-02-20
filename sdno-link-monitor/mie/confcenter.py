#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2016-2017 China Telecommunication Co., Ltd.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import traceback
import re

from xlogger import klog
from bprint import cp


class FileMonitor():
    def __init__(self, files, on_file_reload):
        # Files to be inotified
        self.files = files
        self.on_file_reload = on_file_reload

        self._wm = None
        self._notifier = None
        self._watches = set()

        try:
            # XXX: in case of pyinotify not exits
            self._init_monitor()
        except:
            pass

        self.load()

    def load(self):
        try:
            self._unmonitor_files()
            self._monitor_files()
        except:
            pass

    def __del__(self):
        self._final_monitor()

    def _init_monitor(self):
        import pyinotify

        #
        # EventHandler if configure file changed
        #
        class EventHandler(pyinotify.ProcessEvent):
            def __init__(self, on_file_reload):
                super(EventHandler, self).__init__()
                self.on_file_reload = on_file_reload
            def process_default(self, event):
                self.on_file_reload()

        if not self._wm:
            self._wm = pyinotify.WatchManager()

        if not self._notifier:
            self._notifier = pyinotify.ThreadedNotifier(
                self._wm, EventHandler(self.on_file_reload))
            self._notifier.name = "ConfCenter.Notifier"
            self._notifier.start()

    def _final_monitor(self):
        if self._notifier:
            self._notifier.stop()
            self._notifier = None

        if self._wm:
            self._unmonitor_files()
            self._wm = None

    def _monitor_files(self):
        import pyinotify
        mask = pyinotify.IN_CLOSE_WRITE
        for f in self.files:
            if not f:
                continue
            try:
                wdd = self._wm.add_watch(f, mask, rec=False)
                for val in wdd.values():
                    self._watches.add(val)
            except:
                pass

    def _unmonitor_files(self):
        for wd in self._watches:
            self._wm.del_watch(wd)
        self._watches.clear()


class ConfCenter(object):
    def __init__(self, ro_cfgs=None, rw_cfg=None):

        # i:/opt/value = <get refered count>
        self._dict_conf_refs = {}

        # Loaded from cfg files
        # i:/opt/value = 3333
        self._dict_conf_value = {}

        # Not loaded from cfg file
        # i:/opt/value = defval
        self._dict_conf_defval = {}

        # Only Get no get or alias
        # Used only for dump situation
        self._dict_conf_missed = {}

        # OPT_VAL = i:/opt/value
        self._dict_alias_conf = {}

        self._ro_cfgs = ro_cfgs or []
        self._rw_cfg = rw_cfg

        # Called when configure source changed
        self._monitors = {}

        # inotify the configure files
        self._filemon = None

        # modified since it is loaded
        self._modified = set()

        # tmp or runtime conf, do not save to file
        self._tmp = set()

        self.load()

    def setconfref(self, key):
        key = str(key)
        self._dict_conf_refs[key] = self._dict_conf_refs.get(key, 0) + 1

    def get(self, key, defval):
        '''Get (by guess maybe) the configure for the key

        self.get("UPLOAD_MAX", 222)
        self.get("/upload/max", 222)
        self.get("i:/upload/max", 222)
        '''

        #
        # Check i:/xxx or s:/xxx
        #
        if key[:3] in ["i:/", "s:/"]:
            val = self.dicget(self._dict_conf_value, key)
            if val is not None:
                self.setconfref(key)
                return val

            val = self.dicget(self._dict_conf_defval, key)
            if val is not None:
                self.setconfref(key)
                return val

            self.dicset(self._dict_conf_missed, key, defval)
            return defval

        #
        # Check /xxx
        #
        if key[0] == '/':
            if isinstance(defval, int):
                return self.get("i:" + key, defval)
            else:
                return self.get("s:" + key, defval)

        #
        # This maybe a alias
        #
        newkey = self.dicget(self._dict_alias_conf, key)
        if newkey is not None:
            return self.get(newkey, defval)

        #
        # Check xxx/abc/xyz
        #
        if isinstance(defval, int):
            return self.get("i:/" + key, defval)
        else:
            return self.get("s:/" + key, defval)

        return defval

    def set(self, key, val, tmp=False, callchanged=True):
        # After set, the defval is not necessary
        prefix = key[:3]
        if prefix == "i:/":
            val = int(val)
        elif prefix == "s:/":
            val = val.rstrip("\r\n")
        else:
            return False

        self._modified.add(key)
        if tmp:
            self._tmp.add(key)

        self.dicdel(self._dict_conf_defval, key)
        self.dicdel(self._dict_conf_missed, key)

        self.dicset(self._dict_conf_value, key, val)

        if callchanged:
            self._conf_changed()

        return True

    #
    # XXX: All the settings which not from cfg file is converted to unicode
    #
    def dicset(self, dic, key, val):
        dic[str(key)] = val

    def dicget(self, dic, key, defval=None):
        return dic.get(str(key), defval)

    def dicdel(self, dic, key):
        try:
            key = str(key)
            if key in dic:
                del dic[key]
        except:
            pass

    def dichas(self, dic, key):
        return str(key) in dic

    #
    # xxx
    #
    def foreach(self, func):
        # _dict_conf_value
        for key, val in self._dict_conf_value.items():
            func(key, val)

        for key, val in self._dict_conf_defval.items():
            func(key, val)

    def dump(self, showtype=None, pat=None):
        if not pat or pat == "*":
            pat = ".*"
        else:
            pat = "." + str(pat) + ".*"
        pat = re.compile(pat)

        def match_type(key):
            if not showtype:
                return True

            if showtype[0] == 'u':
                # used
                return self.dichas(self._dict_conf_refs, key)

            if showtype[0] == 'n':
                # not used
                return not self.dichas(self._dict_conf_refs, key)

            if showtype[0] == 't':
                # those who return default value
                return self.dichas(self._dict_conf_missed, key)

            return True

        l = []

        # _dict_conf_value
        for key, val in self._dict_conf_value.items():
            res = pat.search(key)
            if res and match_type(key):
                l.append("%s=%s\n" % (key, str(val)))

        # _dict_conf_defval
        for key, val in self._dict_conf_defval.items():
            res = pat.search(key)
            if res and match_type(key):
                l.append("%s=%s\n" % (key, str(val)))

        # _dict_conf_missed
        for key, val in self._dict_conf_missed.items():
            res = pat.search(key)
            if res and match_type(key):
                l.append("%s=%s\n" % (key, str(val)))

        l.sort(lambda a, b: cmp(a[2:], b[2:]))

        newlist = []
        oldgroup = ""
        for tmp in l:
            try:
                groups = tmp.split("/")
                if not groups:
                    continue
                group = groups[2]
                if oldgroup != group:
                    newlist.append("")
                    oldgroup = group
            except:
                pass
            newlist.append(tmp.strip())

        l.sort(lambda a, b: cmp(a[2:], b[2:]))

        return newlist

    def has(self, key):
        if not self.dichas(self._dict_conf_value, key):
            key = self.dicget(self._dict_alias_conf, key)
            if key is not None:
                return self.has(key)
        return True

    def setmonitor(self, monitor, cookie=None):
        self._monitors[monitor] = cookie

        if not self._filemon:
            files = self._ro_cfgs + [self._rw_cfg]
            self._filemon = FileMonitor(files, self._file_reload)

    def loadfile(self, path):
        ln = 0
        with open(path, "r") as f:
            for line in f.readlines():
                ln += 1
                l = line.lstrip()

                if not l or l[0] == '#':
                    continue

                if l[0] == '%':
                    self.loadfile(l[1:])
                    continue

                equalpos = l.find("=")
                if equalpos < 0:
                    continue

                key = l[:equalpos]
                if len(key) < 4:
                    continue

                val = l[equalpos + 1:]

                try:
                    if not self.set(key, val, callchanged=False):
                        klog.e("BADCONF: %s:%d: '%s'" % (path, ln, line))
                except:
                    traceback.print_exc()
                    klog.e("BADCONF: %s:%d: '%s'" % (path, ln, line))

        self._conf_changed()

    def load(self):
        self._dict_conf_value = {}

        for cfg in self._ro_cfgs + [self._rw_cfg]:
            if cfg:
                try:
                    self.loadfile(cfg)
                except:
                    pass

        self._modified.clear()

    def _conf_changed(self):
        for monitor, cookie in self._monitors.items():
            monitor(cookie)

    def _file_reload(self):
        self.load()
        self._filemon.load()

    def save(self, full=False):
        if not self._rw_cfg:
            klog.w("Not rw_cfg set")
            return False

        if full:
            #
            # save ALL conf to file
            #
            self._modified |= set(self._dict_conf_value.keys())
            self._modified |= set(self._dict_conf_defval.keys())

        #
        # Do save
        #
        done = set()
        lines = []
        with open(self._rw_cfg, "r") as f:
            lines = f.readlines()

        # If some line changed, replace that line
        for i in range(len(lines)):
            segs = lines[i].strip().split("=", 1)
            if len(segs) < 2 or segs[0] == '#':
                continue
            key = segs[0]
            if key not in self._tmp and key in self._modified:
                val = self.dicget(self._dict_conf_value, key)
                lines[i] = "%s=%s\n" % (key, val)
                # OK, this conf is finish, make sure it don't been added again
                done.add(key)

        # Some configure is not from cfg file, so append them
        for key, val in self._dict_conf_value.items():
            if key not in self._tmp and key in self._modified and key not in done:
                val = self.dicget(self._dict_conf_value, key)
                lines.append("%s=%s\n" % (key, val))
                done.add(key)

        # Some configure is not from cfg file, so append them
        for key, val in self._dict_conf_defval.items():
            if key not in self._tmp and key in self._modified and key not in done:
                val = self.dicget(self._dict_conf_defval, key)
                lines.append("%s=%s\n" % (key, val))
                done.add(key)

        self._modified.clear()

        with open(self._rw_cfg, "w") as f:
            f.writelines(lines)

        return True

    def __getitem__(self, key):
        if self.has(key):
            return self.get(key, None)
        print(cp.r("CC.ERROR(1):"), " '%s' not found" % (key))
        raise AttributeError

    def __getattr__(self, key):
        if self.has(key):
            return self.get(key, None)
        print(cp.r("CC.ERROR(2):"), " '%s' not found" % (key))
        raise AttributeError

    def rem(self, key):
        try:
            key = str(key)

            self.dicdel(self._dict_conf_value, key)
            self.dicdel(self._dict_conf_defval, key)
            self.dicdel(self._dict_alias_conf, key)
            self.dicdel(self._dict_conf_missed, key)

            try:
                self._modified.remove(key)
            except:
                pass

            return True
        except:
            traceback.print_exc()
            return False

    def alias_add(self, alias, key, defval):
        prefix = key[:3]
        if prefix not in ["i:/", "s:/"]:
            return

        try:
            self.dicset(self._dict_alias_conf, alias, key)

            if prefix == "i:/":
                defval = int(defval)
            if prefix == "s:/":
                defval = str(defval)

            if not self.dichas(self._dict_conf_value, key):
                # If set alias to a non-conf entry, warn the caller
                self.dicset(self._dict_conf_defval, key, defval)
        except:
            pass

    def alias_del(self, alias):
        prefix = alias[:3]
        if prefix not in ["i:/", "s:/"]:
            return

        key = self.dicget(self._dict_alias_conf, alias)
        if key is not None:
            self.dicdel(self._dict_conf_defval, key)
        self.dicdel(self._dict_alias_conf, alias)


class XConfCenter(object):
    def __init__(self, group, ro_cfgs=None, rw_cfg=None, conf=None, alias=None):

        if not conf:
            self.conf = ConfCenter(ro_cfgs, rw_cfg)
        else:
            if isinstance(conf, ConfCenter):
                self.conf = conf
            elif isinstance(conf, XConfCenter):
                self.conf = conf.conf
            else:
                raise AttributeError

        self.group = group

        # alias process
        for a in alias or []:
            self.alias(*a)
        self.alias_init()

    def alias_init(self):
        # Stub
        pass

    def cd(self, path):
        '''Adjust the group /xxx/bbb/222'''
        pass

    def xget(self, subpath, defval):
        if isinstance(defval, int):
            key = "i:/%s/%s" % (self.group, subpath)
        else:
            key = "s:/%s/%s" % (self.group, subpath)

        return self.conf.get(key, defval)

    def alias(self, nickname, subpath, defval):
        if isinstance(defval, int):
            key = "i:/%s/%s" % (self.group, subpath)
        else:
            key = "s:/%s/%s" % (self.group, subpath)
        self.conf.alias_add(nickname, key, defval)

    #
    # Take over cc's interface
    #
    def foreach(self, func):
        return self.conf.foreach(func)

    def dump(self, showtype=None, pat=None):
        return self.conf.dump(showtype, pat)

    def has(self, conf):
        return self.conf.has(conf)

    def setmonitor(self, monitor, cookie=None):
        return self.conf.setmonitor(monitor, cookie)

    def loadfile(self, path):
        return self.conf.loadfile(path)

    def load(self):
        return self.conf.load()

    def save(self, full=False):
        return self.conf.save(full)

    def __getitem__(self, key):
        return self.conf.__getitem__(key)

    def __getattr__(self, key):
        return self.conf.__getattr__(key)

    def get(self, conf, defval):
        return self.conf.get(conf, defval)

    def set(self, conf, val, tmp=False):
        return self.conf.set(conf, val, tmp)

    def rem(self, conf):
        return self.conf.rem(conf)

    def alias_add(self, alias, path, defval):
        return self.conf.alias_add(alias, path, defval)

    def alias_del(self, alias):
        return self.conf.alias_del(alias)
