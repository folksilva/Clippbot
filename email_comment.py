#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging, email

from models import *

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

class EmailHandler(InboundMailHandler):
	def receive(self, message):
		logging.info("Received a message from: " + message.sender)

def main():
	run_wsgi_app(webapp.WSGIApplication([LogSenderHandler.mapping()],debug=True))

if __name__ == "__main__":
	main()