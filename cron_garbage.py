#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from models import Item
from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from datetime import *

def main():
	"""Varrer os itens antigos e excluí-los"""
	last_month = datetime.now() - timedelta(days=30)
	last_six_months = datetime.now() - timedelta(days=180)
	# Remover itens não classificados com mais de um mês
	remove_list = Item.all().filter("classified =",False).filter("date <",last_month)
	for remove in remove_list:
		logging.info("O item %s foi removido" % remove.key().name())
		remove.delete()
	# Arquivar itens classificados com mais de seis meses
	archive_list = Item.all().filter("classified =",True).filter("date <",last_six_months)
	for archive in archive_list:
		logging.info("O item %s foi arquivado" % archive.key().name())
		archive.is_archived = True
		archive.put()

if __name__ == "__main__":
	main()