# src/artwork.py
import os
import shutil
from pathlib import Path

class ArtworkExtractor:
    def __init__(self, output_dir="data/artworks"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # あなたが見つけてくれた絶対パスを基準にします
        self.share_base = Path(os.environ['APPDATA']) / "Pioneer" / "rekordbox" / "share"

    def extract(self, track):
        # ImagePath 自体がない場合はスキップ
        if not hasattr(track, 'ImagePath') or not track.ImagePath:
            return None
        
        # RekordboxのDBに入っているパス (例: PIONEER/Artwork/001/002.jpg)
        rel_path = track.ImagePath

        # パスの結合を試みる
        # もし rel_path が / から始まっていたら除去する
        clean_rel_path = rel_path.lstrip('/')
        # もし rel_path が share/ から始まっていたら除去する
        if clean_rel_path.startswith("share/"):
            clean_rel_path = clean_rel_path.replace("share/", "", 1)

        # 最終的な絶対パスを合成
        src_path = self.share_base / clean_rel_path

        # 【デバッグ用】最初の1曲目だけ中身を表示する
        if not hasattr(self, '_debug_done'):
            print(f"\n[DEBUG] 探索中のパス:")
            print(f"  DB内のパス: {rel_path}")
            print(f"  合成した絶対パス: {src_path}")
            print(f"  ファイルの存在確認: {'OK' if src_path.exists() else 'NOT FOUND'}")
            self._debug_done = True

        if not src_path.exists():
            return None

        # 保存先のファイル名（Track IDをファイル名にする）
        ext = src_path.suffix or ".jpg"
        dest_filename = f"{track.ID}{ext}"
        dest_path = self.output_dir / dest_filename
        
        try:
            shutil.copy2(src_path, dest_path)
            # JSONには Webサイトから見た相対パスを記録する
            return f"artworks/{dest_filename}"
        except Exception as e:
            print(f"Error copying artwork: {e}")
            return None