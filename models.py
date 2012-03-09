#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import db
from datetime import timedelta, datetime

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
	is_admin = db.BooleanProperty(default=False,required=True)
	# O membro pode receber notíficações
	can_be_notified = db.BooleanProperty(default=True,required=True)
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
	# Frequencia de sincronização do canal em minutos
	frequence = db.IntegerProperty(default=60)
	# Data da criação do canal
	date = db.DateTimeProperty()
	# Data da modificação do canal
	updated = db.DateTimeProperty()

	# Data da próxima sincronização do canal
	def next_sync(self):
		if self.last_sync:
			return self.last_sync + timedelta(minutes=self.frequence)
		else:
			now = datetime.now()
			return datetime(now.year,now.month,now.day,now.hour,now.minute)

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
	is_archived = db.BooleanProperty(default=False,required=True)
	# O item foi classificado?
	classified = db.BooleanProperty(default=False,required=True)
	# Equipe dona do item
	team = db.ReferenceProperty(reference_class=Team,collection_name='items')
	# O item é novo
	is_new = db.BooleanProperty(default=True,required=True)
	# O item falhou na categorização
	failure = db.StringProperty()

class ItemInCategory(db.Model):
	"""
		Item em uma categoria
	"""
	# Item
	item = db.ReferenceProperty(reference_class=Item,required=True,collection_name="categories")
	# Categoria
	category = db.ReferenceProperty(reference_class=Category,required=True,collection_name="items")
	# Essa categoria é uma sugestão?
	is_suggestion = db.BooleanProperty(default=False,required=True)
	# O item foi adicionado a categoria recentemente?
	is_new = db.BooleanProperty(default=True,required=True)

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

class ItemObservation(db.Model):
    """Observação do item"""
    # Item que recebeu a observação
    item = db.ReferenceProperty(reference_class=Item,required=True,collection_name="observations")
    # Contato que criou a observação
    contact = db.ReferenceProperty(reference_class=Contact,collection_name="observations")
    # Membro que criou a observação
    member = db.ReferenceProperty(reference_class=Membership,collection_name="observations")
    # Conteúdo da observação
    content = db.TextProperty(required=True)
    # Data da observação
    date = db.DateTimeProperty(auto_now_add=True)
