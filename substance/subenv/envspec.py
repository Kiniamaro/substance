import os
import time
from collections import OrderedDict
from substance.monads import *
from substance.constants import *
from substance.utils import readDotEnv, writeToFile, makeSymlink
from substance import Shell
from substance.subenv import (SPECDIR, ENVFILE, CODELINK)
import jinja2

class SubenvSpec(object):
  def __init__(self, specPath, basePath, name=None, vars={}, lastApplied=None):
    self.specPath = specPath
    self.basePath = basePath
    self.envPath = None
    self.name = name
    self.envFiles = []
    self.overrides = vars
    self.vars = OrderedDict()
    self.lastApplied = lastApplied
    self.current = False
    self.struct = {'files': [], 'dirs': []}

  @staticmethod
  def fromEnvPath(path):
    if not os.path.isdir(path):
      return Fail(InvalidOptionError("Specified path '%s' does not exist." % path))

    envPath = path
    name = os.path.basename(envPath)

    envVars = Try.attempt(readDotEnv, os.path.join(envPath, ENVFILE))
    if envVars.isFail():
      return envVars
    envVars = envVars.getOK()

    vars = envVars.copy()
    for k in vars.keys():
      if k.startswith('subenv.'):
        del vars[k]

    lastApplied = None   
    if 'subenv.lastApplied' in envVars:
      lastApplied = envVars['subenv.lastApplied']
    
    env = SubenvSpec(envVars['subenv.specPath'], envVars['subenv.basePath'], envVars['subenv.name'], vars, lastApplied)
    env.envPath = envPath
    return env

  @staticmethod
  def fromSpecPath(path, vars={}, name=None):
    if not os.path.isdir(path):
      return Fail(InvalidOptionError("Specified path '%s' does not exist." % path))

    if os.path.basename(path) == SPECDIR or not os.path.isdir(os.path.join(path, SPECDIR)):
      return Fail(InvalidOptionError("Invalid path specified. Please pass a path to a folder with a %s directory." % SPECDIR))
    specPath = os.path.join(path, SPECDIR)

    name = os.path.basename(path) if name is None else name

    return SubenvSpec(specPath, path, name, vars).scan()

  def getLastAppliedDateTime(self, fmt='%Y-%m-%d %H:%M:%S'):
    if self.lastApplied:
      return time.strftime(fmt, time.localtime(float(self.lastApplied)))
    return None
 
  def scan(self):
    return self.loadEnvVars(self.overrides) \
      .then(self.loadEnvStruct)

  def applyTo(self, envPath):
    self.envPath = envPath
    return self.applyDirs() \
      .then(self.applyFiles)  \
      .then(self.writeEnv) \
      .then(self.linkCode) \
      .then(lambda: OK(self))

  def linkCode(self):
    return Try.sequence([
      Try.attempt(makeSymlink, self.basePath, os.path.join(self.envPath, CODELINK), True),
      Try.attempt(makeSymlink, self.specPath, os.path.join(self.envPath, SPECDIR), True)
    ])
    
  def writeEnv(self):
    dotenv = os.path.join(self.envPath, ENVFILE)
    logging.debug("Writing environment to: %s" % dotenv)
    envVars = OrderedDict(**self.vars)
    envVars.update({
      'subenv.name': self.name, 
      'subenv.basePath': self.basePath, 
      'subenv.specPath': self.specPath,
      'subenv.lastApplied': time.time()
    })

    env = "\n".join([ "%s=\"%s\"" % (k,v) for k,v in envVars.iteritems() ])
    return Try.attempt(writeToFile, dotenv, env)
  
  def applyDirs(self):
    dirs = [self.envPath]
    dirs.extend([os.path.join(self.envPath, dir) for dir in self.struct['dirs']])
    map(lambda x: logging.debug("Creating directory '%s'"%x), dirs)
    return OK(dirs).mapM(Shell.makeDirectory)

  def applyFiles(self):
    ops = []
    for file in self.struct['files']:
      fname, ext = os.path.splitext(file)
      source = os.path.join(self.specPath, file)
      dest = os.path.join(self.envPath, file)

      if fname == ENVFILE:
        continue
      elif ext == '.jinja':
        logging.debug("Rendering '%s' to %s" % (file, dest))
        dest = os.path.splitext(dest)[0]
        ops.append(self.renderFile(file, dest, self.vars))
      else:
        logging.debug("Copying '%s' to %s" % (file, dest))
        ops.append(Shell.copyFile(os.path.join(self.specPath, file), os.path.join(self.envPath, file)))
      
    return Try.sequence(ops)
 
  def renderFile(self, source, dest, vars={}):
    try:
      tplEnv = jinja2.Environment(loader=jinja2.FileSystemLoader(self.specPath))
      tpl = tplEnv.get_template(source)
 
      tplVars = vars.copy()
      tplVars.update({'subenv':self})

      with open(dest, 'wb') as fh:
        fh.write(tpl.render(**tplVars))
      return OK(None)
    except Exception as err:
      return Fail(err)
       
  def loadEnvStruct(self):
    return self.scanEnvStruct().bind(self.setEnvStruct) 

  def scanEnvStruct(self):
    struct = {'dirs':[], 'files':[]}
    for root, dirs, files in os.walk(self.specPath):
      relPath = os.path.relpath(root, self.specPath).strip('./').strip('/')
      for dir in dirs:
        struct['dirs'].append(os.path.join(relPath, dir))
      for file in files:
        struct['files'].append(os.path.join(relPath, file))
    return OK(struct)
       
  def setEnvStruct(self, struct):
    self.struct = struct
    return OK(self)
 
  def setEnvVars(self, e={}):
    self.vars = e
    return OK(self)

  def loadEnvVars(self, env={}):
    return self.readEnvFiles() \
      .map(lambda e: dict(e, **env)) \
      .bind(self.setEnvVars)

  def readEnvFiles(self):
    specEnvFile = os.path.join(self.specPath, ENVFILE)
    if os.path.isfile(specEnvFile):
      self.envFiles.append(specEnvFile)

    baseEnvFile = os.path.join(self.basePath, ENVFILE)
    if os.path.isfile(baseEnvFile):
      self.envFiles.append(baseEnvFile)

    map(lambda x: logging.info("Loading dotenv file: '%s'" % x), self.envFiles)
    return Try.sequence(map(Try.attemptDeferred(readDotEnv), self.envFiles))  \
      .map(lambda envs: reduce(lambda acc,x: dict(acc, **x), envs, {}))

  def __repr__(self):
    return "SubEnvSpec(%(name)s) spec:%(specPath)s base:%(basePath)s envFile:%(envFiles)s vars:%(vars)s files:%(struct)s" % self.__dict__