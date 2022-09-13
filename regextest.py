import re
from SocketTesting import MASTER_TEAM_LIST
from random import choice, randint

t1Choices = [choice(MASTER_TEAM_LIST) for _ in range(5)]
t2Choices = [choice(MASTER_TEAM_LIST) for _ in range(5)]
t1Noms = []
t2Noms = []
validSides = ["red", "blue"]
while(True):
    lineParse = f"0: say: ^2ACHUTA:\"!nominate us_heroes {choice(validSides)}\"".split(":")
    a = re.match('!nominate (.*)', lineParse[-1].strip("\""))
    command = a.group().split()
    if len(command) < 3:
        print("invalid command")
    elif command[1] in MASTER_TEAM_LIST:
        nomName = command[1]
        if nomName in MASTER_TEAM_LIST:
            nomTeam = command[2]
            if nomTeam == "red":
                if len(t1Noms) == 5:
                    print("t1Noms full!")
                elif nomName in t1Noms:
                    print("team already nominated: %s" % (nomName))
                else:
                    t1Noms.append(nomName)
                    t1Choices[len(t1Noms) - 1] = nomName
            elif nomTeam == "blue":
                if len(t2Noms) == 5:
                    print("t2Noms full!")
                elif nomName in t2Noms:
                    print("team already nominated: %s" % (nomName))
                else:
                    t2Noms.append(nomName)
                    t2Choices[len(t2Noms) - 1] = nomName
            else:
                print("invalid team (not red/blue)")
        else:
            print("invalid team name: %s" % (nomName))
    else:
        print("n")