import sys
import os
import logging
import paramiko
from paramiko.py3compat import u
import socket
from time import time
from collections import namedtuple
from substance.monads import *
from substance.exceptions import *

logging.getLogger("paramiko").setLevel(logging.CRITICAL)

LinkResponse = namedtuple('LinkResponse', ['link','stdin','stdout','stderr', 'code', 'cmd'])

try:
  import termios
  import tty
  hasTermios = True
except ImportError:
  hasTermios = False


class Link(object):
  
  def __init__(self, keyFile):
    self.keyFile = keyFile
    self.key = None
    self.username = "substance"
    self.port = 22
    self.connected = False
    self.client = None
    self.sftp = None

  def waitForConnect(self, maxtries=200, timeout=60):

    start = time()   
    tries = 0

    while not self.connected:
      logging.debug("Connect attempt %s..." % tries)
      state = self.connect()  \
        .catchError(paramiko.ssh_exception.SSHException, lambda err: OK(None)) \
        .catchError(socket.error, lambda err: OK(None)) 
      if state.isFail():
        return state
      if time() - start > timeout:
        return Fail(LinkConnectTimeoutExceeded("Timeout exceeded"))
      if tries >= maxtries:
        return Fail(LinkRetriesExceeded("Max retries exceeded"))
      tries += 1
  
    return OK(self)
 
  def connectEngine(self, engine):
    connectDetails = engine.getConnectInfo()
    self.hostname = connectDetails.get('hostname')
    self.port = connectDetails.get('port')
    logging.info("Connecting to engine %s via %s:%s" % (engine.name, self.hostname, self.port))
    return self.loadKey().then(self.waitForConnect)

  def connectHost(self, host, port):
    self.hostname = host
    self.port = port
    return self.loadKey().then(self.waitForConnect)

  def loadKey(self):
    try:
      if not self.key:
        self.key = paramiko.rsakey.RSAKey.from_private_key_file(self.keyFile, password=None)
      logging.debug("Connecting using key: %s" % self.keyFile)
    except Exception as err:
      return Fail(err)
    return OK(self.key) 

  def connect(self):
    try:
      self.client = paramiko.SSHClient()
      self.client.load_system_host_keys()
      self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
      options = self.getConnectOptions()
      self.client.connect(**options)
      self.connected = True
      return OK(self)
    except Exception as err:
      return Fail(err)

  def getConnectOptions(self):
    return {
      'hostname': self.hostname,
      'port': self.port,
      'username': self.username, 
      'pkey': self.key,
      'allow_agent': True,
      'look_for_keys': True,
      'timeout': 1,
      'banner_timeout': 1
    }

  def command(self, cmd, *args, **kwargs):
    return self.runCommand(cmd, *args, **kwargs) 

  def streamCommand(self, cmd, *args, **kwargs):
    return self.runCommand(cmd, stream=True) 

#  def runCommand(self, cmd, *args, **kwargs):
#    try:
#      stdin, stdout, stderr = self.client.exec_command(cmd, *args, **kwargs)
#      return OK(LinkResponse(link=self, cmd=cmd, stdin=stdin, stdout=stdout, stderr=stderr, code=None))
#    except Exception as err:
#      return Fail(err)
#
#  def onRunCommand(self, linkResponse):
#    return OK(LinkResponse(
#      link=self,
#      cmd=linkResponse.cmd,
#      stdin=linkResponse.stdin,
#      stdout=linkResponse.stdout,
#      stderr=linkResponse.stderr,
#      code=linkResponse.stdout.channel.recv_exit_status()
#    ))

  def runCommand(self, cmd, sudo=False, stream=False, *args, **kwargs):
   
    cmd = "sudo %s" % cmd if sudo is True else "%s" % cmd

    logging.debug("LINKCOMMAND: %s" % cmd)

    try:
      channel = self.client.get_transport().open_session()
      forward = paramiko.agent.AgentRequestHandler(channel)
      stdin = channel.makefile('wb', -1)
      stdout = channel.makefile('rb', -1)
      stderr = channel.makefile('rb', -1)
      channel.exec_command(cmd, *args, **kwargs)
      while True:
        if channel.exit_status_ready():
          break
        if channel.recv_ready() and stream:
          sys.stdout.write(channel.recv(1024))
         
        if channel.recv_stderr_ready() and stream:
          sys.stdout.write(channel.recv_stderr(1024))

      code = channel.recv_exit_status()

      return OK(LinkResponse(link=self, cmd=cmd, stdin=stdin, stdout=stdout, stderr=stderr, code=code))
    except Exception as err:
      return Fail(err)


  def getClient(self):
    return self.client

  def getSFTP(self):
    if not self.sftp:
      self.sftp = self.client.open_sftp()
    return self.sftp

  def upload(self, localPath, remotePath):
    return Try.attempt(self._put, localPath, remotePath)
    
  def download(self, remotePath, localPath):
    return Try.attempt(self._get, remotePath, localPath)

  def runScript(self, scriptPath, sudo=False):
    scriptName = "/tmp/%s.sh" % time()

    return self.upload(scriptPath, scriptName) \
      .then(defer(self.runCommand, "chmod +x %s" % scriptName, sudo=True)) \
      .then(defer(self.runCommand, cmd=scriptName, sudo=sudo, stream=True))

  def interactive(self):
    if hasTermios:
      return Try.attempt(self._posixShell)
    else:
      return Try.attempt(self._windowsShell)

  def _posixShell(self):
    import select
 
    channel = self.client.invoke_shell()
    forward = paramiko.agent.AgentRequestHandler(channel)
         
    sys.stdout.write('\r\n*** Begin interactive session.\r\n')
    oldtty = termios.tcgetattr(sys.stdin)
    try:
      tty.setraw(sys.stdin.fileno())
      tty.setcbreak(sys.stdin.fileno())
      channel.settimeout(0.0)

      while True:
        r, w, e = select.select([channel, sys.stdin], [], [])
        if channel in r:
          try:
            x = u(channel.recv(1024))
            if len(x) == 0:
              sys.stdout.write('\r\n*** End of interactive session.\r\n')
              break
            sys.stdout.write(x)
            sys.stdout.flush()
          except socket.timeout:
            pass
        if sys.stdin in r:
          x = sys.stdin.read(1)
          if len(x) == 0:
            break
          channel.send(x)

    finally:
      termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldtty)

  def _windowsShell(self):
    import threading
  
    sys.stdout.write("Line-buffered terminal emulation. Press F6 or ^Z to send EOF.\r\n\r\n")
        
    def writeall(sock):
      while True:
        data = sock.recv(256)
        if not data:
          sys.stdout.write('\r\n*** EOF ***\r\n\r\n')
          sys.stdout.flush()
          break
        sys.stdout.write(data)
        sys.stdout.flush()
        
    writer = threading.Thread(target=writeall, args=(chan,))
    writer.start()
    try:
      while True:
        d = sys.stdin.read(1)
        if not d:
          break
        chan.send(d)
    except EOFError:
      # user hit ^Z or F6
      pass



  def _put(self, localPath, remotePath):
    client = self.getSFTP()
    return client.put(localPath, remotePath) 
       
  def _get(self, remotePath, localPath):
    client = self.getSFTP()
    return client.get(remotePath, localPath) 