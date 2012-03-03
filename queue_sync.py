#!/usr/bin/env python
# -*- coding: utf-8 -*-

import feedparser

from models import *
from datetime import datetime
from dateutil import parser

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class SyncWorker(webapp.RequestHandler):
	def get(self):
		self.response.out.write('<h1>Clippbot</h1>Este é um trabalho de plano de fundo! Nada a fazer.<br>This is a background work! Nothing to do.')

	def post(self):
		key = self.request.get('channel')
		channel = Channel.get(key)
		# Capturar as notícias do canal
		d = feedparser.parse(feed)
			if not d.bozo == 1 and len(d.entries) > 0:
				for entry in d.entries:
					# Verificar se já foi armazenado
					item = channel.items.filter('date =',parser.parse(entry.get('date'))).filter('title =',entry.get('title')).get()
					if not item:
						# Criar o novo item
						item_title = entry.get('title')
						item_link = entry.get('link')
						item_description = entry.get('description')
						item_author = entry.get('author','Sem autor')
						item_date = parser.parse(entry.get('date'))
						item_enclosure = entry.enclosures[0].get('href') if len(entry.enclosures) > 0 else None
						key_name = "_".join(item_title.lower().split()[:6]) + "_" + item_date.strftime("%Y%m%d%H%M")
						item = Item(key_name=key_name,
							title=item_title,
							link=item_link,
							description=item_description,
							author=item_author,
							date=item_date,
							enclosure=item_enclosure,
							source_channel=channel)
						try:
							item.put()
							# Colocar a categorização automatica na fila
							taskqueue.add(queue_name='categorize',params={'item':item.key(),'team':channel.team.key().name()})
						except:
							logging.error("O item não pode ser salvo")

		# Marcar a última atualização do canal
		channel.last_sync = datetime.now()
		channel.put()

def main():
	run_wsgi_app(webapp.WSGIApplication([
		('/_ah/queue/sync',SyncWorker),
	]))

if __name__ == "__main__":
	main()