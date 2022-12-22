from zipfile import ZipFile

mb2_folder_path = r"C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\\"
pk3s_to_open = ["03_MovieGameMappack.pk3", "mb2_cmp_assets3.pk3", "mb2_pb_assets2.pk3", "mb2_um_assets3.pk3", "MBAssets3.pk3"]

class Map(object):
  def __init__(self):
    self.name = None
    self.redTeam = None
    self.blueTeam = None


def getMapTeams():
  teams = {}
  for i in pk3s_to_open:
    with ZipFile(mb2_folder_path + i, "r") as zip:
      toExtract = []
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
def mapTeams(mapName):
  map = MAP_LIST.get(mapName)
  if map:
    return (map.redTeam, map.blueTeam)
  else:
    return None

for i in getMapTeams():
  print(i + str(mapTeams(i)))