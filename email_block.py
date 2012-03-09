#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging, email, re

from models import *
from utils import *

from google.appengine.api.labs import taskqueue

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler

class EmailHandler(InboundMailHandler):
	def receive(self, message):
		# Esse e-mail é sobre qual item?
		contact_key = re.search('block\..*@',message.to).group()[8:][:-1]
		contact = Contact.get(contact_key)
		if not contact or not isinstance(contact,Contact):
			# O e-mail não é para um contato conhecido
			logging.error(u"O e-mail de bloqueio recebido não é destinado a nenhum contato conhecido")
			return

		# Quem enviou a mensagem?
		sender_email = message.sender.strip()
		if "<" in sender_email and ">" in sender_email:
			sender_email = re.search('<.*@.*>',sender_email).group()[1:][:-1]
		sender = None

		if not sender == contact.email:
			# Quem enviou a mensagem não foi o próprio contato
			logging.error(u"O e-mail de bloqueio recebido não foi enviado pelo próprio contato")
			return
		
		contact.send_automatic = False
		contact.put()

		plaintext_bodies = message.bodies('text/plain')
		observation = None
		for c,b in plaintext_bodies:
			# Trate o e-mail e extraia apenas o comentário
			comment = b.decode()
			exp = re.compile("(\n.*)(\n\n)(>.*)")
			match = exp.search(comment)
			if match:
				comment = comment[:match.start()]

			for name,email in getTeamAdminEmails(team):
				taskparams = {
					'to':'%s <%s>' % (name,email),
					'subject':'Contato bloqueado no Clippbot',
					'body':getTemplate('email_blocked_pure',{'contact':contact,'comment':comment,'name':name}),
					'html':getTemplate('email_blocked',{'contact':contact,'comment':comment,'name':name})
				}
				taskqueue.add(queue_name='mail',params=taskparams)
			break

def main():
	run_wsgi_app(webapp.WSGIApplication([EmailHandler.mapping()]))

if __name__ == "__main__":
	main()