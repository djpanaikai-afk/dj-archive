from pathlib import Path
from rich.console import Console

console = Console()


def find_database():
    """
    Rekordboxのdatafile.edbを探す
    """

    candidates = [
        Path.home() / "AppData/Roaming/Pioneer",
        Path.home() / "AppData/Roaming/AlphaTheta",
    ]

    for folder in candidates:
        if not folder.exists():
            continue

        dbs = list(folder.rglob("datafile.edb"))

        if dbs:
            return dbs[0]

    return None