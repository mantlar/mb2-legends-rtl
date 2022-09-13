# SocketTesting

from math import floor
import re
from socket import (socket, AF_INET, SOCK_STREAM, SOCK_DGRAM, SHUT_RDWR, gethostbyname_ex,
                    gaierror, timeout as socketTimeout, error as socketError)
from time import time, sleep
from os import listdir
from random import choice

class Player(object):
  def __init__(self, clientID, name, address):
    self.id = clientID
    self.name = name
    self.address = address
    self.isRtl = False
    self.isVoting = False
    self.voteNum = None
    
    


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
    team = bytes(team, "UTF-8")
    return self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam1 \"%b\"" % (self.rcon_pwd, team))
  
  def setTeam2(self, team):
    team = bytes(team, "UTF-8")
    return self._send(b"\xff\xff\xff\xffrcon %b g_siegeteam2 \"%b\"" % (self.rcon_pwd, team))
  
  def mapRestart(self, delay=0):
    """ (DEPRECATED, DO NOT USE) """
    return self._send(b"\xff\xff\xff\xffrcon %b map_restart %i" % (self.rcon_pwd, delay))
  
  def mapReload(self):
    """ USE THIS """
    currMap = self.getCurrentMap()
    return self._send(b"\xff\xff\xff\xffrcon %b map %b" % (self.rcon_pwd, currMap))

  def getCurrentMap(self):
    response = self._send(b"\xff\xff\xff\xffrcon %b mapname" % (self.rcon_pwd))
    response = response.removeprefix(b'\xff\xff\xff\xffprint\n"mapname" is:"')
    mapName = response.removesuffix(b'^7" default:"nomap^7"\n\xff\xff\xff\xffprint\n')
    return mapName

  def changeTeams(self, team1, team2):
    self.setTeam1(team1)
    self.setTeam2(team2)
    return self.mapReload()

  def status(self):
    a = self._send(b"\xff\xff\xff\xffrcon %b status" % (self.rcon_pwd))
    a = a.replace(b"print\n", b"")
    a = a.replace(b'\xff\xff\xff\xff', b"")
    a = a.split(b'\n')
    a = a[3:]     # first 3 lines are mapname, headers, and dashes so we don't care about them
    players = []
    for line in a:
      line = line.split()
      if line != []:
        newPlayerID = line[0].decode('UTF-8')
        newPlayerName = line[3].decode('UTF-8')
        newPlayerAddress = line[5].decode('UTF-8')
        newPlayer = Player(newPlayerID, newPlayerName, newPlayerAddress)
        players.append(newPlayer)
    return players

if __name__ == "__main__":
    
  test = Rcon(("192.168.1.87", 29070), "192.168.1.87", "fuckmylife")
  # print(test.mbmode(4))
  # test.clientkick(0)
  # print(test.say("^4test"))
  # currentMap = test.getCurrentMap()
  # print(currentMap)
  # test.mapReload()

  # print(test.getCurrentMap())

  teams = listdir("./teams")
  teams = [x.removesuffix(".mbtc") for x in teams]
  # team1Choice = choice(teams)
  # print("team 1: %s" % (team1Choice))
  # team2Choice = choice(teams)
  # print("team 2: %s" % (team2Choice))
  # print(test.changeTeams(team1Choice, team2Choice))
  # print(test.changeTeams("water_oldrepublicjedi", "DuelOfficeSith"))

  # print(test.getCurrentMap().decode("UTF-8"))
  print([x.name for x in test.status()])

  playerList = {}
  startVote = False
  voting = False
  currentVote = 0
  voteTimeRemaining = 60
  # get current players
  for i in test.status():
    playerList[i.id] = i
  print(playerList)
  toSeek = 0
  while(True):
    with open("C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\server.log") as log:
      log.seek(toSeek)
      for line in log.readlines():
        toSeek += len(line)
        line = re.sub('\ *(\d+:\d+) ', "", line)  # strip the timestamp from the line
        lineParse = line.split()
        if re.match('\d+:', lineParse[0]) and lineParse[3].lower() == "\"rtl\"":
          print("%s (%s) %s" % (lineParse[2], lineParse[0], lineParse[3]))
          sender = lineParse[0][:-1]
          senderName = lineParse[2][:-1]  # strip the colon off each
          if playerList[sender] and not playerList[sender].isRtl and playerList[sender].name == senderName:
            playerList[sender].isRtl = True
            test.svsay("^6[RTL]^7: %s^7 voted to change Legends teams! (%s/%d)" % (senderName, [playerList[x].isRtl for x in playerList].count(True), len(playerList)))
            if [playerList[x].isRtl for x in playerList].count(True) >= max(len(playerList) // 2, 1):
              startVote = True
              currentVote = 1
        elif re.match('\d+:', lineParse[0]) and lineParse[3].lower() == "\"unrtl\"":
          print("%s (%s) %s" % (lineParse[2], lineParse[0], lineParse[3]))
          sender = lineParse[0][:-1]
          senderName = lineParse[2][:-1]  # strip the colon off each
          if playerList[sender] and playerList[sender].isRtl and playerList[sender].name == senderName:
            playerList[sender].isRtl = False
            test.svsay("^6[RTL]^7: %s^7 no longer wants to change Legends teams!" % (senderName))
        elif re.match('\d+:', lineParse[0]) and re.match('\"\!\d\"', lineParse[3]):
          sender = lineParse[0][:-1]
          playerList[sender].voteNum = lineParse[3][2]

    if startVote and not voting:
      startVote = False
      voting = True
      test.svsay("^6[RTL]^7: Vote Initiated. Say !<num> to vote!")
      # TODO: make this smarter
      t1Choices = [choice(teams) for _ in range(5)]
      t2Choices = [choice(teams) for _ in range(5)]
      if currentVote == 1:
        test.svsay("^6[RTL]^7: Voting will complete in ^2%d^7 seconds" % (voteTimeRemaining))
        test.svsay(f"^6[RTL]^7: 1({[(playerList[x].voteNum == '1') for x in playerList].count(True)}): {t1Choices[0]}; 2({[(playerList[x].voteNum == '2') for x in playerList].count(True)}): {t1Choices[1]}; 3({[(playerList[x].voteNum == '3') for x in playerList].count(True)}): {t1Choices[2]}; 4({[(playerList[x].voteNum == '4') for x in playerList].count(True)}): {t1Choices[3]}; 5({[(playerList[x].voteNum == '5') for x in playerList].count(True)}): {t1Choices[4]}")
      elif currentVote == 2:
        test.svsay("^6[RTL]^7: Voting will complete in ^2%d^7 seconds" % (voteTimeRemaining))
        test.svsay(f"^6[RTL]^7: 1({[(playerList[x].voteNum == '1') for x in playerList].count(True)}): {t2Choices[0]}; 2({[(playerList[x].voteNum == '2') for x in playerList].count(True)}): {t2Choices[1]}; 3({[(playerList[x].voteNum == '3') for x in playerList].count(True)}): {t2Choices[2]}; 4({[(playerList[x].voteNum == '4') for x in playerList].count(True)}): {t2Choices[3]}; 5({[(playerList[x].voteNum == '5') for x in playerList].count(True)}): {t2Choices[4]}")
      voteStartTime = time()
    elif voting and voteTimeRemaining <= 0:
      if currentVote == 1:
        test.svsay("^6[RTL]^7: Voting complete!")
        test.svsay("^6[RTL]^7: Switching team 1 to %s" % (voteTimeRemaining))
        test.svsay("^6[RTL]^7: Initiating Blue Team Vote...")
        currentVote = 2
        startVote = True
      elif currentVote == 2:
        test.svsay("^6[RTL]^7: Voting complete!")
        test.svsay("^6[RTL]^7: Switching team 2 to %s" % (voteTimeRemaining))
        voting = False
    elif startVote and currentVote == 2:
      startVote = False
      voteTimeRemaining = 60
      voteStartTime
      


    elif voting and floor(time() - voteStartTime) >= 30:
      voteTimeRemaining -= floor(time() - voteStartTime)
      voteStartTime = floor(time())
      if currentVote == 1:
        test.svsay("^6[RTL]^7: Time remaining: ^2%d^7 seconds" % (voteTimeRemaining))
        test.svsay(f"^6[RTL]^7: 1({[(playerList[x].voteNum == '1') for x in playerList].count(True)}): {t1Choices[0]}; 2({[(playerList[x].voteNum == '2') for x in playerList].count(True)}): {t1Choices[1]}; 3({[(playerList[x].voteNum == '3') for x in playerList].count(True)}): {t1Choices[2]}; 4({[(playerList[x].voteNum == '4') for x in playerList].count(True)}): {t1Choices[3]}; 5({[(playerList[x].voteNum == '5') for x in playerList].count(True)}): {t1Choices[4]}")
      elif currentVote == 2:
        test.svsay("^6[RTL]^7: Time remaining: ^2%d^7 seconds" % (voteTimeRemaining))
        test.svsay(f"^6[RTL]^7: 1({[(playerList[x].voteNum == '1') for x in playerList].count(True)}): {t2Choices[0]}; 2({[(playerList[x].voteNum == '2') for x in playerList].count(True)}): {t2Choices[1]}; 3({[(playerList[x].voteNum == '3') for x in playerList].count(True)}): {t2Choices[2]}; 4({[(playerList[x].voteNum == '4') for x in playerList].count(True)}): {t2Choices[3]}; 5({[(playerList[x].voteNum == '5') for x in playerList].count(True)}): {t2Choices[4]}")
      