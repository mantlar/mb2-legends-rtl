# Rock The Legends, version 0.3
# You need to change IP_GOES_HERE in main() to the server IP

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
  "This server also runs the ^2RTV^6 plugin! Type ^2rtv^6 or ^2!rtv^6 to vote to change the current map!",
  "To get a specific map's FA teams, type '^2!mapteams <mapname>^6' in chat.",
  "RTL has a Discord! The invite code is ^23WmyjexHKC^6!"
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

class Map(object):
  def __init__(self):
    self.name = None
    self.redTeam = None
    self.blueTeam = None

def getMapTeams():
  teams = {}
  for i in pk3s_to_open:
    with ZipFile(MB2_FOLDER_PATH + i, "r") as zip:
      for name in zip.namelist():
        if name.lower().startswith("maps/"):
          newMap = Map()
          newMap.name = name[5:].removesuffix(".siege")
          side = 0
          a = zip.open(name)
          for line in a.readlines():
            line = line.decode("UTF-8", "ignore").strip()
            if line.lower().startswith("useteam"):
              if side == 0:
                side += 1
                lineParse = line.replace("\"", "").split()
                newMap.redTeam = lineParse[1]
              else:
                lineParse = line.replace("\"", "").split()
                newMap.blueTeam = lineParse[1]
      
          teams[newMap.name] = newMap
  return teams

MAP_LIST = getMapTeams()

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
  
  def resetNominations(self):
    self.redNomination = None
    self.redNomIdx = None
    self.blueNomination = None
    self.blueNomIdx = None


class RTLVote(object):
  def __init__(self):
    self.timeRemaining = None
    self.totalVoteTime = None
    self.side = None
    self.startTime = None
    self.choices = None
    self.votes = {}
    self.tieBreakerSide = None
  
  def start(self, voteTime, side, teams):
    self.timeRemaining = voteTime
    self.totalVoteTime = voteTime
    self.side = side
    self.choices = teams
    for i, _ in enumerate(teams):
      self.votes[str(i+1)] = []
    self.startTime = floor(time())

  def getVotes(self, idx):
    if type(idx) == str:  # just in case a string index is passed
      idx = int(idx)
    if 0 <= idx <= 5:
      return self.votes[str(idx)]


class RTL(object):
  def __init__(self, rconObject, voteTime=None):
    self.rcon: Rcon = rconObject
    self.t1Noms = []
    self.t2Noms = []
    self.t1ToSet = None
    self.t2ToSet = None
    self.currentVote = None    
    self.voteTime = voteTime if voteTime else 60
    self.toSeek = 0   # place to seek to when reading log file, done so we only read new lines
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
    
  def searchTeams(self, query):
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
      # do mapTeams if no team was found, because people sometimes use searchteams as mapteams
      mapCheck = self.mapTeams(query, quiet=True)
      if not mapCheck:
        self.rcon.say("^6[RTL]^7: No results found for the given query")

  def nomTeam(self, playerID, teamName, side):
    teamName = teamName.lower()
    for team in MASTER_TEAM_LIST:
      if teamName == team.lower():
        if side == "red" or side == "r":
          if len(self.t1Noms) == 5:
            self.rcon.say("^6[RTL]^7: ^1Red^7 Team nominations full!")
          elif team in self.t1Noms:
            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (team))
          elif self.playerList[playerID].redNomination != None:
            self.t1Noms[self.t1Noms.index(self.playerList[playerID].redNomination)] = team
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 changed their nomination for ^1red^7 to {team}!")
          else:
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 nominated team {team} for ^1red^7")
            self.playerList[playerID].redNomination = team
            self.t1Noms.append(team)
          return True
        elif side == "blue" or side == "b":
          if len(self.t2Noms) == 5:
            self.rcon.say("^6[RTL]^7: ^5Blue^7 Team nominations full!")
          elif team in self.t2Noms:
            self.rcon.say("^6[RTL]^7: Team already nominated: %s" % (team))
          elif self.playerList[playerID].blueNomination != None:
            self.t2Noms[self.t2Noms.index(self.playerList[playerID].blueNomination)] = team
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 changed their nomination for ^5blue^7 to {team}!")
          else:
            self.rcon.say(f"^6[RTL]^7: {self.playerList[playerID].name}^7 nominated team {team} for ^5blue^7")
            self.playerList[playerID].blueNomination = team
            self.t2Noms.append(team)
          return True
        else:
          self.rcon.say("^6[RTL]^7: invalid team (not ^1red^7/^5blue^7)")
          return False     
    self.rcon.say("^6[RTL]^7: team name not found")
    return False
        

  def mapTeams(self, mapName, quiet=False):
    for i in MAP_LIST:
      if i.lower() == mapName.lower():
        self.rcon.say("^6[RTL]^7: %s: ^1Red^7=%s; ^5Blue^7=%s" % (i, MAP_LIST[i].redTeam, MAP_LIST[i].blueTeam))
        return True
    if not quiet:
      self.rcon.say("^6[RTL]^7: map not found")
    return False


  def populatePlayers(self):
    """ Gets the players from the server's current status """
    playerList, currentMap = self.rcon.status()
    for i in playerList:
      self.playerList[i.id] = i
    self.currentMap = currentMap

  def refreshChoices(self):
    self.t1Noms = []
    self.t2Noms = []
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
      if self.playerList[sender] and self.currentVote == None and not self.changeNextRound:
        if not self.playerList[sender].isRtl:
          self.playerList[sender].isRtl = True
          self.rcon.svsay("^6[RTL]^7: %s^7 wants to change Legends teams! (%s/%d)" % (senderName, [self.playerList[x].isRtl for x in self.playerList].count(True), max(ceil(len(self.playerList) * VOTE_THRESHOLD), 1)))
          if [self.playerList[x].isRtl for x in self.playerList].count(True) >= max(ceil(len(self.playerList) * VOTE_THRESHOLD), 1):
            self.startVote("red")
        else:
          self.rcon.svsay("^6[RTL]^7: %s^7 already wants to change Legends teams!" % (senderName))
    elif re.match('\d+:', lineParse[0]) and lineParse[-1].lower() == "\"unrtl\"" or lineParse[-1].lower() == "\"!unrtl\"":
      lineParse = line.split(':')
      sender = lineParse[0]
      senderName = lineParse[2][1:].strip()
      print("LOG: %s (client %s) un-voted RTL" % (senderName, sender))
      if self.playerList[sender] and self.playerList[sender].isRtl and self.currentVote == None:
        self.playerList[sender].isRtl = False
        self.rcon.svsay("^6[RTL]^7: %s^7 no longer wants to change Legends teams!" % (senderName))
    elif re.match('\d+:', lineParse[0]) and re.match('\"\!\d\"', lineParse[-1]) and lineParse[-1] in ['"!1"', '"!2"', '"!3"', '"!4"', '"!5"', '"!6"'] and self.currentVote:
      sender = lineParse[0][:-1]
      voteNum = lineParse[-1][2]
      if int(voteNum) <= len(self.currentVote.choices):
        if self.playerList[sender].voteNum != None:
          self.currentVote.votes[self.playerList[sender].voteNum].remove(sender)
        self.playerList[sender].voteNum = voteNum
        self.playerList[sender].isVoting = True
        self.currentVote.votes[voteNum].append(sender)
    elif re.match('\d+:', lineParse[0]) and self.currentVote == None and (lineParse[-3].strip("\"") == "!nomteam" or lineParse[-3].strip("\"") == "!teamnom" or lineParse[-3].strip("\"") == "!nominateteam" or lineParse[-3].strip("\"") == "!teamnominate"):
      lineParse = line.split(":")
      command = re.match('!nomteam (.*)', lineParse[-1][1:].strip("\"")).group().split()
      if len(command) < 3:
          print("invalid command")
      nomName = command[1]
      self.nomTeam(lineParse[0], nomName, command[2].strip("\""))
    elif re.match('\d+:', lineParse[0]) and (lineParse[-2].strip("\"") == '!teamlist' or lineParse[-2].strip("\"") == '!listteams'):
      if lineParse[-1].strip('\"').isdigit():
        self.teamList(int(lineParse[-1].strip("\"")), pageSize=50)
      else:
        self.rcon.svsay("^6[RTL]^7: Invalid page index")
    elif re.match('\d+:', lineParse[0]) and (lineParse[-2].strip("\"") == '!searchteam' or lineParse[-2].strip("\"") == '!searchteams'):
      self.searchTeams(lineParse[-1].strip("\""))
    elif re.match('\d+:', lineParse[0]) and (lineParse[-2].strip("\"") == '!mapteams' or lineParse[-2].strip("\"") == '!mapteam'):
      self.mapTeams(lineParse[-1].strip("\""))
    
    elif lineParse[0] == "ClientConnect:":
      regex = re.escape(line)
      regex = re.findall('\\(.*?\\)', line)
      playerName = regex[0][1:-1].strip()
      playerIP = regex[1][5:-1]
      playerID = re.search('ID: \d+', line).group()[4:]
      # oldName = self.playerList[playerID].name
      # oldIP = self.playerList[playerID].address
      if not playerID in self.playerList:
        print("LOG: %s connected with id %s" % (playerName, playerID))
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
        if self.currentVote and self.playerList[playerID].voteNum:
          self.currentVote.votes[self.playerList[playerID].voteNum].remove(playerID)
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
        self.currentVote = None
        self.changeNextRound = False
      # lineParse = line.split('\\')
      # lineParse = lineParse[1:]
      if self.doChangeNextRound and self.changeNextRound:
        self.changeNextRound = False
        self.changeTeams(self.t1ToSet, self.t2ToSet)

    elif lineParse[0] == "ClientUserinfoChanged:":
      playerID = lineParse[1]
      playerObject = self.playerList[playerID]
      vars = ['n'] + line.split('\\')[1:]   # this is hacky as shit but so is the rest of the script
      for i in range(0, len(vars), 2):
        playerObject.userinfo[vars[i]] = vars[i+1]
      if playerObject.name != playerObject.userinfo["n"]:
        print("LOG: DETECTED NAME CHANGE on client %s (from %s to %s)" % (playerID, playerObject.name, playerObject.userinfo["n"]))
        playerObject.name = playerObject.userinfo["n"]

  def startVote(self, side, choices=None):
    # reset the players' voting flags
    for i in self.playerList:
      self.playerList[i].isRtl = False
      self.playerList[i].isVoting = False
      self.playerList[i].voteNum = None
    # fill in remaining team options
    while len(self.t1Noms) < 5:
      newTeam = choice(MASTER_TEAM_LIST)
      if not newTeam in self.t1Noms and not newTeam in self.t2Noms:
        self.t1Noms.append(newTeam)
    while len(self.t2Noms) < 5:
      newTeam = choice(MASTER_TEAM_LIST)
      if not newTeam in self.t2Noms and not newTeam in self.t1Noms:
        self.t2Noms.append(newTeam)

    newVote = RTLVote()

    if choices != None:
      newVote.tieBreakerSide = side
      newVote.start(self.voteTime // 2, side, choices)
    elif side == "red":
      self.rcon.svsay("^6[RTL]^7: Initiating ^1Red^7 Team Vote... (Say !<num> to vote)")
      newVote.start(self.voteTime, "red", self.t1Noms + ["Don't change"])
    elif side == "blue":
      self.rcon.svsay("^6[RTL]^7: Initiating ^5Blue^7 Team Vote... (Say !<num> to vote)")
      newVote.start(self.voteTime, "blue", self.t2Noms + ["Don't change"])
    # newVote.voteTimeRemaining = self.voteTime
    # newVote.voteStartTime = floor(time())
    self.currentVote = newVote
    choiceString = ""
    for i, v in enumerate(newVote.choices):
      choiceString += f"{i+1}(0): {newVote.choices[i]}; "
    choiceString = choiceString[:-2]
    self.rcon.svsay("^6[RTL]^7: Voting will complete in ^2%d^7 seconds" % (newVote.timeRemaining))
    self.rcon.svsay(f"^6[RTL]^7: {choiceString}")

  def displayVotes(self):
    self.rcon.svsay("^6[RTL]^7: Time remaining: ^2%d^7 seconds" % (self.currentVote.timeRemaining))
    votes = self.currentVote.votes
    choiceString = ""
    for i, v in enumerate(self.currentVote.choices):
      choiceString += f"{i+1}({len(votes[str(i+1)])}): {self.currentVote.choices[i]}; "
    choiceString = choiceString[:-2]
    self.rcon.svsay(f"^6[RTL]^7: {choiceString}")

  def resetVotes(self):
    self.nominationWinner = None
    for i in self.playerList:
      self.playerList[i].resetNominations()

  def changeTeams(self, t1, t2):
    if self.currentTeam1 == self.t1ToSet and self.currentTeam2 == self.t2ToSet:
      self.t1ToSet = None
      self.t2ToSet = None
      self.rcon.svsay("^6[RTL]^7: Teams remain unchanged! (voting reset)")
      self.populatePlayers()
      self.resetVotes()
      self.refreshChoices()
      return None
    self.currentTeam1 = self.t1ToSet
    self.currentTeam2 = self.t2ToSet
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
    self.currentTeam1 = self.rcon.getTeam1()
    self.currentTeam2 = self.rcon.getTeam2()
    self.rcon.say("^6[RTL]^7: Rock The Legends initialized! Have fun!")
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


      if self.currentVote and self.currentVote.timeRemaining <= 0:
        votes = self.currentVote.votes
        winners = []
        voteMax = max(votes, key=lambda i: len(votes[i]))
        for i in votes:
          if len(votes[i]) == len(votes[voteMax]):
            winners.append(i)
        if len(votes[voteMax]) == 0:
          self.rcon.svsay("^6[RTL]^7: Voting Failed! (No Votes Cast)")
          self.currentVote = None
          self.resetVotes()
          self.refreshChoices()
          continue
        else:
          # just choose randomly if the tiebreaker results in a tie
          if self.currentVote.tieBreakerSide != None and len(winners) > 1:
            winners = [choice(winners)]
          if len(winners) == 1:
            self.nominationWinner = int(winners[0])
            self.rcon.svsay("^6[RTL]^7: Voting complete!")
            if self.currentVote.side == "red":
              teamToChange = self.currentVote.choices[self.nominationWinner - 1]
              if teamToChange == "Don't change":
                teamToChange = self.currentTeam1
              if self.doChangeNextRound:
                if teamToChange == self.currentTeam1:
                  self.rcon.svsay("^6[RTL]^7: Keeping ^1Red^7 Team on %s next round!" % (teamToChange))
                else:
                  self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s next round!" % (teamToChange))
              else:
                if teamToChange == self.currentTeam1:
                  self.rcon.svsay("^6[RTL]^7: Keeping ^1Red^7 Team on %s!" % (teamToChange))
                else:
                  self.rcon.svsay("^6[RTL]^7: Switching ^1Red^7 Team to %s!" % (teamToChange))
              self.t1ToSet = teamToChange
              self.startVote("blue")
            elif self.currentVote.side == "blue":
              teamToChange = self.currentVote.choices[self.nominationWinner - 1]
              self.currentVote = None
              if teamToChange == "Don't change":
                teamToChange = self.currentTeam2
              self.t2ToSet = teamToChange
              if self.doChangeNextRound:
                if teamToChange == self.currentTeam2:
                  self.rcon.svsay("^6[RTL]^7: Keeping ^5Blue^7 Team on %s next round!" % (teamToChange))
                else:
                  self.rcon.svsay("^6[RTL]^7: Switching ^5Blue^7 Team to %s next round!" % (teamToChange))
                self.changeNextRound = True
              else:
                if teamToChange == self.currentTeam2:
                  self.rcon.svsay("^6[RTL]^7: Keeping ^5Blue^7 Team on %s!" % (teamToChange))
                else:
                  self.rcon.svsay("^6[RTL]^7: Switching ^5Blue^7 Team to %s!" % (teamToChange))
                self.changeTeams(self.t1ToSet, self.t2ToSet)
          else:
            self.rcon.svsay("^6[RTL]^7: Tie detected! Beginning a new round of voting...")
            winnerTeams = []
            for i in winners:
              i = int(i)
              winnerTeams.append(self.currentVote.choices[i-1])
            self.startVote(self.currentVote.side, winnerTeams)
          
              
      elif self.currentVote and self.currentVote.timeRemaining % (self.voteTime // 2) == 0 and self.currentVote.timeRemaining != self.voteTime and self.currentVote.timeRemaining != 0:
        self.displayVotes()
      if self.currentVote:
        if self.currentVote.tieBreakerSide != None:
          self.currentVote.timeRemaining = (self.voteTime // 2) - floor(time() - self.currentVote.startTime)
        else:
          self.currentVote.timeRemaining = self.voteTime - floor(time() - self.currentVote.startTime)
        if all([self.playerList[x].isVoting for x in self.playerList]):
          self.currentVote.timeRemaining = 0


      # Server announcements
      if floor(time()) % 300 == 0:      # display a tip every 5 minutes, or about once a round
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

  def getTeam1(self):
    response = self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam1" % (self.rcon_pwd))
    response = response.decode("UTF-8", "ignore")
    response = response.removeprefix("print\n\"g_siegeTeam1\" is:")
    response = response.split('"')[1][:-2]
    return response

  def getTeam2(self):
    response = self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam2" % (self.rcon_pwd))
    response = response.decode("UTF-8", "ignore")
    response = response.removeprefix("print\n\"g_siegeTeam2\" is:")
    response = response.split('"')[1][:-2]
    return response
  
  def _mapRestart(self, delay=0):
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
        newPlayerName = newPlayerName.decode('UTF-8', "ignore")[:-1].strip()
        newPlayerAddress = lineSplit[-3].decode('UTF-8')  
        newPlayer = Player(newPlayerID, newPlayerName, newPlayerAddress)
        players.append(newPlayer)
    return players, currentMap


if __name__ == "__main__":
  while True:
    try:
      rcon = Rcon(("192.168.50.1", 29070), "192.168.50.1", "fuckmylife")
      rtlInstance = RTL(rcon, voteTime=120)
      rtlInstance.start()
    except KeyboardInterrupt:
      exit(2)
    except Exception as e:
      print(f"WARNING: Unexpected error occurred {e}, attempting to restart RTL...")
      rcon.say("^6[RTL]^7: Unexpected error occurred, restarting RTL...")
    # rcon = Rcon(("192.168.1.118", 29070), "192.168.1.118", "fuckmylife")
    # rtlInstance = RTL(rcon, voteTime=120)
    # rtlInstance.start()