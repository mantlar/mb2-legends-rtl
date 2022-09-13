from os import listdir

class Character(object):
    def __init__(self, mbclass):
        self.weapons = []
        self.attributes = []
        self.mbclass = mbclass
    def getClassPointCost(self, attribute, level):
        if attribute == "MB_ATT_ARMOUR":
            costs = [0, 4, 6]
        elif attribute == "MB_ATT_AMMO":
            costs = [0, 4, 6]
        elif attribute == "MB_ATT_FORCEBLOCK":
            costs = [4, 6, 6]
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        elif attribute == "MB_ATT_PISTOL":
            if "WP_BLASTER_PISTOL" in self.weapons:
                costs = [0, 4, 15]
            elif "WP_DEMP2" in self.weapons:
                costs = [0, 4, 10]
            elif "WP_BRYAR_OLD" in self.weapons:
                costs = [0, 4, 14]
        elif attribute == "MB_ATT_BLASTER":
            if 
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        elif attribute == "MB_ATT_DEFLECT":
            costs = [2, 4, 6]
        
        return sum(costs[:level])
    def getArmorCost(self, armorval):
        if self.mbclass == "MB_CLASS_TROOPER" or self.mbclass == "MB_CLASS_SOLDIER" or "MB_CLASS_ELITETROOPER" or self.mbclass == "MB_CLASS_COMMANDER":
            pass
        elif self.mbclass == "MB_CLASS_ELITETROOPER" or self.mbclass == "MB_CLASS_COMMANDER":
            pass
        elif self.mbclass == "MB_CLASS_ELITETROOPER" or self.mbclass == "MB_CLASS_COMMANDER":
            pass
        elif self.mbclass == "MB_CLASS_ELITETROOPER" or self.mbclass == "MB_CLASS_COMMANDER":
            pass
        
class Weapon(object):
    def __init__(self):
        


MASTER_TEAM_LIST = listdir("./teams")
MASTER_CHAR_LIST = listdir("./chars")
for i in MASTER_CHAR_LIST:
    with open(i) as file:
        