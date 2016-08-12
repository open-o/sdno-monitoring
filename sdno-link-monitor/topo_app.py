#!/usr/bin/python
# -*- coding: utf-8 -*-

__author__ = 'pzhang'

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options

from topo_handler import ms_topo_handler

class topo_app(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r'/', ms_topo_handler)
        ]
        tornado.web.Application.__init__(self, handlers)
        pass