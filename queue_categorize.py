#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import logging

from math import log

from models import *

from utils import *

from google.appengine.api.labs import taskqueue
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class CategorizeWorker(webapp.RequestHandler):

	def tf(self,term,doc,normalize=True):
		doc = doc.lower().split()
		if len(doc) > 0:
			if normalize:
				return doc.count(term.lower()) / float(len(doc))
			else:
				return doc.count(term.lower()) / 1.0

	def idf(self,term, corpus):
		num_texts_with_terms = len([True for text in corpus if term.lower() in text.lower().split()])
		try:
			return 1.0 + log(float(len(corpus)) / num_texts_with_terms)
		except ZeroDivisionError:
			return 1.0

	def tf_idf(self,term,doc,corpus):
		return self.tf(term,doc) * self.idf(term, corpus)

	# Funções do webapp

	def get(self):
		self.response.out.write(u'<h1>Clippbot</h1>Este é um trabalho de plano de fundo! Nada a fazer.<br>This is a background work! Nothing to do.')

	def post(self):
		""" Algoritmo de auto categorização do item """
		# Obter dados essenciais para o algoritmo
		key = self.request.get('item')
		t_key = self.request.get('team')
		item = Item.get(key)
		team = Team.get_by_key_name(t_key)
		if not item or not team:
			logging.error(u"A categorização não recebeu dados")
			return
		title_terms = unify(remove_stopwords(item.title.lower()).split())
		description_terms = unify(remove_stopwords(item.description.lower()).split())
		if len(title_terms) < 3 or len(description_terms) < 3:
			# Notificar a equipe que este item não possui dados suficientes para trabalhar
			logging.warning(u"O item %s não possui dados suficientes para analisar" % key)
			item.failure = u"O item não possui dados suficientes para analisar"
			item.put()
			return
		if team.categories.count(1) == 0:
			# Notificar a equipe que não possui categorias cadastradas
			logging.warning(u"A equipe não possui categorias cadastradas. Impossível analizar o item %s" % key)
			item.failure = u"A equipe não possui categorias cadastradas"
			item.put()
			return

		# Variaveis do algoritmo
		space = {} # Conjunto de corpus

		# Construir os corpus 
		for category in team.categories:
			if category.items.count(11) < 10:
				logging.info(u"A categoria %s foi ignorada por não conter dados suficientes para análise do item %s" % (category.name,key))
				continue

			space[category.key().name()] = {}
			space[category.key().name()]['title'] = []
			space[category.key().name()]['description'] = []
			for item_c in category.items.order('-date').fetch(25):
				space[category.key().name()]['title'].append(remove_stopwords(item_c.item.title))
				space[category.key().name()]['description'].append(remove_stopwords(item_c.item.description))
		
		# Calcular o TF-IDF do item atual
		scores = {}
		for category in space:
			scores[category] = 0
			corpus = space[category]
			
			# Pontuação dos títulos
			for title_term in title_terms:
				for doc in sorted(corpus['title']):
					scores[category] += self.tf_idf(title_term,doc,corpus['title'])*2

			# Pontuação das descrições
			for description_term in description_terms:
				for doc in sorted(corpus['description']):
					scores[category] += self.tf_idf(description_term,doc,corpus['description'])

		logging.info(scores)
		# Analisar os dados obtidos
		total_score = sum([scores[k] for k in scores])
		auto_categories = []
		suggestion_categories = []
		if len(scores) > 0 and total_score > 0:
			avg_score = total_score / len(scores)
			# Categorias com maior probabilidade de estar correto
			auto_categories = [category for category in scores if scores[category] >= (avg_score + (avg_score/len(scores)))]
			# Categorias com mais de 50% (e menos de 75%) de probabilidade de estar correto
			suggestion_categories = [category for category in scores if scores[category] > avg_score and scores[category] < (avg_score + (avg_score/2))]

		if len(auto_categories) == 0 and len(suggestion_categories) == 0:
			# Notificar a equipe que esse item não se enquadra em nenhuma categoria
			logging.info(u"O item %s não se enquadra em nenhuma categoria" % key)
			item.failure = u"O item não se enquadra em nenhuma categoria"
			item.put()
			return

		if len(auto_categories) > 0:
			# Enfileirar os e-mails para os contatos da categoria definida automaticamente
			item.classified = True
			item.put()
			for category in auto_categories:
				c = Category.get_by_key_name(category,parent=team)
				ic = ItemInCategory(item=item,category=c,is_suggestion=False)
				ic.put()

		if len(suggestion_categories) > 0:
			# Notificar a equipe sobre as sugestões de categorias e solicitar confirmação
			#suggestions = []
			for category in suggestion_categories:
				c = Category.get_by_key_name(category,parent=team)
				#suggestions.append(c)
				ic = ItemInCategory(item=item,category=c,is_suggestion=True)
				ic.put()

def main():
	run_wsgi_app(webapp.WSGIApplication([
		('/_ah/queue/categorize',CategorizeWorker),
	]))

if __name__ == "__main__":
	main()