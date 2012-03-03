#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import db
from datetime import timedelta, datetime

class _ChannelNextSyncPropertyDatastore():
	def __init__(self,val):
		self.value = val
	def retval(self):
		return self.value

class ChannelNextSyncProperty(db.Property):
	def __init__(self,*args,**kw):
		super(ChannelNextSyncProperty, self).__init__(*args, **kw)

	def calculateGet(self):
		if self.instance.last_sync:
			return self.instance.last_sync + timedelta(minutes=self.instance.frequence)
		else:
			now = datetime.now()
			return datetime(now.year,now.month,now.day,now.hour,now.minute)

	def attr_name(self):
		if self._attr_name:
			return self._attr_name()
		else:
			return "_" + self.name

	def __get__(self, model_instance, class_instance):
		if model_instance is None:
			return self
		last = model_instance.last_sync
		next = None
		if last:
			next = last + timedelta(minutes=model_instance.frequence)
		else:
			now = datetime.now()
			next = datetime(now.year,now.month,now.day,now.hour,now.minute)
		setattr(model_instance,self.attr_name(),next)
		return next

	def __set__(self,model_instance,value):
		if isinstance(value,_ChannelNextSyncPropertyDatastore):
			setattr(model_instance,self.attr_name(),value.retval())
		else:
			raise db.DerivedPropertyError("Calculado automaticamente, nada a fazer")

	def make_value_from_datastore(self,value):
		return _ChannelNextSyncPropertyDatastore(value)

class Team(db.Model):
	"""
		Uma equipe de usuários do Clippbot
	"""
	# Nome da equipe. O keyname será usado na URL da equipe. Ex.: corinthians (clippbot/team/corinthians)
	name = db.StringProperty(required=True)
	# Breve descrição da equipe. O nome a ser exibido. Ex.: Assessoria de imprensa do Sport Club Corinthians Paulista
	description = db.StringProperty(required=True)
	# Usuário que criou a equipe
	creator = db.UserProperty(required=True,auto_current_user_add=True)
	# Data de criação da equipe
	created = db.DateTimeProperty(auto_now_add=True)
	# Data de modificação da equipe
	updated = db.DateTimeProperty(auto_now=True)
	# Permitir que usuários entrem na equipe?
	allow_subscriptions = db.BooleanProperty(default=True)
	# Código secreto para usuários entrarem na equipe, gerado automaticamente
	subscription_code = db.StringProperty()

class Profile(db.Model):
	"""
		Perfil de um usuário
	"""
	# Usuário dono do perfil
	user = db.UserProperty(required=True,auto_current_user_add=True)
	# Nome do usuário por extenso
	name = db.StringProperty(required=True)
	# E-mail do usuário para receber notificações, por padrão o mesmo do usuário, mas pode ser alterado
	email = db.EmailProperty(required=True)
	# Conta XMPP do usuário
	im = db.IMProperty()

class Membership(db.Model):
	"""
		Membro de uma equipe
	"""
	# Perfil do usuário
	profile = db.ReferenceProperty(reference_class=Profile,required=True,collection_name="teams")
	# Equipe ao qual o membro pertence
	team = db.ReferenceProperty(reference_class=Team,required=True,collection_name="members")
	# O membro é administrador da equipe?
	is_admin = db.BooleanProperty(default=False)
	# O membro pode receber notíficações
	can_be_notified = db.BooleanProperty(default=True)
	# Data da criação do membro
	created = db.DateTimeProperty(auto_now_add=True)
	# Data de modificação do membro
	updated = db.DateTimeProperty(auto_now=True)

class Channel(db.Model):
	"""
		Canal de notícias RSS
	"""
	# Título do canal
	title = db.StringProperty()
	# Fonte do RSS/Atom
	feed = db.LinkProperty()
	# Link do canal
	link = db.LinkProperty()
	# Descrição do canal
	description = db.TextProperty()
	# Equipe dona do canal
	team = db.ReferenceProperty(reference_class=Team,required=True,collection_name="channels")
	# Data da última sincronização do canal
	last_sync = db.DateTimeProperty()
	# Data da próxima sincronização do canal
	next_sync = ChannelNextSyncProperty(required=True)
	# Frequencia de sincronização do canal em minutos
	frequence = db.IntegerProperty(default=60)
	# Data da criação do canal
	date = db.DateTimeProperty()
	# Data da modificação do canal
	updated = db.DateTimeProperty()

class Category(db.Model):
	"""
		Categoria de itens de notícia
	"""
	# Nome da categoria
	name = db.StringProperty()
	# Cor da categoria em formato hexadecimal. Ex.: #FF0000
	color = db.StringProperty()
	# Equipe dona da categoria
	team = db.ReferenceProperty(reference_class=Team,required=True,collection_name="categories")
	# Data da criação da categoria
	created = db.DateTimeProperty(auto_now_add=True)
	# Usuário que criou a categoria
	creator = db.UserProperty(auto_current_user_add=True)
	# Data da modificação da categoria
	updated = db.DateTimeProperty(auto_now=True)

class Item(db.Model):
	"""
		Item de notícia
	"""
	# Título da notícia
	title = db.StringProperty(required=True)
	# Link da notícia
	link = db.LinkProperty(required=True)
	# Descrição da notícia
	description = db.TextProperty(required=True)
	# Autor da notícia
	author = db.StringProperty()
	# Data de publicação da notícia
	date = db.DateTimeProperty()
	# URL de item anexado
	enclosure = db.LinkProperty()
	# Canal origem da notícia
	source_channel = db.ReferenceProperty(reference_class=Channel,required=True,collection_name="items")
	# O item está arquivado?
	is_archived = db.BooleanProperty(default=False)

class ItemInCategory(db.Model):
	"""
		Item em uma categoria
	"""
	# Item
	item = db.ReferenceProperty(reference_class=Item,required=True,collection_name="categories")
	# Categoria
	category = db.ReferenceProperty(reference_class=Category,required=True,collection_name="items")
	# Essa categoria é uma sugestão?
	is_sugestion = db.BooleanProperty(default=False)

class Contact(db.Model):
	"""
		Contato rápido de uma categoria
	"""
	# Nome do contato
	name = db.StringProperty()
	# E-mail do contato
	email = db.EmailProperty()
	# Categoria do contato
	category = db.ReferenceProperty(reference_class=Category,required=True,collection_name="contacts")
	# Telefone para SMS do contato
	phone = db.PhoneNumberProperty()
	# Enviar as notícias automáticamente para esse contato?
	send_automatic = db.BooleanProperty(default=True)
	# Data da criação do contato
	created = db.DateTimeProperty(auto_now_add=True)
	# Usuário que criou o contato
	creator = db.UserProperty(auto_current_user_add=True)
	# Data da modificação do contato
	updated = db.DateTimeProperty(auto_now=True)
