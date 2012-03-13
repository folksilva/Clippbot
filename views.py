#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import feedparser
import logging
from datetime import datetime
from dateutil import parser

from google.appengine.api import users

from google.appengine.ext import db
from google.appengine.ext.db import djangoforms

from google.appengine.api import xmpp
from google.appengine.api.labs import taskqueue

import django
from django import http
from django import shortcuts
from django.http import HttpResponseRedirect as Redirect
from django.forms.util import ErrorList
from django.core.paginator import Paginator, InvalidPage, EmptyPage

from models import *
from forms import *
from utils import *

class DivErrorList(ErrorList):
	def __unicode__(self):
		return self.as_divs()
	def as_divs(self):
		if not self: return u''
		return u'<div class="errorlist">%s</div>' % ''.join([u'<div class="error">%s</div>' % e for e in self])

def getProfile(user,request):
	""" Força o carregamento de um perfil de usuário válido """
	if not user or user == None:
		return Redirect(users.CreateLoginURL(request.path))
	profile = Profile.all().filter('user =',user).get()
	if not profile or profile == None:
		return Redirect('/')
	return profile

def respond(request, user, template, params=None):
	"""Helper to render a response, passing standard stuff to the response.

	Args:
	request: The request object.
	user: The User object representing the current user; or None if nobody
	  is logged in.
	template: The template name; '.html' is appended automatically.
	params: A dict giving the template parameters; modified in-place.

	Returns:
	Whatever render_to_response(template, params) returns.

	Raises:
	Whatever render_to_response(template, params) raises.
	"""
	if params is None:
		params = {}
	if user:
		params['profile'] = Profile.all().filter('user =',user).get()
		params['user'] = user
		params['sign_out'] = users.CreateLogoutURL('/')
		params['is_admin'] = (users.IsCurrentUserAdmin() and 'Dev' in os.getenv('SERVER_SOFTWARE'))
	else:
		params['sign_in'] = users.CreateLoginURL(request.path)
	if not template.endswith('.html'):
		template += '.html'
	return shortcuts.render_to_response(template,params)

def index(request):
	"""Página inicial"""
	user = users.GetCurrentUser()
	if user:
		profile = Profile.all().filter('user =',user).get()
		if not profile:
			# Primeiro acesso
			profile_data = {'email':user.email(),'name':user.nickname()}
			form = ProfileForm(data=request.POST or profile_data, instance = profile, error_class=DivErrorList)
			if not request.POST:
				return respond(request,user,'index',{'form':form,'title':'Crie seu perfil'})
			errors = form.errors
			if form.is_valid():
				try:
					profile = form.save()
					im_address = form.cleaned_data['im_address']
					if im_address:
						im_user, im_protocol = im_address.split('@')
						im_protocol = 'http://%s' % im_protocol
						profile.im = '%s %s' % (im_protocol,im_user)
					profile.put()
					taskparams = {
						'to':'%s <%s>' % (profile.name,profile.email),
						'subject':'Bem vindo!',
						'body':getTemplate('welcome_pure',{'name':profile.name}),
						'html':getTemplate('welcome',{'name':profile.name})
					}
					taskqueue.add(queue_name='mail',params=taskparams)
					return Redirect('/teams')
				except ValueError, err:
					errors['__all__'] = unicode(err)
			return respond(request,user,'index',{'form':form,'title':'Crie seu perfil'})

		elif not profile.teams or profile.teams.count(1) == 0:
			# Sem equipe
			return Redirect('/teams')

		elif profile.teams.count(2)>1:
			# Mais de uma equipe
			memberships_list = profile.teams
			paginator = Paginator(memberships_list,10)
			try:
				page = int(request.GET.get('page','1'))
			except ValueError:
				page = 1
			try:
				memberships = paginator.page(page)
			except (EmptyPage,InvalidPage):
				memberships = paginator.page(paginator.num_pages)
			return respond(request,user,'index',{'memberships':memberships,'title':'Escolha a equipe'})

		else:
			# Uma equipe
			membership = profile.teams.get()
			return Redirect('/team/%s' % membership.team.key().name())
	return respond(request,user,'index')

def teams(request):
	"""Lista de equipes"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;

	teams_list = Team.all().order('-allow_subscriptions').order('name')
	paginator = Paginator(teams_list,10)
	
	try:
		page = int(request.GET.get('page','1'))
	except ValueError:
		page = 1
	
	try:
		teams = paginator.page(page)
	except (EmptyPage,InvalidPage):
		teams = paginator.page(paginator.num_pages)

	new_team = None
	form = CreateTeamForm(data=request.POST or None, instance = new_team, error_class=DivErrorList)
	if request.POST:
		errors = form.errors
		if form.is_valid():
			try:
				team = form.save()
				admin = Membership(profile=profile,team=team,is_admin=True)
				admin.put()
				return Redirect('/team/%s' % team.key().name())
			except ValueError, err:
				errors['__all__'] = unicode(err)

	return respond(request,user,'teams',{'teams':teams,'form':form,'title':'Equipes'})

def team_home(request,team_key):
	"""Home da equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		if team.allow_subscriptions:
			return Redirect('/team/%s/join' % team.key().name())
		else:
			return Redirect('/teams')

	paginator = Paginator(team.items.filter("classified =",False).filter("is_archived =",False).order("-date"),10)
	try:
		page = int(request.GET.get('page','1'))
	except ValueError:
		page = 1
	
	try:
		items = paginator.page(page)
	except (EmptyPage,InvalidPage):
		items = paginator.page(paginator.num_pages)

	return respond(request,user,'home',{'team':team,'membership':membership,'action':'home','items':items,'title':team.name})

def team_join(request,team_key):
	"""Entrar na equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if membership:
		return Redirect('/team/%s' % team.key().name())
	if not request.POST:
		return respond(request,user,'home',{'team':team,'action':'join','title':'Entrar na equipe'})
	else:
		subscription_code = request.POST.get('subscription_code')
		if subscription_code == team.subscription_code:
			member = Membership(profile=profile,team=team)
			member.put()
			for name,email in getTeamAdminEmails(team):
				taskparams = {
					'to':'%s <%s>' % (name,email),
					'subject':'Novo membro',
					'body':getTemplate('email_new_member_pure',{'member':member}),
					'html':getTemplate('email_new_member',{'member':member})
				}
				taskqueue.add(queue_name='mail',params=taskparams)
			return Redirect('/team/%s' % team.key().name())
		else:
			return respond(request,user,'home',{'team':team,'action':'join','error':'O código secreto está incorreto.','title':'Entrar na equipe'})

def team_exit(request,team_key):
	"""Sair da equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams/')
	if not request.POST:
		return respond(request,user,'home',{'team':team,'action':'exit','title':'Sair da equipe'})
	else:
		membership.delete()
		return Redirect('/teams/')

def team_edit(request,team_key):
	"""Editar equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership or not membership.is_admin:
		return Redirect('/team/%s' % team.key().name())

	form = TeamForm(data=request.POST or None, instance = team, error_class=DivErrorList)
	if request.POST:
		errors = form.errors
		if form.is_valid():
			try:
				team = form.save()
				return Redirect('/team/%s' % team.key().name())
			except ValueError, err:
				errors['__all__'] = unicode(err)
	return respond(request,user,'home',{'team':team,'membership':membership,'form':form,'action':'edit','title':'Editar a equipe'})

def team_members(request,team_key):
	"""Exibir/editar membros da equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')

	if request.GET.get('change') and request.GET.get('level'):
		member = Membership.get(request.GET.get('change'))
		if member: 
			if request.GET.get('level') == "a":
				member.is_admin = True
			elif request.GET.get('level') == "c":
				member.is_admin = False
			member.put()
			return Redirect('/team/%s/members' % team.key().name())
	elif request.GET.get('kick'):
		member = Membership.get(request.GET.get('kick'))
		if member: 
			member.delete()
			return Redirect('/team/%s/members' % team.key().name())
	elif request.GET.get('notify') and request.GET.get('can'):
		member = Membership.get(request.GET.get('notify'))
		if member: 
			if request.GET.get('can') == "y":
				member.can_be_notified = True
			elif request.GET.get('can') == "n":
				member.can_be_notified = False
			member.put()
			return Redirect('/team/%s/members' % team.key().name())
	
	members_list = Membership.all().filter('team =',team)
	paginator = Paginator(members_list,10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		members = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		members = paginator.page(paginator.num_pages)

	return respond(request,user,'home',{'team':team,'membership':membership,'members':members,'action':'members','title':'Membros da equipe'})

def team_channels(request, team_key):
	"""Exibir/adicionar canais RSS da equipe"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')

	if request.POST:
		feed = request.POST.get("feed")
		if feed and Channel.all().filter("feed =",feed).count(1) == 0:
			new_channel = Channel(feed=feed,team=team)
			# Obter as informações do Canal RSS/ATOM
			d = feedparser.parse(feed)
			if not d.bozo == 1:
				new_channel.title = d.feed.get("title","Novo canal RSS")
				new_channel.description = d.feed.get("description","Canal RSS/Atom")
				new_channel.link = d.feed.get("link")
				new_channel.frequence = 60
				new_channel.date = parser.parse(d.feed.get("date",datetime.now().__str__()))
				new_channel.updated = parser.parse(d.feed.get("updated",datetime.now().__str__()))
				new_channel.put()
				# Colocar a sincronização na fila de tarefas
				taskqueue.add(queue_name='sync',params={'channel':new_channel.key()})

	channels_list = Channel.all().filter("team =",team).order('-title')
	paginator = Paginator(channels_list,10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		channels = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		channels = paginator.page(paginator.num_pages)

	return respond(request,user,'channels',{'team':team,'channels':channels,'title':'Canais RSS'})

def channel(request, team_key, channel_key):
	"""Editar o canal RSS e listar últimos itens"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')
	channel = Channel.get(channel_key)
	if not channel:
		return Redirect('/team/%s/channels' % team.key().name())

	if request.GET:
		if request.GET.get('do') == 'delete':
			channel.delete()
			return Redirect('/team/%s/channels' % team.key().name())

	form = ChannelForm(data=request.POST or None, instance = channel, error_class=DivErrorList)
	if request.POST:
		errors = form.errors
		if form.is_valid():
			try:
				channel = form.save()
			except ValueError, err:
				errors['__all__'] = unicode(err)

	paginator = Paginator(channel.items,10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		items = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		items = paginator.page(paginator.num_pages)

	return respond(request,user,'channel',{'channel':channel,'form':form,'items':items,'team':team,'title':channel.title})

def team_categories(request, team_key):
	"""Exibir/adicionar/editar categorias de itens"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')

	category = None
	action = "new"
	if request.GET:
		edit = request.GET.get('edit')
		delete = request.GET.get('delete')
		if edit:
			category = Category.get_by_key_name(edit)
			action = "edit"
		elif delete:
			delete_category = Category.get_by_key_name(delete)
			for c in delete_category.contacts:
				c.delete()
			delete_category.delete()
			return Redirect('/team/%s/categories' % team.key().name())
	
	form = CategoryForm(data=request.POST or None, instance = category, error_class=DivErrorList)
	if request.POST:
		errors = form.errors
		if form.is_valid():
			try:
				name = form.cleaned_data['name']
				color = form.cleaned_data['color']
				key_name = "_".join(name.lower().split())
				category = Category(parent=team,key_name=key_name,name=name,color=color,team=team)
				category.put()
				return Redirect('/team/%s/categories' % team.key().name())
			except ValueError, err:
				errors['__all__'] = unicode(err)

	paginator = Paginator(team.categories,10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		categories = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		categories = paginator.page(paginator.num_pages)

	return respond(request,user,'categories',{'categories':categories,'team':team, 'form':form, 'action':action,'title':'Categorias da equipe'})

def category(request, team_key, category_key):
	"""Exibir/adicionar/editar os contatos rápidos da categoria"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')
	category = Category.get_by_key_name(category_key,parent=team)
	if not category:
		return Redirect('/team/%s/categories' % team.key().name())

	contact = Contact(category=category)
	action = "new"
	if request.GET:
		edit = request.GET.get('edit')
		delete = request.GET.get('delete')
		if edit:
			contact = Contact.get(edit)
			action = "edit"
		elif delete:
			delete_contact = Contact.get(delete)
			delete_contact.delete()
			return Redirect('/team/%s/categories/%s' % (team.key().name(),category.key()))
	form = ContactForm(data=request.POST or None, instance = contact, error_class=DivErrorList)
	if request.POST:
		errors = form.errors
		if form.is_valid():
			try:
				contact = form.save()
				return Redirect('/team/%s/categories/%s' % (team.key().name(),category.key().name()))
			except ValueError, err:
				errors['__all__'] = unicode(err)

	paginator = Paginator(category.contacts.order("name"),10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		contacts = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		contacts = paginator.page(paginator.num_pages)

	return respond(request,user,'category',{'category':category,'team':team,'contacts':contacts,'form':form, 'action':action,'title':category.name})

def category_items(request, team_key, category_key):
	"""Exibir os itens da categoria"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(team_key)
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')
	category = Category.get_by_key_name(category_key,parent=team)
	if not category:
		return Redirect('/team/%s/categories' % team.key().name())

	items_list = category.items
	paginator = Paginator(items_list,10)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		items = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		items = paginator.page(paginator.num_pages)

	return respond(request,user,'category_items',{'category':category,'team':team,'items':items,'title':'Itens da categoria'})

def profile(request,profile_key=None):
	"""Exibir perfil de um usuário"""
	user = users.GetCurrentUser()
	profile = None
	is_me = False
	form = None
	if not profile_key:
		profile = getProfile(user,request)
		is_me = True
		if not isinstance(profile,Profile):return profile;
	else:
		profile = Profile.get(profile_key)
		if profile.user == user:
			is_me = True

	if is_me:
		if request.GET and request.GET.get("do") and request.GET.get("do") == "delete":
			profile.delete()
			return Redirect('/')

		form = ProfileForm(data=request.POST or None, instance = profile, error_class=DivErrorList)
		if request.POST:
			errors = form.errors
			if form.is_valid():
				try:
					profile = form.save()
				except ValueError, err:
					errors['__all__'] = unicode(err)
	return respond(request,user,'profile',{'p':profile,'form':form,'title':profile.name})

def item(request,item_key):
	"""Exibir uma notícia"""
	user = users.GetCurrentUser()
	# Buscar o item pela key
	try:
		item = Item.get_by_key_name(item_key)
		if not item or not isinstance(item,Item):
		# Se não encontrar, exibir o erro 404
			raise http.Http404
	except db.KindError:
		raise http.Http404

	if request.POST and request.POST.get('observation'):
		profile = getProfile(user,request)
		if profile and isinstance(profile,Profile):
			team = Team.get_by_key_name(item.source_channel.team.key().name())
			if team:
				membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
				if membership:
					observation = ItemObservation(item=item,member=membership,content=request.POST.get('observation'))
					observation.put()
					return Redirect("/%s" % item.key().name())
	return respond(request,user,'item',{'item':item,'title':item.title})

# TO-DO
def item_edit(request,item_key):
	"""Alterar as categorias de um item"""
	# Buscar o item pela key
	try:
		item = Item.get_by_key_name(item_key)
		if not item or not isinstance(item,Item):
		# Se não encontrar, exibir o erro 404
			raise http.Http404
	except db.KindError:
		raise http.Http404

	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	team = Team.get_by_key_name(item.source_channel.team.key().name())
	if not team:
		return Redirect('/teams')
	membership = Membership.all().filter('profile =',profile).filter('team =',team).get()
	if not membership:
		return Redirect('/teams')

	categories = []
	for c in team.categories:
		category = {"name":c.name,"color":c.color,"key_name":c.key().name()}
		item_category = item.categories.filter("category =",c).get()
		if item_category:
			if item_category.is_suggestion:
				category['suggestion'] = True
			else:
				category['selected'] = True
		categories.append(category)

	selecteds = None
	if request.POST:
		selecteds = request.POST.getlist('categories')
		
		# Remover categorias excluidas
		for c in item.categories:
			if not c.category.key().name() in selecteds or len(selecteds) == 0:
				logging.info("Item %s removed from category %s." % (item.key().name(),c.category.key().name()))
				c.delete()
		
		# Adicionar as novas categorias
		for s in selecteds:
			selected_category = Category.get_by_key_name(s,parent=team)
			item_in_category = item.categories.filter("category =",selected_category).get()
			if not item_in_category:
				logging.info("Item %s saved in category %s." % (item.key().name(),selected_category.key().name()))
				item_in_category = ItemInCategory(item=item,category=selected_category,is_suggestion=False,is_new=True)
				item_in_category.put()
			elif item_in_category.is_suggestion:
				item_in_category.is_suggestion = False
				item_in_category.is_new = True
				item_in_category.put()
			else:
				continue

			"""for contact in selected_category.contacts.filter("send_automatic =",True):
				taskparams = {
					'sender': 'comment.%s' % item.key(),
					'to':"%s <%s>" % (contact.name,contact.email),
					'subject':u'[%s] Nova notícia: %s' % (selected_category.name,item.title),
					'body':getTemplate('new_item_pure',{'item':item}),
					'html':getTemplate('new_item',{'item':item})
				}
				taskqueue.add(queue_name='mail',params=taskparams)"""

		if len(selecteds) > 0:
			item.classified = True
			item.put()

		return Redirect("/%s" % item.key().name())

	return respond(request,user,'item-edit',{'item':item,'categories':categories,'title':'Editar o item'})

def help(request,topic=None):
	"""Ajuda"""
	user = users.GetCurrentUser()
	if not topic: 
		topic = 'help'
	return respond(request,user,topic,{'title':'Ajuda do Clippbot'})

def issue(request):
	"""Formulário para envio de dúvidas"""
	user = users.GetCurrentUser()
	return respond(request,user,"issue",{'title':'Questões'})

def search(request,query=None):
	"""Exibir os resultados de uma pesquisa"""
	user = users.GetCurrentUser()
	profile = getProfile(user,request)
	if not isinstance(profile,Profile):return profile;
	
	if not query:
		query = request.GET.get('q')
		if not query:
			return respond(request,user,'results')
		return Redirect("/search/%s" % "+".join(query.split()))

	results_list = []
	queries = [query]
	if "+" in query:
		queries = query.split("+")

	for member in profile.teams:
		for item in member.team.items:
			reverse_points = 0
			if len(queries) > 1:
				# Contém exatamente igual
				query = " ".join(queries)
				if query in item.title:
					if item.title.startswith(query):
						reverse_points -= 50
					elif not item.title.startswith(query) and not item.title.endswith(query):
						reverse_points -= 49
					else:
						reverse_points -= 48
					reverse_points *= item.title.count(query)
				
				if query in item.description:
					if item.description.startswith(query):
						reverse_points -= 46
					elif not item.description.startswith(query) and not item.description.endswith(query):
						reverse_points -= 45
					else:
						reverse_points -= 44
					reverse_points *= item.description.count(query)

				if query in item.link:
					link = item.link
					if link.startswith("http://"):
						link = link[7:]
					elif link.startswith("https://"):
						link = link[8:]
					link_parts = link.split("/")
					if query in link_parts[0]:
						reverse_points -= 43
					elif query in link_parts[1]:
						reverse_points -= 42
					else:
						reverse_points -= 41
					reverse_points *= item.link.count(query)

				# Contém em minusculo
				query = query.lower()
				if query in item.title.lower():
					if item.title.lower().startswith(query):
						reverse_points -= 20
					elif not item.title.lower().startswith(query) and not item.title.lower().endswith(query):
						reverse_points -= 19
					else:
						reverse_points -= 18
					reverse_points *= item.title.lower().count(query)
				
				if query in item.description.lower():
					if item.description.lower().startswith(query):
						reverse_points -= 16
					elif not item.description.lower().startswith(query) and not item.description.lower().endswith(query):
						reverse_points -= 15
					else:
						reverse_points -= 14
					reverse_points *= item.description.lower().count(query)

				if query in item.link.lower():
					link = item.link.lower()
					if link.startswith("http://"):
						link = link[7:]
					elif link.startswith("https://"):
						link = link[8:]
					link_parts = link.split("/")
					if query in link_parts[0]:
						reverse_points -= 13
					elif query in link_parts[1]:
						reverse_points -= 12
					else:
						reverse_points -= 11
					reverse_points *= item.link.lower().count(query)

			for q in queries:
				query = q.lower()
				if query in item.title.lower():
					if item.title.lower().startswith(query):
						reverse_points -= 10
					elif not item.title.lower().startswith(query) and not item.title.lower().endswith(query):
						reverse_points -= 9
					else:
						reverse_points -= 8
					reverse_points *= item.title.lower().count(query)
				
				if query in item.description.lower():
					if item.description.lower().startswith(query):
						reverse_points -= 6
					elif not item.description.lower().startswith(query) and not item.description.lower().endswith(query):
						reverse_points -= 5
					else:
						reverse_points -= 4
					reverse_points *= item.description.lower().count(query)

				if query in item.link.lower():
					link = item.link.lower()
					if link.startswith("http://"):
						link = link[7:]
					elif link.startswith("https://"):
						link = link[8:]
					link_parts = link.split("/")
					if query in link_parts[0]:
						reverse_points -= 3
					elif query in link_parts[1]:
						reverse_points -= 2
					else:
						reverse_points -= 1
					reverse_points *= item.link.lower().count(query)

			if reverse_points < 0:
				results_list.append({'points':reverse_points*-1,'order':reverse_points,'item':item})

	paginator = Paginator(sorted(results_list, key=lambda points: points['order']),20)
	try: 
		page = int(request.GET.get('page','1')) 
	except ValueError: 
		page = 1
	try: 
		results = paginator.page(page) 
	except (EmptyPage,InvalidPage): 
		results = paginator.page(paginator.num_pages)

	return respond(request,user,'results',{'queries':queries,'query':" ".join(queries),'results':results})