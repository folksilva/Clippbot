#!/usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext.db import djangoforms as forms
from django import forms as form
from models import *

class UniqueKeyField(form.CharField):
	def to_python(self,value):
		return value
	def validate(self,value):
		super(UniqueKeyField, self).validate(value)
		if Team.get_by_key_name(value):
				raise form.ValidationError('Já existe uma equipe com este ID.')

class CreateTeamForm(forms.ModelForm):
	"""
		Formulário de equipes
	"""
	key_name = UniqueKeyField(required=True,label="ID",help_text="Informe um nome único para a sua equipe. Este nome não poderá ser alterado.")
	name = form.CharField(required=True,label='Nome',help_text="Informe o nome da sua equipe")
	description = form.CharField(required=True,label='Descrição',help_text='Descreva a sua equipe <span id="desc_chars"></span>',widget=form.Textarea,max_length=200)
	allow_subscriptions = form.BooleanField(required=False,initial=True,label='Permitir assinaturas?',help_text='Permitir que outras pessoas entrem na sua equipe? Elas precisarão conhecer o seu código de acesso.')
	subscription_code = form.CharField(required=True,min_length=8,label='Código de acesso',help_text='Informe a palavra chave, com pelo menos 8 caracteres, necessária para entrar na sua equipe')
	class Meta:
		model = Team
		fields = ('key_name','name','description','allow_subscriptions','subscription_code')

class TeamForm(forms.ModelForm):
	"""
		Formulário de equipes
	"""
	name = form.CharField(required=True,label='Nome',help_text="Informe o nome da sua equipe")
	description = form.CharField(required=True,label='Descrição',help_text='Descreva a sua equipe <span id="desc_chars"></span>',widget=form.Textarea,max_length=200)
	allow_subscriptions = form.BooleanField(required=False,initial=True,label='Permitir assinaturas?',help_text='Permitir que outras pessoas entrem na sua equipe? Elas precisarão conhecer o seu código de acesso.')
	subscription_code = form.CharField(required=True,min_length=8,label='Código de acesso',help_text='Informe a palavra chave, com pelo menos 8 caracteres, necessária para entrar na sua equipe')
	class Meta:
		model = Team
		exclude = ['creator','created','updated','key_name']

class ProfileForm(forms.ModelForm):
	"""
		Formulário de perfil de usuário
	"""
	name = form.CharField(required=True,label="Nome",help_text="Digite o seu nome completo")
	email = form.EmailField(required=True,label="E-mail",help_text="Digite o e-mail que deseja usar para receber notificações")
	im_address = form.CharField(required=False,label="Bate-papo",help_text="Digite o seu endereço XMPP. Clique <a href='/help/im' target='_blank'>aqui</a> para obter ajuda.")
	class Meta:
		model = Profile
		exclude = ['user','im']

class ChannelForm(forms.ModelForm):
	title = form.CharField(required=True,label='Título',help_text='Digite o título do canal RSS')
	feed = form.URLField(required=True,label='Endereço do canal',help_text='Digite o endereço do Canal RSS')
	link = form.URLField(required=True,label='Link do site',help_text='Digite o link para o site que fornece o RSS')
	description = form.CharField(required=True,label='Descrição',help_text='Descreva o canal RSS',widget=form.Textarea)
	frequence = form.IntegerField(required=True,label='Intervalo (min)',help_text='Defina o intervalo das atualizações, mínimo 5 e no máximo 1440',min_value=5,max_value=1440)
	class Meta:
		model = Channel
		exclude = ['team','last_sync','date','updated','next_sync']

class CategoryForm(forms.ModelForm):
	name = form.CharField(required=True,label='Nome',help_text='Digite o nome da categoria')
	color = form.CharField(required=True,label='Cor',help_text='Escolha uma cor para a categoria')
	class Meta:
		model = Category
		exclude = ['team','created','creator','updated']

class ContactForm(forms.ModelForm):
	name = form.CharField(required=True,label='Nome',help_text='Digite o nome do contato')
	email = form.EmailField(required=True,label='E-mail',help_text='Digite o e-mail do contato')
	phone = form.CharField(required=False,label='Telefone',help_text='Digite o telefone do contato')
	send_automatic = form.BooleanField(required=False,label='Enviar e-mails automáticos?',help_text='Marque para que o contato receba e-mails desta categoria automaticamente')
	class Meta:
		model = Contact
		exclude = ['created','creator','updated','category']

