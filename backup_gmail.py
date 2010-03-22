#!/usr/bin/python -u

import sys, os, getpass
os.environ['DJANGO_SETTINGS_MODULE'] = 'gmail.settings'
import gmail.settings as settings

if not os.path.isdir(settings.MAIL_STORE):
  #create store
  os.mkdir(settings.MAIL_STORE)
if not os.path.isfile(settings.DATABASE_NAME):
  #init database
  from django.core.management import execute_manager
  execute_manager(settings,[sys.argv[0],'syncdb'])

from gmail.sync.models import Account
from gmail.sync import lib

SERVER, PORT, SSL = 'imap.gmail.com', 993, True
if len(sys.argv)<2:
  print "Usage: %s <email>" % os.path.basename(sys.argv[0])
  sys.exit(1)
email = sys.argv[1]
try:
  account  = Account.objects.get(email=email)
except Account.DoesNotExist:
  print "No account defined for <%s>, let's create one:" % email
  username = raw_input('Username: [%s]' % email) 
  server   = raw_input('Server:   [%s]' % SERVER)
  port     = raw_input('Port:     [%s]' % PORT) 
  ssl      = raw_input('SSL:      [%s]' % SSL) 
  if username == '': username = email
  if server   == '': server = SERVER
  if port     == '': port   = PORT
  if ssl      == '': ssl    = SSL
  #TODO: add validation
  account = Account(
    email    = email,
    username = username,
    server   = server,
    port     = port,
    ssl      = ssl
  )
  account.save()

#uncomment to revalidate local cache
#lib.update_local_cache()

#uncomment to start afresh
#for folder in account.folder_set.all():
#  folder.foldermessage_set.all().delete()
#account.folder_set.all().delete()

SKIP = [
  '[Gmail]/Drafts','[Gmail]/Spam','[Gmail]/Trash',
  'BACKUP/ok','BACKUP/missing',
]
print "### Let's rock! ###"
password = getpass.getpass(prompt='Password for "%s": ' % account.username)
lib.backup_account(account,password,skip=SKIP)
print "### That's all, folks. ###"
