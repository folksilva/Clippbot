#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from models import Channel
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from datetime import *

def main():
	""" Carrega todos os canais que devem ser atualizados entre a última atualização e agora e coloca na fila de atualização"""
	dlast = datetime.now() - timedelta(minutes=5)
	dnow = datetime.now()
	
	last_cron_sync_work = datetime(dlast.year,dlast.month,dlast.day,dlast.hour,dlast.minute,0)
	now = datetime(dnow.year,dnow.month,dnow.day,dnow.hour,dnow.minute,59)
	channels_to_sync = Channel.all()#keys_only=True).filter('next_sync > ',last_cron_sync_work).filter('next_sync <= ',now).order('next_sync')
	
	log = "%s channel(s) to sync between %s and %s" % (channels_to_sync.count(),last_cron_sync_work,now)
	logging.info(log)
	
	for channel in channels_to_sync:
		# Colocar a sincronização na fila de tarefas
		logging.info("%s: %s - %s" % (channel.title,channel.last_sync,channel.next_sync))
		if channel.next_sync > last_cron_sync_work and channel.next_sync <= now:
			taskqueue.add(queue_name='sync',params={'channel':channel.key()})

if __name__ == "__main__":
	main()