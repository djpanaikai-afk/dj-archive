# src/database.py
from pyrekordbox import Rekordbox6Database

class RekordboxReader:
    def __init__(self):
        self.db = Rekordbox6Database()

    def get_recent_histories(self, limit=30):
        """履歴の一覧を新しい順に取得"""
        history_items = self.db.get_history().all()
        valid = [h for h in history_items if h.Name]
        valid.sort(key=lambda x: x.DateCreated, reverse=True)
        return valid[:limit]

    def get_tracks_from_history(self, history_id):
        """指定された履歴IDに含まれる曲情報を取得"""
        history_songs = self.db.get_history_songs(HistoryID=history_id).all()
        tracks = []
        for s in history_songs:
            content = self.db.get_content(ID=s.ContentID)
            if content:
                tracks.append(content)
        return tracks