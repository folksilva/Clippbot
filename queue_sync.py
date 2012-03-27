#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Importações padrões do python
import os
# Must set this env var *before* importing any part of Django.
os.environ['DJANGO_SETTINGS_MODULE'] = 'settings'

# Make sure we can import Django.  We may end up needing to do this
# little dance, courtesy of Google third-party versioning hacks.  Note
# that this patches up sys.modules, so all other code can just use
# "from django import forms" etc.
from google.appengine.dist import use_library
use_library('django','1.2')

import feedparser, re, sys, traceback

from utils import *
from models import *
from datetime import datetime, timedelta
from dateutil import parser

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class SyncWorker(webapp.RequestHandler):
	def get(self):
		self.response.out.write(u'<h1>Clippbot</h1>Este é um trabalho de plano de fundo! Nada a fazer.<br>This is a background work! Nothing to do.')

	def post(self):
		key = self.request.get('channel')
		channel = Channel.get(key)
		# Capturar as notícias do canal
		d = feedparser.parse(channel.feed)
		if not d.bozo == 1 and len(d.entries) > 0:
			channel.updated = parser.parse(d.feed.get("updated",datetime.now().__str__()))
			item_count = 0
			for entry in d.entries:
				# Verificar se já foi armazenado
				# item = channel.items.filter('date =',parser.parse(entry.get('date',entry.get('pub_date',"01-01-1900 00:00")))).filter('title =',entry.get('title')).get()
				item = Item.all(keys_only=True).filter('source_channel =',channel).filter('date =',parser.parse(entry.get('date',entry.get('pub_date',"01-01-1900 00:00")))).filter('title =',entry.get('title')).get()
				if not item:
					try:
						# Criar o novo item
						item_title = re.sub('\n','',entry.get('title'))
						item_link = re.sub('\n','',entry.get('link'))
						item_description = remove_html_tags(remove_extra_spaces(remove_html_tags(entry.get('description'))))
						item_author = entry.get('author','Sem autor')
						item_date = parser.parse(entry.get('date',entry.get('pub_date',"01-01-1900 00:00")))
						item_enclosure = entry.enclosures[0].get('href') if len(entry.enclosures) > 0 else None
						key_name = "_".join(remove_acents(item_title).lower().split()[:6]) + "_" + item_date.strftime("%Y%m%d%H%M")
						item = Item(key_name=key_name,
							title=item_title,
							link=item_link,
							description=item_description,
							author=item_author,
							date=item_date,
							enclosure=item_enclosure,
							team=channel.team,
							source_channel=channel)
						item.put()
						item_count += 1;
						# Colocar a categorização automatica na fila
						taskqueue.add(queue_name='categorize',params={'item':item.key(),'team':channel.team.key().name()})
					except:
						exc_type, exc_value, exc_traceback = sys.exc_info()
						logging.error(u"O item não pode ser salvo (%s): \n%s" % (exc_value,traceback.print_exception(exc_type,exc_value,exc_traceback,limit=2,file=sys.stdout)))

		if item_count > 0:
			logging.info('%s items added to channel %s (%s)' % (item_count,channel.title,channel.key()))
		else:
			logging.info('No new items to channel %s (%s)' % (channel.title,channel.key()))
		# Marcar a última atualização do canal
		channel.last_sync = datetime.now()
		channel.put()

def main():
	run_wsgi_app(webapp.WSGIApplication([
		('/_ah/queue/sync',SyncWorker),
	]))

if __name__ == "__main__":
	main()