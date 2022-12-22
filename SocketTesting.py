# SocketTesting

from math import floor, ceil
import re
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)
from time import time, sleep
from random import choice
from zipfile import ZipFile

pk3s_to_open = ["03_MovieGameMappack.pk3", "mb2_cmp_assets3.pk3", "mb2_pb_assets2.pk3", "mb2_um_assets3.pk3", "MBAssets3.pk3"]
MB2_FOLDER_PATH = r"C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\\"
serverTips = [
  "Type '^2rtl^6' or '^2!rtl^6' in chat to vote to change the current Full Authentic teams!",
  "To search for a Full Authentic team, type '^2!searchteams <query>^6' in chat.",
  "To view a list of all Full Authentic teams, type '^2!teamlist <page>^6' in chat.",
  "To nominate a team, type '^2!nomteam <teamname> <red/blue>^6' in chat. You can only have 1 nomination for each side.",
  "This server also runs the ^2RTV^6 plugin! Type rtv or !rtv to vote to change the current map!"
]

def get_team_names():
  teams = []
  for i in pk3s_to_open:
    with ZipFile(MB2_FOLDER_PATH + i, "r") as zip:
      toExtract = []
      for name in zip.namelist():
        if name.lower().startswith("ext_data/mb2/teamconfig"):
          toExtract.append(name.removeprefix("ext_data/mb2/teamconfig/").removeprefix("Ext_Data/MB2/teamconfig/").removesuffix(".mbtc"))  # this is fine
    teams.extend(toExtract)
  teams.sort(key = lambda a: a.lower())
  return teams

MASTER_TEAM_LIST = get_team_names()
VOTE_THRESHOLD = 0.5

class Player(object):
  def __init__(self, clientID, name, address):
    self.id = clientID
    self.name = name
    self.address = address
    self.isRtl = False
    self.isVoting = False
    self.voteNum = None
    self.redNomination = None
    self.redNomIdx = None
    self.blueNomination = None
    self.blueNomIdx = None
    self.userinfo = {}
    
    
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
    self.doChangeNextRound = True
    self.changeNextRound = False
    self.nominationWinner = None

  def teamList(self, page, pageSize=25):
    payload = ""
    base = (page) * pageSize
    if base + pageSize > len(MASTER_TEAM_LIST):
      end = len(MASTER_TEAM_LIST)
    else:
      end = base + pageSize
    for i in range(base, end):
      payload += MASTER_TEAM_LIST[i]
      if i != end - 1:
        payload += ", "
    if len(payload) > 0 and page > 0:
      self.rcon.say("^6[RTL]^7: %s" % (payload))
    else:
      self.rcon.say("^6[RTL]^7: List index out of range")
    
  def searchTeams(self, query, a=None):
    query = query.lower()
    payload = ""
    for team in MASTER_TEAM_LIST:
      if query in team.lower():
        payload += team + ', '
    if len(payload) > 900:
      i = 900
      while payload[i] != ',':
        i -= 1
      payload = payload[:i]
    if len(payload) > 0:
      self.rcon.say("^6[RTL]^7: %s" % (payload))  # payload[:-2]
    else:
      self.rcon.say("^6[RTL]^7: No results found for the given query")

  def nomTeam(self, playerID, teamName, side):
    teamName = teamName.lower()
    for team in MASTER_TEAM_LIST:
      if teamName == team.lower():
        if side == "red" or side == "r":
          if len(self.t1Choices) == 5:
            self.rcon.say("^6[RTL]^7: ^1Red^7 Team nominations full!")
          elif team in self.t1Choices:
            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (team))
          elif self.playerList[playerID].redNomination != None:
            self.t1Choices[self.t1Choices.index(self.playerList[playerID].redNomination)] = team
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 changed their nomination for ^1red^7 to {team}!")
          else:
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 nominated team {team} for ^1red^7")
            self.playerList[playerID].redNomination = team
            self.t1Choices.append(team)
          return True
        elif side == "blue" or side == "b":
          if len(self.t2Choices) == 5:
            self.rcon.say("^6[RTL]^7: ^5Blue^7 Team nominations full!")
          elif team in self.t2Choices:
            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (team))
          elif self.playerList[playerID].blueNomination != None:
            self.t2Choices[self.t2Choices.index(self.playerList[playerID].blueNomination)] = team
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 changed their nomination for ^5blue^7 to {team}!")
          else:
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 nominated team {team} for ^5blue^7")
            self.playerList[playerID].blueNomination = team
            self.t2Choices.append(team)
          return True
        else:
          self.rcon.say("^6[RTL]^7: invalid team (not ^1red^7/^5blue^7)")
          return False     
    self.rcon.say("^6[RTL]^7: team name not found")
    return False
        

  def populatePlayers(self):
    """ Gets the players from the server's current status """
    playerList, currentMap = self.rcon.status()
    for i in playerList:
      self.playerList[i.id] = i
    self.currentMap = currentMap

  def refreshChoices(self):
    self.t1Choices = []
    self.t2Choices = []
    # self.t1ToSet = None
    # self.t2ToSet = None

  def parseLine(self, line):
    lineParse = line.split()
    if re.match('\d+:', lineParse[0]) and lineParse[-1].lower() == "\"rtl\"" or lineParse[-1].lower() == "\"!rtl\"":
      lineParse = line.split(':')
      sender = lineParse[0]
      senderName = lineParse[2][1:].strip()
      print("LOG: %s (client %s) voted RTL" % (senderName, sender))
      # if self.playerList[sender] and not self.playerList[sender].isRtl and self.playerList[sender].name == senderName and not self.voting:
      if self.playerList[sender]and not self.voting and not self.changeNextRound:
        if not self.playerList[sender].isRtl:
          self.playerList[sender].isRtl = True
          self.rcon.svsay("^6[RTL]^7: %s^7 wants to change Legends teams! (%s/%d)" % (senderName, [self.playerList[x].isRtl for x in self.playerList].count(True), max(ceil(len(self.playerList) * VOTE_THRESHOLD), 1)))
          if [self.playerList[x].isRtl for x in self.playerList].count(True) >= max(ceil(len(self.playerList) * VOTE_THRESHOLD), 1):
            self.startVote(1)
        else:
          self.rcon.svsay("^6[RTL]^7: %s^7 already wants to change Legends teams!" % (senderName))
    elif re.match('\d+:', lineParse[0]) and lineParse[-1].lower() == "\"unrtl\"" or lineParse[-1].lower() == "\"!unrtl\"":
      lineParse = line.split(':')
      sender = lineParse[0]
      senderName = lineParse[2][1:].strip()
      print("LOG: %s (client %s) un-voted RTL" % (senderName, sender))
      if self.playerList[sender] and self.playerList[sender].isRtl and not self.voting:
        self.playerList[sender].isRtl = False
        self.rcon.svsay("^6[RTL]^7: %s^7 no longer wants to change Legends teams!" % (senderName))
    elif re.match('\d+:', lineParse[0]) and re.match('\"\!\d\"', lineParse[-1]) and lineParse[-1] in ['"!1"', '"!2"', '"!3"', '"!4"', '"!5"'] and self.voting:
      sender = lineParse[0][:-1]
      self.playerList[sender].voteNum = lineParse[-1][2]
      self.playerList[sender].isVoting = True
    elif re.match('\d+:', lineParse[0]) and not self.voting and (lineParse[-3].strip("\"") == "!nomteam" or lineParse[-3].strip("\"") == "!teamnom" or lineParse[-3].strip("\"") == "!nominateteam" or lineParse[-3].strip("\"") == "!teamnominate"):
      lineParse = line.split(":")
      command = re.match('!nomteam (.*)', lineParse[-1][1:].strip("\"")).group().split()
      if len(command) < 3:
          print("invalid command")
      nomName = command[1]
      self.nomTeam(lineParse[0], nomName, command[2].strip("\""))
    elif re.match('\d+:', lineParse[0]) and (lineParse[-2].strip("\"") == '!teamlist' or lineParse[-2].strip("\"") == '!listeams'):
      if lineParse[-1].strip('\"').isdigit():
        self.teamList(int(lineParse[-1].strip("\"")), pageSize=50)
      else:
        self.rcon.svsay("^6[RTL]^7: Invalid page index")
    elif re.match('\d+:', lineParse[0]) and (lineParse[-2].strip("\"") == '!searchteam' or lineParse[-2].strip("\"") == '!searchteams'):
      self.searchTeams(lineParse[-1].strip("\""))
    
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
      if playerID in self.playerList:
        del self.playerList[playerID]
      else:
        print("WARNING: ATTEMPT TO REMOVE INVALID ID %s FROM DICTIONARY" % (playerID))
    elif lineParse[0] == "InitGame:":
      lineParse = line.split('\\')[1:]
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
        self.changeNextRound = False
      # lineParse = line.split('\\')
      # lineParse = lineParse[1:]
      if self.doChangeNextRound and self.changeNextRound:
        self.changeNextRound = False
        self.changeTeams(self.t1ToSet, self.t2Choices[self.nominationWinner - 1])

    elif lineParse[0] == "ClientUserinfoChanged:":
      playerID = lineParse[1]
      playerObject = self.playerList[playerID]
      vars = ['n'] + line.split('\\')[1:]   # this is hacky as shit but so is the rest of the script
      for i in range(0, len(vars), 2):
        playerObject.userinfo[vars[i]] = vars[i+1]
      if playerObject.name != playerObject.userinfo["n"]:
        print("LOG: DETECTED NAME CHANGE on client %s (from %s to %s)" % (playerID, playerObject.name, playerObject.userinfo["n"]))
        playerObject.name = playerObject.userinfo["n"]

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
    self.nominationWinner = None
    for i in self.playerList:
      self.playerList[i].redNomination = None
      self.playerList[i].blueNomination = None

  def changeTeams(self, t1, t2):
    self.t1ToSet = None
    self.t2ToSet = None
    self.rcon.svsay("^6[RTL]^7: Changing teams, please wait...")
    self.rcon.changeTeams(t1, t2, self.currentMap)
    self.populatePlayers()
    self.resetVotes()
    self.refreshChoices()

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
          line = line[7:]   # strip the timestamp from the line
          self.parseLine(line)


      if self.voting and self.voteTimeRemaining <= 0:
        votes = {
            '1': [self.playerList[x].voteNum == '1' for x in self.playerList].count(True),
            '2': [self.playerList[x].voteNum == '2' for x in self.playerList].count(True),
            '3': [self.playerList[x].voteNum == '3' for x in self.playerList].count(True),
            '4': [self.playerList[x].voteNum == '4' for x in self.playerList].count(True),
            '5': [self.playerList[x].voteNum == '5' for x in self.playerList].count(True),
          }
          
        self.nominationWinner = max(votes, key=votes.get)
        if votes[self.nominationWinner] == 0:
          self.rcon.svsay("^6[RTL]^7: Voting Failed! (No Votes Cast)")
          self.voting = False
          self.resetVotes()
          continue
        self.nominationWinner = int(self.nominationWinner)
        if self.startVote1:
          self.rcon.svsay("^6[RTL]^7: Voting complete!")
          if self.doChangeNextRound:
            self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s next round!" % (self.t1Choices[self.nominationWinner - 1]))
          else:
            self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s!" % (self.t1Choices[self.nominationWinner - 1]))
          self.t1ToSet = self.t1Choices[self.nominationWinner - 1]
          self.startVote(2)
        elif self.startVote2:
          self.voting = False
          self.rcon.svsay("^6[RTL]^7: Voting complete!")
          self.t2ToSet = self.t2Choices[self.nominationWinner - 1]
          if self.doChangeNextRound:
            self.rcon.svsay("^6[RTL]^7: Switching ^5Blue^7 Team to %s next round!" % (self.t2ToSet))
            self.changeNextRound = True
          else:
            self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s and ^5Blue^7 Team to %s!" % (self.t1ToSet, self.t2ToSet))
            self.changeTeams(self.t1ToSet, self.t2ToSet)
          
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
      # Server announcements
      if floor(time()) % 300 == 0:
        self.rcon.svsay("Tip: ^6%s" % (choice(serverTips)))
          
    
  



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
    if not type(msg) == bytes:
      msg = bytes(msg, "UTF-8")
    return self._send(b"\xff\xff\xff\xffrcon %b say %b" % (self.rcon_pwd, msg),
               2048)

  def svsay(self, msg):
    if not type(msg) == bytes:
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
  while True:
    try:
      rcon = Rcon(("192.168.1.118", 29070), "192.168.1.118", "fuckmylife")
      rtlInstance = RTL(rcon)
      rtlInstance.start()
    except KeyboardInterrupt:
      exit(2)
    except Exception as e:
      print(f"WARNING: Unexpected error occurred {e}, attempting to restart RTL...")
      rcon.say("^6[RTL]^7: Unexpected error occurred, restarting RTL...")