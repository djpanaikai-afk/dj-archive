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

# --- 共通処理: GitHubへの公開関数 ---
def push_to_github(commit_message):
    try:
        with st.spinner("GitHubを更新中..."):
            subprocess.run(["git", "add", "."], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
        st.success("Webサイトを更新しました！")
    except Exception as e:
        st.error(f"GitHub連携エラー: {e}")

# タブの作成
tab1, tab2 = st.tabs(["🆕 新規アーカイブ作成", "📁 アーカイブ管理・削除"])

# --- TAB 1: 新規作成 ---
with tab1:
    try:
        reader = RekordboxReader()
        extractor = ArtworkExtractor()
        
        st.header("1. Rekordboxから履歴を選択")
        histories = reader.get_recent_histories(limit=50)
        history_names = [f"{h.DateCreated} - {h.Name}" for h in histories]
        selected_idx = st.selectbox("履歴を選択", range(len(history_names)), format_func=lambda x: history_names[x])
        selected_history = histories[selected_idx]

        st.header("2. イベント情報を入力")
        # (以前と同じ入力フォーム)
        col1, col2 = st.columns(2)
        index_path = Path("data/index.json")
        existing_tags = set()
        if index_path.exists():
            with open(index_path, "r", encoding="utf-8") as f:
                idx_data = json.load(f)
                for item in idx_data:
                    for t in item.get('tags', []): existing_tags.add(t)

        with col1:
            event_name = st.text_input("イベント名", value=selected_history.Name)
            venue = st.text_input("会場 / 配信名")
        with col2:
            event_date = st.date_input("開催日", value=selected_history.DateCreated)
            selected_tags = st.multiselect("既存タグ", options=sorted(list(existing_tags)))
            new_tags = st.text_input("新規タグ (カンマ区切り)")

        final_tags = list(set(selected_tags + [t.strip() for t in new_tags.split(",") if t.strip()]))
        description = st.text_area("説明 / コメント")

        if st.button("アーカイブを保存する", type="primary"):
            safe_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
            archive_id = f"{event_date}_{safe_name}"
            
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
                with open(index_path, "r", encoding="utf-8") as f: index_data = json.load(f)
            index_data = [i for i in index_data if i['id'] != archive_id]
            index_data.append({
                "id": archive_id, "event_name": event_name, "date": str(event_date),
                "track_count": len(track_list), "venue": venue, "tags": final_tags
            })
            index_data.sort(key=lambda x: x['date'], reverse=True)
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data, f, indent=4, ensure_ascii=False)
            st.success("保存しました！")

    except Exception as e:
        st.error(f"エラー: {e}")

# --- TAB 2: 管理・削除 ---
with tab2:
    st.header("作成済みアーカイブの管理")
    index_path = Path("data/index.json")
    
    if not index_path.exists():
        st.info("アーカイブがまだありません。")
    else:
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        
        for item in index_data:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{item['date']} - {item['event_name']}** ({item['track_count']} tracks)")
            with col2:
                # 削除ボタン
                if st.button("削除", key=f"del_{item['id']}"):
                    # 1. JSONファイルを削除
                    json_file = Path(f"data/archives/{item['id']}.json")
                    if json_file.exists():
                        os.remove(json_file)
                    
                    # 2. インデックスから削除
                    new_index = [i for i in index_data if i['id'] != item['id']]
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(new_index, f, indent=4, ensure_ascii=False)
                    
                    st.warning(f"削除しました: {item['event_name']}")
                    st.rerun() # 画面を更新

# --- 共通公開ボタン (サイドバーに配置) ---
st.sidebar.header("🚀 Web公開設定")
if st.sidebar.button("GitHubへ公開（プッシュ）"):
    push_to_github("Update archives (Admin Tool)")