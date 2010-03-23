from django.conf import settings
from gmail.sync.models import *

import imaplib, email.Utils, email.parser
import os, sys, dircache, socket
import datetime, time, re

def now():
  return datetime.datetime(*time.localtime()[:6])

def get_hdr(msg,hdr):
  return ''.join(msg.get_all(hdr,['']))

def hash(msg):
  def clean(hdr):
    return re.sub('[^a-zA-Z0-9_+@\.[\]:-]+',' ',hdr).strip()[:120]
  return '|'.join([ clean(get_hdr(msg,hdr)) for hdr in ['Message-ID','Date','From','Subject'] ])

def parsedDate(dateStr):
  pDate = email.Utils.parsedate(dateStr)
  if not pDate:
    pDate = email.Utils.parsedate(dateStr.replace('.',':'))
  if not pDate:
    raise ValueError('Cannot parse date: "%s"' % dateStr)
  return pDate

def fname(hash):
  (hID,hDate,hFrom,hSubj) = hash.split('|')
  f = '%s-%s-%s' % (
    time.strftime('%Y%m%d-%H%M%S',parsedDate(hDate)),
    re.sub('[:. ]+','_',hFrom.split(' ')[-1]),
    re.sub('[:. ]+','_',hSubj)
  )
  return f

class ImapServer:
  def __init__(self,account,store,password,debug=0):
    if not os.path.isdir(store):
      raise IOError('"%s" does not exist or is not a directory.' % store)
    self.account    = account
    self.store      = store
    self.password   = password
    self.connection = None
    imaplib.Debug   = debug
  def __del__(self):
    self.shutdown()
  def connect(self):
    if not self.connection:
      if self.account.ssl: 
        imap_connect = imaplib.IMAP4_SSL
      else:
        imap_connect = imaplib.IMAP4
      try:
        self.connection = imap_connect(self.account.server,self.account.port)
        self.connection.login(self.account.username,self.password)
      except Exception,e:
        print "ERROR: %s" % e
        self.connection = None
    return self.connection 
  def shutdown(self):
    if self.connection:
      self.connection.logout()
    self.connection = None
  def list_folders(self):
    folders = []
    typ, data = self.connection.list()
    if typ != 'OK':
      print "ERROR in LIST; STATUS: %s, DATA: '%s'" % (typ,data)
      return folders
    for item in data:
      m = re.search(r'^\(([^)]+)\) "/" "(.*)"$',item)
      empty = re.search('noselect',m.group(1).lower())
      if not empty:
        folder = m.group(2)
        folders.append(folder)
    return folders
  def update_folder(self,folder_name):
    typ, data = self.connection.status(folder_name, '(UIDVALIDITY)')
    if typ != 'OK':
      print "ERROR for '%s'; STATUS: %s, DATA: '%s'" % (folder_name,typ,data)
      return None
    m = re.search(r'\(UIDVALIDITY (\d+)\)$',data[0])
    uidvalidity = int(m.group(1))
    f, created = self.account.folder_set.get_or_create(
      name     = folder_name,
      defaults = {
        'uidvalidity': uidvalidity,
        'last_uid':    0,
        'last_seen':   now(),
      }
    )
    if f.uidvalidity != uidvalidity:
      print "ERROR: folder '%s' uidvalidity has changed!!!" % folder_name
      return None
    f.last_seen = now()
    f.save()
    print "NOTICE: folder '%s', uidvalidity %d, last_uid %d" % (folder_name,uidvalidity,f.last_uid)
    return f
  def backup_folder(self,folder):
    try:
      typ, num = self.connection.select('"%s"' % folder.name)
    except Exception,e:
      if "%s" % e == "(8, 'EOF occurred in violation of protocol')":
        raise socket.error(e)
      print "ERROR: cannot select folder '%s'." % folder.name
      print ">> %s" % e
      return
    uidvalidity = int(self.connection.response('UIDVALIDITY')[1][0])
    if folder.uidvalidity != uidvalidity:
      print "ERROR: folder '%s', uidvalidity has changed!!!" % folder.name
      return
    if folder.last_uid:
      search = '(UID %s:*)' % folder.last_uid
    else:
      search = 'ALL'
    typ, data = self.connection.search(None,search)
    if typ != 'OK':
      print "ERROR: folder '%s', search failed." % folder.name
      return
    found = data[0].split()
    for num in found:
      typ, data = self.connection.fetch(num,'(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID DATE FROM SUBJECT)])')
      if typ != 'OK':
        print "ERROR: num %s, fetch headers failed: %s, %s" % (num, typ, data)
        continue
      msg = email.parser.HeaderParser().parsestr(data[0][1],headersonly=True)
      hsh = hash(msg)
      typ, data = self.connection.fetch(num, '(UID RFC822.SIZE)')
      if typ != 'OK':
        print "ERROR: num %s, fetch uid and size failed: %s, %s" % (num, typ, data)
        continue
      m    = re.search(r'^%s \(UID (\d+) RFC822.SIZE (\d+)\)$' % num,data[0])
      uid  = int(m.group(1))
      size = int(m.group(2))
      #TODO: check file size againts RFC822 size, to catch corrupted local files
      #NB:   size as reported by Gmail will differ from the os filesize!!!
      try:
        fm = folder.foldermessage_set.get(uid=uid)
        if fm.message.hash != hsh:
          print "ERROR: uid %s already exists with a different hash. Have UIDs changed???"
          continue
      except FolderMessage.DoesNotExist:
        #message is missing in this folder
        try:
          eml = Message.objects.get(hash=hsh)
        except Message.DoesNotExist:
          #message is missing also from local store, so fetch it
          print "NOTICE: uid %s, downloading message." % uid
          typ, data = self.connection.fetch(num,'(RFC822)')
          if typ != 'OK':
            print "ERROR: uid %s, fetch message failed: %s, %s" % (uid, typ, data)
            continue
          else:
            rfc822 = data[0][1]
            f = fname(hsh)
            i = 1
            while True:
              ff = '%s/%s-%d.eml' % (self.store,f,i)
              if not os.path.exists(ff): break
              i += 1
            try:
              out = file(ff,'w')
              out.write(rfc822)
              out.close()
            except IOError,e:
              print "ERROR: uid %s, storing message as '%s' failed: %s" % (uid, ff, e)
              continue
            eml = Message(
              hash     = hsh,
              filename = os.path.basename(ff),
              date     = time.strftime('%Y-%m-%d %H:%M:%S',parsedDate(get_hdr(msg,'Date'))),
              size     = os.stat(ff).st_size
            )
            eml.save()
            print "NOTICE: uid %s, stored message as '%s'." % (uid, ff)
        fm = folder.foldermessage_set.create(uid=uid, message=eml)
        fm.save()
      folder.last_uid  = uid
      folder.last_seen = now()
      folder.save()
      print "NOTICE: folder '%s', last_uid %s " % (folder.name, uid)

def update_local_cache():
  files  = dircache.listdir(settings.MAIL_STORE)
  N      = len(files)
  print "\0337",
  for n,f in enumerate(files):
    if n % 100 == 0: print "\033[1K%d / %d\0338" % (n,N),
    ff = os.path.join(settings.MAIL_STORE,f)
    if not (f.endswith(".eml") and os.path.isfile(ff)): continue
    msg  = email.parser.HeaderParser().parse(open(ff,"r"))
    hsh = hash(msg)
    date = time.strftime('%Y-%m-%d %H:%M:%S',parsedDate(get_hdr(msg,'Date')))
    size = os.stat(ff).st_size
    m,created = Message.objects.get_or_create(
      hash     = hsh,
      defaults = { 'filename': f, 'date': date, 'size': size }
    )
    if created:
      m.save()
    elif m.filename != f:
      print "ERROR: hash '%s' is not unique!!!" % hsh
    elif m.date.strftime('%Y-%m-%d %H:%M:%S') != date or m.size != size:
      print "ERROR: inconsistent date/size for file '%s'" % f
    else: #everything's ok
      pass

def backup_account(account,password,skip=[],debug=0):
  s = ImapServer(account,store=settings.MAIL_STORE,password=password,debug=debug)
  if not s.connect():
    sys.exit(1)
  folder_names, skip_update  = [], []
  while True:
    try:
      if not folder_names:
         folder_names = s.list_folders()
         skip_update  = []
      for folder_name in folder_names: 
        if folder_name not in skip_update:
          if s.update_folder(folder_name):
            #ok, do not update it again if things blow up
            skip_update.append(folder_name)
      for folder in account.folder_set.all():
        if folder.name not in skip:
          print "### BACKUP %s ###" % folder.name
          s.backup_folder(folder)
          #ok, do not retrieve it again if things blow up
          skip.append(folder.name)
    except (socket.error,socket.sslerror),e:
      #Gmail has the annoying habit of slamming down the connection
      print "ERROR: %s" % e
      #restart
      s.shutdown()
      time.sleep(3)
      s.connect()
      continue
    #if we got here, everything's ok and we can bail out
    break
  s.shutdown()

def create_account(email=None):
  SERVER, PORT, SSL = 'imap.gmail.com', 993, True
  prompt  = ''
  account = None
  if email: prompt = ' for <%s>' % email
  ask = raw_input('No account defined%s, do you want to create one? [Yn] ' % prompt)
  if len(ask) and ask.lower()[0]=='n':
    return None
  while not account:
    if not email:
      email = raw_input('Email: ') 
    username = raw_input('Username: [%s] ' % email) 
    server   = raw_input('Server:   [%s] ' % SERVER)
    port     = raw_input('Port:     [%s] ' % PORT) 
    ssl      = raw_input('SSL:      [%s] ' % SSL) 
    if username == '': username = email
    if server   == '': server = SERVER
    if port     == '': port   = PORT
    if ssl      == '': ssl    = SSL
    try:
      account = Account(
        email    = email,
        username = username,
        server   = server,
        port     = port,
        ssl      = ssl
      )
      account.save()
    except Exception,e:
      print "ERROR: %s" % e
      ask = raw_input('Do you want to retry? [Yn] ')
      if len(ask) and ask.lower()[0]=='n':
        return None
      account = None
  return account

def choose_account(email):
  if email:
    try:
      account = Account.objects.get(email=email)
    except Account.DoesNotExist:
      account = create_account(email)
  elif Account.objects.count() == 0:
    account = create_account(email)
  elif Account.objects.count() == 1:
    account = Account.objects.all()[0]
  else:
    N = Account.objects.count()
    accounts = [ ('%s' % i,a) for i,a in enumerate(Account.objects.order_by('server','email')) ]
    for i,a in accounts:
      print '[%2s] <%s>' % (i,a.email)
    print '[ q] QUIT'
    ask      = None
    accounts = dict(accounts)
    while not accounts.has_key(ask):
      ask = raw_input('Account #? ')
      if len(ask) and ask.lower()[0]=='q':
        return None
    account = accounts[ask]
  return account
