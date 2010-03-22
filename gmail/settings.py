# Django settings for gmail project.

import os

def here(file=''):
  return os.path.join(os.path.abspath(os.path.dirname(__file__)),file)
HERE = here

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    ('Antonio Galea', 'antonio.galea@gmail.com'),
    ('Marta Luchi',   'marta.luchi@gmail.com'),
)
MANAGERS = ADMINS

MAIL_STORE      = here('MailStore')
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME   = os.path.join(MAIL_STORE,'gmail.db')

TIME_ZONE = 'Europe/Rome'
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
MEDIA_ROOT = here('static/')
MEDIA_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/media/'
SECRET_KEY = 'pn*s()h+d!ip+u*7obj92+7kgudubbn=@cgdo2j1o@^f2e+5^o'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'gmail.urls'

TEMPLATE_DIRS = (
    here('templates')
)

INSTALLED_APPS = (
#   'django.contrib.auth',
#   'django.contrib.contenttypes',
#   'django.contrib.sessions',
#   'django.contrib.sites',
    'gmail.sync',
)
