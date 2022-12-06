from zipfile import ZipFile

mb2_folder_path = r"C:\Program Files (x86)\Steam\steamapps\common\Jedi Academy\GameData\MBII\\"
pk3s_to_open = ["03_MovieGameMappack.pk3", "mb2_cmp_assets3.pk3", "mb2_pb_assets2.pk3", "mb2_um_assets3.pk3", "MBAssets3.pk3"]
teams = []

def get_team_names():
    for i in pk3s_to_open:
        with ZipFile(mb2_folder_path + i, "r") as zip:
            toExtract = []
            for name in zip.namelist():
                if name.lower().startswith("ext_data/mb2/teamconfig"):
                    toExtract.append(name.removeprefix("ext_data/mb2/teamconfig/").removeprefix("Ext_Data/MB2/teamconfig/").removesuffix(".mbtc"))  # this is fine
            teams.extend(toExtract)
    return teams


