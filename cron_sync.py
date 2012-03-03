#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from models import Channel
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from datetime import timedelta, datetime

def main():
	""" Carrega todos os canais que devem ser atualizados entre a última atualização e agora e coloca na fila de atualização"""
	dlast = datetime.now() - timedelta(minutes=5)
	dnow = datetime.now()
	
	last_cron_sync_work = datetime(dlast.year,dlast.month,dlast.day,dlast.hour,dlast.minute,0)
	now = datetime(dnow.year,dnow.month,dnow.day,dnow.hour,dnow.minute,59)
	
	channels_to_sync = Channel.all(keys_only=True).filter('next_sync > ',last_cron_sync_work).filter('next_sync <= ',now).order('next_sync')
	
	logging.info("%s channel(s) to sync between %s and %s" % (channels_to_sync.count(),last_cron_sync_work,now))
	
	for channel in channels_to_sync:
		# Colocar a sincronização na fila de tarefas
		taskqueue.add(queue_name='sync',params={'channel':channel})

if __name__ == "__main__":
	main()