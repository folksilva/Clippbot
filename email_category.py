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
		item_key = message.to[9:][:-25]
		item = Item.get(item_key)
		logging.info(item.title)
		if not item or not isinstance(item,Item):
			# O e-mail não é sobre um item conhecido
			logging.error(u"O e-mail de categoria recebido não é destinado a um item conhecido")
			return

		# Quem enviou a mensagem?
		sender_email = message.sender
		sender = None

		# É um contato de uma categoria desse item?
		for c in item.categories:
			sender = c.category.contacts.filter("email =",sender_email).get()
			if sender:
				break
		# Se não é um contato, é um membro da equipe?
		for member in item.categories.get().category.team.members:
			if member.profile.email == sender_email:
				sender = member

		if sender == None:
			# Se não é conhecido ignore o e-mail
			logging.error(u"Quem enviou o e-mail de categoria para o item %s não é conhecido" % item.key().name())
			return
		
		plaintext_bodies = message.bodies('text/plain')
		for c,b in plaintext_bodies:
			# Trate o e-mail e extraia apenas a(s) categoria(s)
			text = b.decode()
			exp = re.compile("\A.*")
			categories_keys = exp.search(text).group(0).lower().split(',')
			categories = []
			for c in categories_keys:
				c = c.strip()
				c_key = "_".join(c.split())
				category = Category.get_by_key_name(c_key)
				if not category or not category.team.key() == item.source_channel.team.key():
					# A categoria não existe
					logging.error(u"A categoria %s não existe nesta equipe" % c)
					continue
				ic = item.categories.filter('category =',category).get()
				if not ic:
					ic = ItemInCategory(item=item,category=category,is_suggestion=False)
				elif ic.is_suggestion:
					ic.is_suggestion = False
				else:
					continue
				ic.put()
				logging.info(u"categoria %s adicionada ao item %s por %s" % (category.name,item.key().name(),sender_email))
				for contact in category.contacts.filter("send_automatic =",True):
					taskparams = {
						'sender': 'comment.%s' % item.key(),
						'to':"%s <%s>" % (contact.name,contact.email),
						'subject':u'Nova notícia: %s' % item.title,
						'body':getTemplate('new_item_pure',{'item':item}),
						'html':getTemplate('new_item',{'item':item})
					}
					taskqueue.add(queue_name='mail',params=taskparams)
			break

def main():
	run_wsgi_app(webapp.WSGIApplication([EmailHandler.mapping()],debug=True))

if __name__ == "__main__":
	main()