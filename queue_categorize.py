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
		self.response.out.write('<h1>Clippbot</h1>Este é um trabalho de plano de fundo! Nada a fazer.<br>This is a background work! Nothing to do.')

	def post(self):
		""" Algoritmo de auto categorização do item """
		# Obter dados essenciais para o algoritmo
		key = self.request.get('item')
		t_key = self.request.get('team')
		item = Item.get(key)
		team = Team.get_by_key_name(t_key)
		if not item or not team:
			logging.error("A categorização não recebeu dados")
			return
		title_terms = unify(remove_stopwords(item.title.lower()).split())
		description_terms = unify(remove_stopwords(item.description.lower()).split())
		if len(title_terms) < 3 or len(description_terms) < 3:
			# Notificar a equipe que este item não possui dados suficientes para trabalhar
			logging.warning("O item %s não possui dados suficientes para analisar" % key)
			for name, email in getTeamEmails(team):
				taskparams = {
					'sender': 'category.%s' % key,
					'to':'%s <%s>' % (name,email),
					'subject':u'O item não pode ser classificado',
					'body':getTemplate('bad_item_pure',{'item':item}),
					'html':getTemplate('bad_item',{'item':item})
				}
				taskqueue.add(queue_name='mail',params=taskparams)
			return
		if team.categories.count(1) == 0:
			# Notificar a equipe que não possui categorias cadastradas
			logging.warning("A equipe não possui categorias cadastradas. Impossível analizar o item %s" % key)
			for name, email in getTeamEmails(team):
				taskparams = {
					'to':'%s <%s>' % (name,email),
					'subject':u'O item não pode ser classificado',
					'body':getTemplate('no_team_pure',{'item':item}),
					'html':getTemplate('no_team',{'item':item})
				}
				taskqueue.add(queue_name='mail',params=taskparams)
			return

		# Variaveis do algoritmo
		space = {} # Conjunto de corpus

		# Construir os corpus 
		for category in team.categories:
			if category.items.count(11) < 10:
				logging.info("A categoria %s foi ignorada por não conter dados suficientes para análise do item %s" % (category.name,key))
				continue

			titles = ""
			descriptions = ""
			space[category.key().name()] = {}
			space[category.key().name()]['title'] = []
			space[category.key().name()]['description'] = []
			for item_c in category.items:
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
		avg_score = total_score / len(scores)
		# Categorias com maior probabilidade de estar correto
		auto_categories = [category for category in scores if scores[category] >= (avg_score + (avg_score/len(scores)))]
		# Categorias com mais de 50% (e menos de 75%) de probabilidade de estar correto
		suggestion_categories = [category for category in scores if scores[category] > avg_score and scores[category] < (avg_score + (avg_score/2))]

		if len(auto_categories) == 0 and len(suggestion_categories) == 0:
			# Notificar a equipe que esse item não se enquadra em nenhuma categoria
			logging.warning("O item %s não se enquadra em nenhuma categoria" % key)
			for name, email in getTeamEmails(team):
				taskparams = {
					'sender': 'category.%s' % key,
					'to':'%s <%s>' % (name,email),
					'subject':u'O item não pode ser classificado',
					'body':getTemplate('lost_item_pure',{'item':item}),
					'html':getTemplate('lost_item',{'item':item})
				}
				taskqueue.add(queue_name='mail',params=taskparams)
			return

		if len(auto_categories) > 0:
			# Enfileirar os e-mails para os contatos da categoria definida automaticamente
			item.classified = True
			item.put()
			logging.info(item)
			for category in auto_categories:
				c = Category.get_by_key_name(category)
				ic = ItemInCategory(item=item,category=c,is_suggestion=False)
				ic.put()
				for contact in c.contacts.filter("send_automatic =",True):
					taskparams = {
						'sender': 'comment.%s' % key,
						'to':"%s <%s>" % (contact.name,contact.email),
						'subject':u'Nova notícia: %s' % item.title,
						'body':getTemplate('new_item_pure',{'item':item}),
						'html':getTemplate('new_item',{'item':item})
					}
					taskqueue.add(queue_name='mail',params=taskparams)

		if len(suggestion_categories) > 0:
			# Notificar a equipe sobre as sugestões de categorias e solicitar confirmação
			suggestions = []
			for category in suggestion_categories:
				c = Category.get_by_key_name(category)
				suggestions.append(c)
				ic = ItemInCategory(item=item,category=c,is_suggestion=True)
				ic.put()
			for name, email in getTeamEmails(team):
				taskparams = {
					'sender': 'suggestion.%s' % key,
					'to':'%s <%s>' % (name,email),
					'subject':u'O item possui sugestões de classificação',
					'body':getTemplate('suggestion_pure',{'item':item,'suggestions':suggestions}),
					'html':getTemplate('suggestion',{'item':item,'suggestions':suggestions})
				}
				taskqueue.add(queue_name='mail',params=taskparams)

def main():
	run_wsgi_app(webapp.WSGIApplication([
		('/_ah/queue/categorize',CategorizeWorker),
	]))

if __name__ == "__main__":
	main()