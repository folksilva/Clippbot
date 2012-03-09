#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
from models import *
def main():
	""" Carrega todos os canais que devem ser atualizados entre a última atualização e agora e coloca na fila de atualização e envia os e-mails pendentes"""
	for c in Channel.all():
		logging.warning("Channel %s reseted" % c.key())
		c.last_sync = None;
		c.put()
	
if __name__ == "__main__":
	main()