from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.http import (HttpResponse, HttpResponseNotFound,
    HttpResponseBadRequest, HttpResponseServerError)

from django.http import HttpResponseRedirect
from django.views.generic.base import View
from django.views.generic import TemplateView
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response


from systems.models import System, ProgrammingLanguage, OperatingSystem
from systems.serializers import SystemSerializer, OperatingSytemSerializer, ProgrammingLanguageSerializer
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

import hashlib, time

ranks = [{'score': 1439, 'order': 1, 'name': 'Oracle'},
{'score': 1272, 'order': 2, 'name': 'MySQL'},
{'score': 1177, 'order': 3, 'name': 'Microsoft-SQL-Server'},
{'score': 267, 'order': 4, 'name': 'MongoDB'},
{'score': 262, 'order': 5, 'name': 'PostgreSQL'},
{'score': 202, 'order': 6, 'name': 'DB2'},
{'score': 140, 'order': 7, 'name': 'Microsoft'},
{'score': 107, 'order': 8, 'name': 'Cassandra'},
{'score': 99, 'order': 9, 'name': 'SQLite'},
{'score': 99, 'order': 10, 'name': 'Redis'},
{'score': 86, 'order': 11, 'name': 'Sybase'},
{'score': 81, 'order': 12, 'name': 'Solr'},
{'score': 69, 'order': 13, 'name': 'Teradata'},
{'score': 57, 'order': 14, 'name': 'HBase'},
{'score': 53, 'order': 15, 'name': 'FileMaker'},
{'score': 52, 'order': 16, 'name': 'Elasticsearch'},
{'score': 36, 'order': 17, 'name': 'Hive'},
{'score': 35, 'order': 18, 'name': 'Informix'},
{'score': 35, 'order': 19, 'name': 'Splunk'}]

class LoadContext(object):

  @staticmethod
  def load_base_context(request):
    context = {}
    context["user"] = request.user
    context["databases"] = map(lambda x: x.name, System.objects.all())
    context["languages"] = map(lambda x: x.name, ProgrammingLanguage.objects.all())
    context["oses"] = map(lambda x: x.name, OperatingSystem.objects.all())
    return context

  @staticmethod
  def load_db_data(db):
    written_lang, oses, support_langs = [], [], []
    for os_id in db["oses"]:
      os = OperatingSystem.objects.get(id = os_id)
      oses.append(OperatingSytemSerializer(os).data['name'])
    for lang_id in db["support_languages"]:
      lang = ProgrammingLanguage.objects.get(id = lang_id)
      support_langs.append(ProgrammingLanguageSerializer(lang).data['name'])
    for lang_id in db["written_in"]:
      lang = ProgrammingLanguage.objects.get(id = lang_id)
      written_lang.append(ProgrammingLanguageSerializer(lang).data['name'])
    db["oses"] = oses
    db["written_in"] = written_lang
    db["support_languages"] = support_langs
    return db

class HomePage(View):

  def get(self, request):
    context = LoadContext.load_base_context(request)
    context["ranks"] = ranks[:5]
    return render(request, 'homepage.html',
      context)

class DatabasePage(View):

  def get(self, request, db_name):
    db_name = db_name.replace("-", " ")
    database = System.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
    return render(request, 'database.html',
        context)

class OSPage(View):

  def get(self, request, db_name):
    os = OperatingSystem.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["os"] = OperatingSystemSerializer(os).data
    return render(request, 'os.html',
        context)

class LangPage(View):

  def get(self, request, db_name):
    lang = ProgrammingLanguage.objects.get(name = db_name)
    context = LoadContext.load_base_context(request)
    context["lang"] = ProgrammingLanguageSerializer(lang).data
    return render(request, 'lang.html',
        context)

class DatabaseEditingPage(View):

  savedModels = {}

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(DatabaseEditingPage, self).dispatch(*args, **kwargs)

  def post(self, request, db_name, key):
    db_name = db_name.replace("-", " ")
    savedModels = DatabaseEditingPage.savedModels
    db = System.objects.get(name = db_name)
    if db.secret_key != key:
      return HttpResponseBadRequest()
    data = dict(request.POST)
    for field in data:
      if field == "model_stuff":
        continue
      if "support_" in field:
        data[field][0] = True if data[field][0] == "1" else False
      elif "year" in field:
        data[field][0] = int(data[field][0])
      if db.__getattribute__(field) != data[field][0]:
        db.__setattr__(field, data[field][0])
    db.save()
    options = eval(data["model_stuff"][0])
    adds = dict(map(lambda x: (x, map(lambda y: "add_" + y, options["adds"][x])), options["adds"]))
    removes = dict(map(lambda x: (x, map(lambda y: "rem_" + y, options["removes"][x])), options["removes"]))
    map(lambda x: adds[x].extend(removes[x]), adds)
    for lang_name in adds["written_in"]:
      task, lang_name = lang_name[:3], lang_name[4:]
      if lang_name in savedModels and savedModels[lang_name]:
        lang = savedModels[lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        savedModels[lang_name] = lang
      if task == "add": db.written_in.add(lang)
      else: db.written_in.remove(lang)
    for lang_name in adds["support_languages"]:
      task, lang_name = lang_name[:3], lang_name[4:]
      if lang_name in savedModels and savedModels[lang_name]:
        lang = savedModels[lang_name]
      else:
        lang = ProgrammingLanguage.objects.get(name = lang_name)
        savedModels[lang_name] = lang
      if task == "add": db.support_languages.add(lang)
      else: db.support_languages.remove(lang)
    for os_name in adds["oses"]:
      task, os_name = os_name[:3], os_name[4:]
      if os_name in savedModels and savedModels[os_name]:
        os = savedModels[os_name]
      else:
        os = OperatingSystem.objects.get(name = os_name)
        savedModels[os_name] = os
      if task == "add": db.oses.add(os)
      else: db.oses.remove(os) 
    return HttpResponseRedirect("/db/%s" % db_name)

  def get(self, request, db_name, key):
    db_name = db_name.replace("-", " ")
    database = System.objects.get(name = db_name)
    if database.secret_key == key:
      context = LoadContext.load_base_context(request)
      context["db"] = LoadContext.load_db_data(SystemSerializer(database).data)
      return render(request, 'database_edit.html',
        context)
    else:
      return HttpResponseBadRequest()

class DatabaseCreationPage(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(DatabaseCreationPage, self).dispatch(*args, **kwargs)

  @staticmethod
  def create_secret_key():
    key = hashlib.sha1()
    key.update(str(time.time()))
    return key.hexdigest()[:11]

  def get(self, request):
    return render(request, 'database_create.html',
      LoadContext.load_base_context(request))

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      key = DatabaseCreationPage.create_secret_key()
      newDB = System(name = name, secret_key = key)
      newDB.save()
      return redirect("/db/%s/%s" % (name, key))

class PLCreationView(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(PLCreationView, self).dispatch(*args, **kwargs)

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      newDB = ProgrammingLanguage(name = name)
      newDB.save()
      return HttpResponseRedirect("/createdb")

class OSCreationView(View):

  @csrf_exempt
  def dispatch(self, *args, **kwargs):
    return super(OSCreationView, self).dispatch(*args, **kwargs)

  def post(self, request):
    if request.POST.get('name', False):
      name = request.POST.get('name')
      newDB = OperatingSystem(name = name)
      newDB.save()
      return HttpResponseRedirect("/createdb")

class FetchAllSystems(APIView):

  def get(self, request):
    systems = SystemSerializer(System.objects.all(), many = True)
    return Response(systems.data)