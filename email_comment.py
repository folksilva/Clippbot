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
		item_key = re.search('comment\..*@',message.to).group()[8:][:-1]
		item = Item.get(item_key)
		if not item or not isinstance(item,Item):
			# O e-mail não é sobre um item conhecido
			logging.error(u"O e-mail de comentário recebido não é destinado a um item conhecido")
			return

		# Quem enviou a mensagem?
		sender_email = message.sender.strip()
		if "<" in sender_email and ">" in sender_email:
			sender_email = re.search('<.*@.*>',sender_email).group()[1:][:-1]
		sender = None

		# É um contato de uma categoria desse item?
		for c in item.categories:
			sender = c.category.contacts.filter("email =",sender_email).get()
			if sender:
				break
		# Se não é um contato, é um membro da equipe?
		if sender == None:
			for member in item.source_channel.team.members:
				if member.profile.email == sender_email:
					sender = member

		if sender == None:
			# Se não é conhecido ignore o e-mail
			logging.error(u"Quem enviou o e-mail de comentário para o item %s não é conhecido" % item.key().name())
			return
		
		plaintext_bodies = message.bodies('text/plain')
		observation = None
		for c,b in plaintext_bodies:
			# Trate o e-mail e extraia apenas o comentário
			comment = b.decode()
			exp = re.compile("(\n.*)(\n\n)(>.*)")
			match = exp.search(comment)
			if match:
				comment = comment[:match.start()]
			observation = ItemObservation(item=item,content=comment)
			if isinstance(sender,Contact):
				observation.contact = sender
			else:
				observation.member = sender
			observation.put()
			break

		logging.info(u"comentário adicionado ao item %s por %s" % (item.key().name(),sender_email))

def main():
	run_wsgi_app(webapp.WSGIApplication([EmailHandler.mapping()]))

if __name__ == "__main__":
	main()