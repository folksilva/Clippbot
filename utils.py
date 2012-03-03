#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, os

from django.forms.util import ErrorList
from stopwords import stopwords as sw

from google.appengine.ext.webapp import template

def unify(seq, idfun=None):
	if idfun is None:
		def ifun(x): return x
	seen = {}
	result = []
	for item in seq:
		marker = idfun(item)
		if marker in seen: continue
		seen[marker] = 1
		result.append(item)
	return result

def remove_stopwords(text):
	# Lista de palavras a serem consideradas stopwords
	stopwords = sw + [',','.',';','"','\'','!','?','\\','/','{','}','[',']','(',')','<','>','*','%','$','#','@']
	regxp_str = '('
	for word in stopwords:
		regxp_str += ('|' if not regxp_str == '(' else '')
		regxp_str += word
	regxp_str = regxp_str + ')'
	regxp_str = '( %s |^%s | %s$)' % (regxp_str,regxp_str,regxp_str)
	regxp = re.compile(regxp_str, re.IGNORECASE)
	text = regxp.sub(' ',text)
	return text.strip()

def getTemplate(template_file,data={}):
	if not template_file.endswith('.html'):
		template_file += '.html'
		path = os.path.join(os.path.dirname(__file__),'templates','email',template_file)
		return template.render(path,data)

def getTeamEmails(team):
	emails = []
	for member in team.members.filter('can_be_notified =',True):
		emails[member.profile.name] = member.profile.email
	return emails

class DivErrorList(ErrorList):
	def __unicode__(self):
		return self.as_divs()
	def as_divs(self):
		if not self: return u''
		return u'<div class="errorlist">%s</div>' % ''.join([u'<div class="error">%s</div>' % e for e in self])

