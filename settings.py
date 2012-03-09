#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Configurações do Django para o projeto

import os

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = ()

MANAGERS = ADMINS

DATABASE_ENGINE = ''
DATABASE_NAME = ''
DATABASE_USER = ''
DATABASE_PASSWORD = ''
DATABASE_HOST = ''
DATABASE_PORT = ''

#TIME_ZONE = 'America/Sao_Paulo Brazil/East'
TIME_ZONE = 'America/Sao_Paulo'
LANGUAGE_CODE = 'pt-br'

SITE_ID = 1

USE_I18N = True

MEDIA_ROOT = ''
MEDIA_URL = ''
ADMIN_MEDIA_PREFIX = '/resources/'

APPEND_SLASH = False

SECRET_KEY = 'clippbot-sccp-2012'

TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.load_template_source',
)

MIDDLEWARE_CLASSES = (
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
	os.path.join(os.path.dirname(__file__),'templates'),
	os.path.join(os.path.dirname(__file__),'templates','email'),
)

INSTALLED_APPS = (
	'django.contrib.admin',
	'django.contrib.contenttypes',
)