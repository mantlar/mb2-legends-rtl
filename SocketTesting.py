# SocketTesting

from math import floor, ceil
from operator import indexOf
import re
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)
from time import time, sleep
from os import listdir
from random import choice

MASTER_TEAM_LIST = listdir("./teams")
MASTER_TEAM_LIST = [x.removesuffix(".mbtc") for x in MASTER_TEAM_LIST]

class Player(object):
  def __init__(self, clientID, name, address):
    self.id = clientID
    self.name = name
    self.address = address
    self.isRtl = False
    self.isVoting = False
    self.voteNum = None
    self.redNomination = None
    self.blueNomination = None
    
    
class RTL(object):
  def __init__(self, rconObject, voteTime=None):
    self.rcon: Rcon = rconObject
    self.t1Choices = []
    self.t2Choices = []
    self.t1ToSet = None
    self.t2ToSet = None
    self.startVote1 = False
    self.startVote2 = False
    self.voting = False
    self.votes = {'0': [], '1': [], '2': [], '3': [], '4': [], '5': []}
    self.voteTime = voteTime if voteTime else 60
    self.toSeek = 0   # place to seek to when reading log file, done so we only read new lines
    self.voteStartTime = 0
    self.voteTimeRemaining = 0
    self.playerList = {}
    self.currentMap = None

  def populatePlayers(self):
    """ Gets the players from the server's current status """
    playerList, currentMap = self.rcon.status()
    for i in playerList:
      self.playerList[i.id] = i
    self.currentMap = currentMap

  def refreshChoices(self):
    self.t1Choices = []
    self.t2Choices = []
    self.t1ToSet = None
    self.t2ToSet = None

  def startVote(self, team):
    # reset the players' voting flags
    for i in self.playerList:
      self.playerList[i].isRtl = False
      self.playerList[i].isVoting = False
      self.playerList[i].voteNum = None
    # fill in remaining team options
    while len(self.t1Choices) < 5:
      newTeam = choice(MASTER_TEAM_LIST)
      if not newTeam in self.t1Choices:
        self.t1Choices.append(newTeam)
    while len(self.t2Choices) < 5:
      newTeam = choice(MASTER_TEAM_LIST)
      if not newTeam in self.t2Choices:
        self.t2Choices.append(newTeam)
    if team == 1:
      self.rcon.svsay("^6[RTL]^7: Initiating ^1Red^7 Team Vote... (Say !<num> to vote)")
      self.rcon.svsay("^6[RTL]^7: Voting will complete in ^2%d^7 seconds" % (self.voteTime))
      self.rcon.svsay(f"^6[RTL]^7: 1({[(self.playerList[x].voteNum == '1') for x in self.playerList].count(True)}): {self.t1Choices[0]}; 2({[(self.playerList[x].voteNum == '2') for x in self.playerList].count(True)}): {self.t1Choices[1]}; 3({[(self.playerList[x].voteNum == '3') for x in self.playerList].count(True)}): {self.t1Choices[2]}; 4({[(self.playerList[x].voteNum == '4') for x in self.playerList].count(True)}): {self.t1Choices[3]}; 5({[(self.playerList[x].voteNum == '5') for x in self.playerList].count(True)}): {self.t1Choices[4]}")
      self.startVote2 = False
      self.startVote1 = True
    elif team == 2:
      self.rcon.svsay("^6[RTL]^7: Initiating ^5Blue^7 Team Vote... (Say !<num> to vote)")
      self.rcon.svsay("^6[RTL]^7: Voting will complete in ^2%d^7 seconds" % (self.voteTime))
      self.rcon.svsay(f"^6[RTL]^7: 1({[(self.playerList[x].voteNum == '1') for x in self.playerList].count(True)}): {self.t2Choices[0]}; 2({[(self.playerList[x].voteNum == '2') for x in self.playerList].count(True)}): {self.t2Choices[1]}; 3({[(self.playerList[x].voteNum == '3') for x in self.playerList].count(True)}): {self.t2Choices[2]}; 4({[(self.playerList[x].voteNum == '4') for x in self.playerList].count(True)}): {self.t2Choices[3]}; 5({[(self.playerList[x].voteNum == '5') for x in self.playerList].count(True)}): {self.t2Choices[4]}")
      self.startVote1 = False
      self.startVote2 = True
    self.voteTimeRemaining = self.voteTime
    self.voteStartTime = floor(time())
    self.voting = True

  def displayVotes(self, team):
    if team == 1:
      self.rcon.svsay("^6[RTL]^7: Time remaining: ^2%d^7 seconds" % (self.voteTimeRemaining))
      self.rcon.svsay(f"^6[RTL]^7: 1({[(self.playerList[x].voteNum == '1') for x in self.playerList].count(True)}): {self.t1Choices[0]}; 2({[(self.playerList[x].voteNum == '2') for x in self.playerList].count(True)}): {self.t1Choices[1]}; 3({[(self.playerList[x].voteNum == '3') for x in self.playerList].count(True)}): {self.t1Choices[2]}; 4({[(self.playerList[x].voteNum == '4') for x in self.playerList].count(True)}): {self.t1Choices[3]}; 5({[(self.playerList[x].voteNum == '5') for x in self.playerList].count(True)}): {self.t1Choices[4]}")
    elif team == 2:
      self.rcon.svsay("^6[RTL]^7: Time remaining: ^2%d^7 seconds" % (self.voteTimeRemaining))
      self.rcon.svsay(f"^6[RTL]^7: 1({[(self.playerList[x].voteNum == '1') for x in self.playerList].count(True)}): {self.t2Choices[0]}; 2({[(self.playerList[x].voteNum == '2') for x in self.playerList].count(True)}): {self.t2Choices[1]}; 3({[(self.playerList[x].voteNum == '3') for x in self.playerList].count(True)}): {self.t2Choices[2]}; 4({[(self.playerList[x].voteNum == '4') for x in self.playerList].count(True)}): {self.t2Choices[3]}; 5({[(self.playerList[x].voteNum == '5') for x in self.playerList].count(True)}): {self.t2Choices[4]}")
      

  def resetVotes(self):
    self.votes = {'0': [], '1': [], '2': [], '3': [], '4': [], '5': []}


  def start(self):
    self.rcon.say("^6[RTL]^7: Initializing Rock The Legends...")
    self.populatePlayers()
    self.resetVotes()
    self.refreshChoices()
    # self.currentMap = self.rcon.getCurrentMap()
    # ignore existing log lines
    with open("C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\server.log") as log:
      for line in log.readlines():
          self.toSeek += len(line)
    while True:
      with open("C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\server.log") as log:
        log.seek(self.toSeek)
        for line in log.readlines():
          self.toSeek += len(line)
          line = re.sub('\ *(\d+:\d+) ', "", line)  # strip the timestamp from the line
          lineParse = line.split()
          if re.match('\d+:', lineParse[0]) and lineParse[-1].lower() == "\"rtl\"":
            lineParse = line.split(':')
            sender = lineParse[0]
            senderName = lineParse[2][1:].strip()
            print("LOG: %s (client %s) voted RTL" % (senderName, sender))
            if self.playerList[sender] and not self.playerList[sender].isRtl and self.playerList[sender].name == senderName and not self.voting:
              self.playerList[sender].isRtl = True
              self.rcon.svsay("^6[RTL]^7: %s^7 wants to change Legends teams! (%s/%d)" % (senderName, [self.playerList[x].isRtl for x in self.playerList].count(True), max(ceil(len(self.playerList) * 2/3), 1)))
              if [self.playerList[x].isRtl for x in self.playerList].count(True) >= max(ceil(len(self.playerList) * 2/3), 1):
                self.startVote(1)
          elif re.match('\d+:', lineParse[0]) and lineParse[-1].lower() == "\"unrtl\"":
            lineParse = line.split(':')
            sender = lineParse[0]
            senderName = lineParse[2][1:].strip()
            print("LOG: %s (client %s) un-voted RTL" % (senderName, sender))
            if self.playerList[sender] and self.playerList[sender].isRtl and self.playerList[sender].name == senderName:
              self.playerList[sender].isRtl = False
              self.rcon.svsay("^6[RTL]^7: %s^7 no longer wants to change Legends teams!" % (senderName))
          elif re.match('\d+:', lineParse[0]) and re.match('\"\!\d\"', lineParse[-1]) and lineParse[-1] in ['"!1"', '"!2"', '"!3"', '"!4"', '"!5"'] and self.voting:
            sender = lineParse[0][:-1]
            self.playerList[sender].voteNum = lineParse[-1][2]
            self.playerList[sender].isVoting = True
          elif re.match('\d+:', lineParse[0]) and re.match('!nominate', lineParse[-3].strip("\"")):
            lineParse = line.split(":")
            command = re.match('!nominate (.*)', lineParse[-1][1:].strip("\"")).group().split()
            if len(command) < 3:
                print("invalid command")
            elif command[1] in MASTER_TEAM_LIST:
                nomName = command[1]
                if nomName in MASTER_TEAM_LIST:
                    nomTeam = command[2].strip("\"")
                    if nomTeam == "red":
                        if len(self.t1Choices) == 5:
                            self.rcon.say("^6[RTL]^7: ^1Red^7 Team nominations full!")
                        elif nomName in self.t1Choices:
                            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (nomName))
                        elif self.playerList[lineParse[0]].redNomination != None:
                            self.rcon.say("^6[RTL]^7: User already nominated team: %s" % (self.playerList[lineParse[0]].redNomination))
                        else:
                            self.rcon.say(f"^6[RTL]^7: {self.playerList[lineParse[0]].name}^7 nominated team {nomName} for red")
                            self.playerList[lineParse[0]].redNomination = nomName
                            self.t1Choices.append(nomName)
                    elif nomTeam == "blue":
                        if len(self.t2Choices) == 5:
                            self.rcon.say("^6[RTL]^7: ^5Blue^7 Team nominations full!")
                        elif nomName in self.t2Choices:
                            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (nomName))
                        elif self.playerList[lineParse[0]].blueNomination != None:
                            self.rcon.say("^6[RTL]^7: User already nominated team: %s" % (self.playerList[lineParse[0]].blueNomination))
                        else:
                            self.rcon.say(f"^6[RTL]^7: {self.playerList[lineParse[0]].name}^7 nominated team {nomName} for blue")
                            self.playerList[lineParse[0]].blueNomination = nomName
                            self.t2Choices.append(nomName)
                    else:
                        self.rcon.say("^6[RTL]^7: invalid team (not red/blue)")
                else:
                    self.rcon.say("^6[RTL]^7: invalid team name: %s" % (nomName))
            else:
                self.rcon.say("^6[RTL]^7: team name not found")
          
          elif lineParse[0] == "ClientConnect:":
            regex = re.escape(line)
            regex = re.findall('\\(.*?\\)', line)
            playerName = regex[0][1:-1].strip()
            playerIP = regex[1][5:-1]
            playerID = re.search('ID: \d+', line).group()[4:]
            # oldName = self.playerList[playerID].name
            # oldIP = self.playerList[playerID].address
            print("LOG: %s connected with id %s" % (playerName, playerID))
            if not playerID in self.playerList:
              self.playerList[playerID] = Player(playerID, playerName, playerIP)
            elif self.playerList[playerID].name != playerName and len(playerName) > 15 and playerName.startswith(self.playerList[playerID].name):
              print("LOG: DETECTED LONG NAME %s" % (playerName))
              self.playerList[playerID].name = playerName
            elif self.playerList[playerID].name != playerName:
              # print("WARNING: TWO USERS WERE ASSIGNED ID %s (%s and %s), IGNORING %s'S COMMANDS" % (playerID, self.playerList[playerID].name, playerName, playerName))
              print("WARNING: %s and %s were both assigned ID %s, overwriting dict item with %s's data" % (self.playerList[playerID].name, playerName, playerID, playerName))
              self.playerList[playerID].name = playerName
              self.playerList[playerID].address = playerIP
          elif lineParse[0] == "ClientDisconnect:":
            playerID = lineParse[1]
            print("LOG: Player with ID %s disconnected" % (playerID))
            if self.playerList[playerID]:
              del self.playerList[playerID]
            else:
              print("WARNING: ATTEMPT TO REMOVE INVALID ID %s FROM DICTIONARY" % (playerID))
          elif lineParse[0] == "InitGame:":
            lineParse = line.split('\\')
            lineParse = lineParse[1:]
            if not 'mapname' in lineParse:
              currentMap = self.rcon.getCurrentMap()
            else:
              currentMap = lineParse[lineParse.index("mapname") + 1].encode()
            if currentMap != self.currentMap:   # Non-RTL map change detected
              print("Non-RTL map change detected: %s" % (currentMap))
              self.currentMap = currentMap
              self.populatePlayers()
              self.resetVotes()
              self.refreshChoices()
              self.voting = False


      if self.voting and self.voteTimeRemaining <= 0:
        votes = {
            '1': [self.playerList[x].voteNum == '1' for x in self.playerList].count(True),
            '2': [self.playerList[x].voteNum == '2' for x in self.playerList].count(True),
            '3': [self.playerList[x].voteNum == '3' for x in self.playerList].count(True),
            '4': [self.playerList[x].voteNum == '4' for x in self.playerList].count(True),
            '5': [self.playerList[x].voteNum == '5' for x in self.playerList].count(True),
          }
        winner = max(votes, key=votes.get)
        if votes[winner] == 0:
          self.rcon.svsay("^6[RTL]^7: Voting Failed! (No Votes Cast)")
          self.voting = False
          self.resetVotes()
          continue
        winner = int(winner)
        if self.startVote1:
          self.rcon.svsay("^6[RTL]^7: Voting complete!")
          self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s" % (self.t1Choices[winner - 1]))
          self.t1ToSet = self.t1Choices[winner - 1]
          self.startVote(2)
        elif self.startVote2:
          self.voting = False
          self.rcon.svsay("^6[RTL]^7: Voting complete!")
          self.rcon.svsay("^6[RTL]^7: Switching ^5Blue^7 Team to %s" % (self.t2Choices[winner - 1]))
          self.rcon.changeTeams(self.t1ToSet, self.t2Choices[winner - 1], self.currentMap)
          self.populatePlayers()
          self.resetVotes()
          self.refreshChoices()
      elif self.voting and self.voteTimeRemaining % 30 == 0 and self.voteTimeRemaining != self.voteTime and self.voteTimeRemaining != 0:
        # self.voteStartTime = floor(time())
        if self.voting and self.startVote1:
          self.displayVotes(1)
        elif self.voting and self.startVote2:
          self.displayVotes(2)
      if self.voting:
        self.voteTimeRemaining = self.voteTime - floor(time() - self.voteStartTime)
        if all([self.playerList[x].isVoting for x in self.playerList]):
          self.voteTimeRemaining = 0
      
          
    
  



class Rcon(object):
  """Send commands to the server via rcon. Wrapper class."""
  def __init__(self, address, bindaddr, rcon_pwd):
    self.address = address
    self.bindaddr = bindaddr
    self.rcon_pwd = bytes(rcon_pwd, "UTF-8")


  def _send(self, payload, buffer_size=1024): # This method shouldn't be used outside the scope of this object's
                                              # wrappers.
    sock = socket(AF_INET, SOCK_DGRAM) # Socket descriptor sending/receiving rcon commands to/from the server.
    sock.bind((self.bindaddr, 0)) # Setting port as 0 will let the OS pick an available port for us.
    sock.settimeout(1)
    sock.connect(self.address)
    send = sock.send
    recv = sock.recv
    while(True): # Make sure an infinite loop is placed until
                 # the command is successfully received.
      try:
        # payload = payload.encode()
        # startTime = time()
        send(payload)
        a = b''
        while(True):
          try:
            a += recv(buffer_size)
          except socketTimeout:
            break
          
        # endTime = time() - startTime
        # print(endTime)
        # print(a)
        break

      except socketTimeout:
        # print("socket timeout")
        continue

      except socketError:
        print("socket error")
        break

    sock.shutdown(SHUT_RDWR)
    sock.close()
    return a

  def say(self, msg):
    msg = bytes(msg, "UTF-8")
    return self._send(b"\xff\xff\xff\xffrcon %b say %b" % (self.rcon_pwd, msg),
               2048)

  def svsay(self, msg):
    msg = bytes(msg, "UTF-8")
    if len(msg) > 141: # Message is too big for "svsay".
                       # Use "say" instead.
      return self.say(msg)

    else:
      return self._send(b"\xff\xff\xff\xffrcon %b svsay %b" % (self.rcon_pwd, msg))

  def mbmode(self, cmd):
    return self._send(b"\xff\xff\xff\xffrcon %b mbmode %i" % (self.rcon_pwd, cmd))

  def clientkick(self, player_id):
    return self._send(b"\xff\xff\xff\xffrcon %b clientkick %i" % (self.rcon_pwd, player_id))
  
  def echo(self, msg):
    msg = bytes(msg, "UTF-8")
    return self._send(b"\xff\xff\xff\xffrcon %b echo %b" % (self.rcon_pwd, msg))

  def setTeam1(self, team):
    team = team.encode()
    return self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam1 \"%b\"" % (self.rcon_pwd, team))
  
  def setTeam2(self, team):
    team = team.encode()
    return self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam2 \"%b\"" % (self.rcon_pwd, team))
  
  def mapRestart(self, delay=0):
    """ (DEPRECATED, DO NOT USE) """
    return self._send(b"\xff\xff\xff\xffrcon %b map_restart %i" % (self.rcon_pwd, delay))
  
  def mapReload(self, mapName):
    """ USE THIS """
    currMap = mapName
    return self._send(b"\xff\xff\xff\xffrcon %b map %b" % (self.rcon_pwd, currMap))

  def getCurrentMap(self):
    response = self._send(b"\xff\xff\xff\xffrcon %b mapname" % (self.rcon_pwd))
    response = response.removeprefix(b'\xff\xff\xff\xffprint\n"mapname" is:"')
    mapName = response.removesuffix(b'^7" default:"nomap^7"\n\xff\xff\xff\xffprint\n')
    return mapName

  def changeTeams(self, team1, team2, mapName):
    self.setTeam1(team1)
    self.setTeam2(team2)
    return self.mapReload(mapName)

  def status(self):
    a = self._send(b"\xff\xff\xff\xffrcon %b status" % (self.rcon_pwd))
    a = a.replace(b"print\n", b"")
    a = a.replace(b'\xff\xff\xff\xff', b"")
    a = a.split(b'\n')
    currentMap = a[0][5:]
    a = a[3:]     # first 3 lines are mapname, headers, and dashes so we don't care about them
    players = []
    for line in a:
      lineSplit = line.split()
      if lineSplit != []:
        newPlayerID = lineSplit[0].decode('UTF-8')
        newPlayerName = b''.join([x + b' ' for x in lineSplit[3:-4]])
        newPlayerName = newPlayerName.decode('UTF-8')[:-1].strip()
        newPlayerAddress = lineSplit[-3].decode('UTF-8')  
        newPlayer = Player(newPlayerID, newPlayerName, newPlayerAddress)
        players.append(newPlayer)
    return players, currentMap

if __name__ == "__main__":
  rcon = Rcon(("192.168.1.87", 29070), "192.168.1.87", "fuckmylife")
  rtlInstance = RTL(rcon)
  rtlInstance.start()