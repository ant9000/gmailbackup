from django.db import models

class Message(models.Model):
  hash          = models.CharField(max_length=500,unique=True) 
  filename      = models.CharField(max_length=500,unique=True)
  date          = models.DateTimeField()
  size          = models.PositiveIntegerField()  
  dos2unix_size = models.PositiveIntegerField()  
  #TODO: shall we add more headers for searching?

class Account(models.Model):
  email    = models.EmailField(primary_key=True)
  username = models.CharField(max_length=500) 
  server   = models.CharField(max_length=500)
  port     = models.PositiveIntegerField()
  ssl      = models.BooleanField()
  #TODO: shall we store the password, too?

class Folder(models.Model):
  account     = models.ForeignKey('Account')
  name        = models.CharField(max_length=200)
  uidvalidity = models.PositiveIntegerField()
  last_uid    = models.PositiveIntegerField() 
  last_seen   = models.DateTimeField()
  class Meta:
    unique_together = [ ('account','name') ]

class FolderMessage(models.Model):
  folder      = models.ForeignKey(Folder)
  uid         = models.PositiveIntegerField()
  message     = models.ForeignKey(Message)
  class Meta:
    unique_together = [ ('folder','uid') ]
