#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from models import *
from utils import *
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from datetime import *
from google.appengine.api import mail

def sendmail(params):
	email = mail.EmailMessage()
	to = params.get('to')
	if to:
		email.to=to
	cc = params.get('cc')
	if cc:
		email.cc=cc
	bcc = params.get('bcc')
	if bcc:
		email.bcc=bcc
	reply_to = params.get('reply_to')
	if reply_to:
		email.reply_to=reply_to
	subject = params.get('subject')
	if subject:
		email.subject=subject
	body = params.get('body')
	if body:
		email.body=body
	html = params.get('html')
	if html:
		email.html=html
	sender = params.get('sender')
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
	""" Carrega todos os canais que devem ser atualizados entre a última atualização e agora e coloca na fila de atualização e envia os e-mails pendentes"""
	
	classified = {}
	failed = {}
	suggestions = {}
	# Itens que falharam
	all_items = Item.all().filter("is_new =",True).filter("failure !=",None)
	for item in all_items:
		if not item.team.key() in failed:
			failed[item.team.key()] = []
		failed[item.team.key()].append(item)
		item.is_new = False
		item.put()

	all_items_in_category = ItemInCategory.all().filter("is_new =", True)
	for ic in all_items_in_category:
		if not ic.is_suggestion:
			if not ic.category.key() in classified:
				classified[ic.category.key()] = []
			classified[ic.category.key()].append(ic.item)
		else:
			if not ic.item.team.key() in suggestions:
				suggestions[ic.item.team.key()] = []
			suggestions[ic.item.team.key()].append(ic.item)
		ic.is_new = False
		ic.put()

	# E-mails para a equipe
	if len(failed) > 0:
		for t in failed:
			team = Team.get(t)
			logging.info(u"%s itens com falhas para enviar para a equipe %s" % (len(failed[t]),t))
			for name, email in getTeamEmails(team):
				# Items que falharam
				emailparams = {
					'to':'%s <%s>' % (name,email),
					'subject':u'Itens que não foram classificados',
					'body':getTemplate('email_failed_pure',{'items':failed[t],'name':name}),
					'html':getTemplate('email_failed',{'items':failed[t],'name':name})
				}
				sendmail(emailparams)
	else:
		logging.info(u"Nenhum item com falhas para enviar")
	
	if len(suggestions) > 0:
		for t in suggestions:
			team = Team.get(t)
			logging.info(u"%s itens com sugestões para enviar para a equipe %s" % (len(suggestions[t]),t))
			for name, email in getTeamEmails(team):
				# Items com sugestão
				if len(suggestions[t]) > 0:
					emailparams = {
						'to':'%s <%s>' % (name,email),
						'subject':u'Itens com sugestões do Clippbot',
						'body':getTemplate('email_suggestion_pure',{'items':suggestions[t],'name':name}),
						'html':getTemplate('email_suggestion',{'items':suggestions[t],'name':name})
					}
					sendmail(emailparams)
	else:
		logging.info(u"Nenhum item com sugestões para enviar")

	# E-mails para os contatos
	if len(classified) > 0:
		for c in classified:
			category = Category.get(c)
			logging.info(u"%s itens classificados para enviar para os contatos da categoria %s" % (len(classified[c]),c))
			for contact in category.contacts.filter("send_automatic =",True):
				emailparams = {
					'to':"%s <%s>" % (contact.name,contact.email),
					'subject':u'[%s] Novas notícias no Clippbot' % category.name,
					'body':getTemplate('email_news_pure',{'items':classified[c],'contact':contact,'category':category}),
					'html':getTemplate('email_news',{'items':classified[c],'contact':contact,'category':category})
				}
				sendmail(emailparams)
	else:
		logging.info(u"Nenhum item classificado para enviar")

	dlast = datetime.now() - timedelta(minutes=5)
	dnow = datetime.now()
	
	last_cron_sync_work = datetime(dlast.year,dlast.month,dlast.day,dlast.hour,dlast.minute,0)
	now = datetime(dnow.year,dnow.month,dnow.day,dnow.hour,dnow.minute,59)
	channels_to_sync = 0
	for channel in Channel.all():
		if channel.next_sync() > last_cron_sync_work and channel.next_sync() <= now:
			taskqueue.add(queue_name='sync',params={'channel':channel.key()})
			channels_to_sync += 1
	
	log = "%s channel(s) to sync between %s and %s" % (channels_to_sync,last_cron_sync_work,now)
	logging.info(log)		

if __name__ == "__main__":
	main()