#!/usr/bin/python -u

import sys, os, getpass
os.environ['DJANGO_SETTINGS_MODULE'] = 'gmail.settings'
import gmail.settings as settings

if not os.path.isdir(settings.MAIL_STORE):
  print "NOTICE: creating directory for local storage at:"
  print "        '%s'" % settings.MAIL_STORE
  os.mkdir(settings.MAIL_STORE)
if not os.path.isfile(settings.DATABASE_NAME):
  print "NOTICE: creating local storage state database"
  print "        '%s'" % settings.DATABASE_NAME
  from django.core.management import execute_manager
  execute_manager(settings,[sys.argv[0],'syncdb'])

from gmail.sync import lib

from optparse import OptionParser
usage = """
  %prog [options] [email]

If you don't provide an email address and only
one account exists, it will be used; otherwise
you will be prompted to choose among the existing
or create one. If you provide an email which has
no related account information, you will be
asked to create a new one.
"""
parser = OptionParser(usage=usage)
#parser.add_option("-f", "--file", dest="filename",
#                  help="write report to FILE", metavar="FILE")
#parser.add_option("-q", "--quiet",
#                  action="store_false", dest="verbose", default=True,
#                  help="don't print status messages to stdout")
(options, args) = parser.parse_args()

email = None
if args: email = args[0]
account = lib.choose_account(email)
if not account:
  parser.print_help()
  sys.exit(1)

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
print 'Password for "%s": ' % account.username,
password = getpass.getpass(prompt='')
lib.backup_account(account,password,skip=SKIP)
print "### That's all, folks. ###"
