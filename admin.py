# admin.py
import streamlit as st
import json
import os
import subprocess
from pathlib import Path
from src.database import RekordboxReader
from src.artwork import ArtworkExtractor

st.set_page_config(page_title="DJ Archive Admin", layout="wide")

st.title("🎧 DJ Archive Manager - Admin")

# 1. データの準備
try:
    reader = RekordboxReader()
    extractor = ArtworkExtractor()
except Exception as e:
    st.error(f"Rekordbox接続エラー: {e}")
    st.stop()

# 既存の全タグを取得
index_path = Path("data/index.json")
existing_tags = set()
if index_path.exists():
    with open(index_path, "r", encoding="utf-8") as f:
        idx_data = json.load(f)
        for item in idx_data:
            for t in item.get('tags', []):
                existing_tags.add(t)

# 2. 履歴の読み込み
st.header("1. Rekordboxから履歴を選択")
histories = reader.get_recent_histories(limit=50)
history_names = [f"{h.DateCreated} - {h.Name}" for h in histories]
selected_idx = st.selectbox("処理する履歴を選んでください", range(len(history_names)), format_func=lambda x: history_names[x])
selected_history = histories[selected_idx]

# 3. メタデータの入力
st.header("2. イベント情報を入力")
col1, col2 = st.columns(2)
with col1:
    event_name = st.text_input("イベント名 (タイトル)", value=selected_history.Name)
    venue = st.text_input("会場 / 配信名", placeholder="Example Club")
with col2:
    event_date = st.date_input("開催日", value=selected_history.DateCreated)
    selected_tags = st.multiselect("既存のタグから選択", options=sorted(list(existing_tags)))
    new_tags = st.text_input("新規タグを追加 (カンマ区切り)", placeholder="Techno, House")

final_tags = list(set(selected_tags + [t.strip() for t in new_tags.split(",") if t.strip()]))
description = st.text_area("セットの説明 / コメント")

# 4. 保存処理
if st.button("このセットをアーカイブ保存する", type="primary"):
    safe_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
    archive_id = f"{event_date}_{safe_name}"
    
    with st.spinner("処理中..."):
        tracks = reader.get_tracks_from_history(selected_history.ID)
        track_list = []
        for t in tracks:
            art_path = extractor.extract(t)
            track_list.append({
                "title": getattr(t, 'Title', 'Unknown'),
                "artist": getattr(t, 'ArtistName', 'Unknown'),
                "album": getattr(t, 'AlbumName', ''),
                "artwork": art_path
            })

        archive_data = {
            "id": archive_id, "event_name": event_name, "venue": venue,
            "date": str(event_date), "tags": final_tags,
            "description": description, "tracks": track_list
        }

        os.makedirs("data/archives", exist_ok=True)
        with open(f"data/archives/{archive_id}.json", "w", encoding="utf-8") as f:
            json.dump(archive_data, f, indent=4, ensure_ascii=False)
        
        index_data = []
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                index_data = json.load(f)
        
        index_data = [i for i in index_data if i['id'] != archive_id]
        index_data.append({
            "id": archive_id, "event_name": event_name, "date": str(event_date),
            "track_count": len(track_list), "venue": venue, "tags": final_tags
        })
        index_data.sort(key=lambda x: x['date'], reverse=True)
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4, ensure_ascii=False)

    st.success(f"保存完了しました！")
    st.balloons()

# --- 公開セクション ---
st.divider()
st.header("🚀 Webサイトに公開")
st.info("保存したデータをGitHubにアップロードして公開します。")
if st.button("GitHubへ公開（プッシュ）"):
    try:
        with st.spinner("公開作業中..."):
            # Gitコマンドを裏側で実行
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", f"Add archive: {event_name}"], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
        st.success("Webサイトの更新が完了しました！(反映まで1〜2分かかります)")
    except Exception as e:
        st.error(f"エラーが発生しました: {e}\nGitの設定を確認してください。")