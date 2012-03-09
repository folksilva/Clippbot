#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from models import *

from google.appengine.api import mail
from google.appengine.api.labs import taskqueue

from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MailWorker(webapp.RequestHandler):
	def get(self):
		self.response.out.write(u'<h1>Clippbot</h1>Este é um trabalho de plano de fundo! Nada a fazer.<br>This is a background work! Nothing to do.<form method="post">TO:<input name="to">SUB:<input name="subject">BOD:<input name="body"><input type="submit"></form>')

	def post(self):

		email = mail.EmailMessage()
		to = self.request.get('to')
		if to:
			email.to=to
		cc = self.request.get('cc')
		if cc:
			email.cc=cc
		bcc = self.request.get('bcc')
		if bcc:
			email.bcc=bcc
		reply_to = self.request.get('reply_to')
		if reply_to:
			email.reply_to=reply_to
		subject = self.request.get('subject')
		if subject:
			email.subject=subject
		body = self.request.get('body')
		if body:
			email.body=body
		html = self.request.get('html')
		if html:
			email.html=html
		sender = self.request.get('sender')
		if not sender:
			sender = "no-reply"
		email.sender="Clippbot <%s@clippbot.appspotmail.com>" % sender
		try:
			email.send()
			logging.info("Email enviado para %s com o assunto %s" % (to,subject))
		except mail.InvalidEmailError:
			logging.error(u"A mensagem não pode ser enviada por que um ou mais e-mails destinatários são inválidos")
		except mail.MissingRecipientsError:
			logging.error(u"A mensagem não pode ser enviada por que nenhum destinatário foi informado")
		except mail.MissingSubjectError:
			logging.error(u"A mensagem não pode ser enviada por que não possui assunto")
		except mail.MissingBodyError:
			logging.error(u"A mensagem não pode ser enviada por que não possui um corpo")
		except:
			logging.error(u"A mensagem não pode ser enviada")

def main():
	run_wsgi_app(webapp.WSGIApplication([
		('/_ah/queue/mail',MailWorker),
	]))

if __name__ == "__main__":
	main()