#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re, os, logging

from stopwords import stopwords as sw

from google.appengine.ext.webapp import template

def unify(seq, idfun=None):
	if idfun is None:
		def idfun(x): return x
	seen = {}
	result = []
	for item in seq:
		marker = idfun(item)
		if marker in seen: continue
		seen[marker] = 1
		result.append(item)
	return result

def remove_html_tags(text):
    p = re.compile(r'<.*?>')
    return p.sub('', text)

def remove_extra_spaces(text):
    p = re.compile(r'\s+')
    return p.sub(' ', text)

def remove_acents(text):
	text = re.sub('[áàãâä]','a',text)
	text = re.sub('[ÁÀÃÂÄ]','A',text)
	text = re.sub('[éèẽêë]','e',text)
	text = re.sub('[ÉÈẼÊË]','E',text)
	text = re.sub('[íìĩîï]','i',text)
	text = re.sub('[ÍÌĨÎÏ]','I',text)
	text = re.sub('[óòõôö]','o',text)
	text = re.sub('[ÓÒÕÔÖ]','O',text)
	text = re.sub('[úùũûü]','u',text)
	text = re.sub('[ÚÙŨÛÜ]','U',text)
	text = re.sub('ç','c',text)
	text = re.sub('Ç','C',text)
	text = re.sub('[,\.;]','',text)
	return text

def remove_stopwords(text):
	# Lista de palavras a serem consideradas stopwords
	stopwords = sw 
	
	regxp_str = '('
	for word in stopwords:
		regxp_str += ('|' if not regxp_str == '(' else '')
		regxp_str += word
	regxp_str = regxp_str + ')'
	regxp_str = '( %s |^%s | %s$)' % (regxp_str,regxp_str,regxp_str)
	regxp = re.compile(regxp_str, re.IGNORECASE)

	aditional_stopwords = [
		'-',	'_',	'=',	'+',	',',	'\.',	';',
		'"',	'\'',	'!',	'?',	'\\\\',	'/',	'\{',
		'\}',	'\[',	'\]',	'\(',	'\)',	'<',	'>',
		'\*',	'\%',	'\$',	'\@'
	]
	aditional = '['
	for acent in aditional_stopwords:
		aditional += acent
	aditional += ']'

	text = remove_html_tags(text)
	text = remove_extra_spaces(text)

	text = re.sub(aditional,'',text)
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

