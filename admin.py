# admin.py (最新版)
import streamlit as st
import json
import os
import subprocess
from pathlib import Path
from src.database import RekordboxReader
from src.artwork import ArtworkExtractor

st.set_page_config(page_title="DJ Archive Admin", layout="wide")

st.title("🎧 DJ Archive Manager - Admin")

def push_to_github(commit_message):
    try:
        with st.spinner("GitHubの状態を確認中..."):
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True).stdout
            if not status:
                st.info("変更がないため、GitHubへの送信はスキップしました。")
                return
            subprocess.run(["git", "add", "-A"], check=True)
            subprocess.run(["git", "commit", "-m", commit_message], check=True)
            subprocess.run(["git", "push", "origin", "main"], check=True)
        st.success("Webサイトを更新しました！")
    except Exception as e:
        st.error(f"GitHub連携エラー: {e}")

tab1, tab2 = st.tabs(["🆕 新規アーカイブ作成", "📁 アーカイブ管理・削除"])

with tab1:
    try:
        reader = RekordboxReader()
        extractor = ArtworkExtractor()
        
        st.header("1. Rekordboxから履歴を選択")
        histories = reader.get_recent_histories(limit=50)
        history_names = [f"{h.DateCreated} - {h.Name}" for h in histories]
        selected_idx = st.selectbox("履歴を選択", range(len(history_names)), format_func=lambda x: history_names[x])
        selected_history = histories[selected_idx]

        # 履歴の曲を取得
        original_tracks = reader.get_tracks_from_history(selected_history.ID)
        
        st.header("2. 曲目の編集 (表示/非表示・コメント)")
        st.info("チェックを外した曲はWebサイトに表示されません。コメントは自由に変更できます。")
        
        # 編集内容を保持するリスト
        edited_track_data = []

        with st.container():
            for i, t in enumerate(original_tracks):
                col_show, col_info, col_comm = st.columns([0.5, 3, 4])
                
                # 初期値の準備
                artist = getattr(t, 'ArtistName', 'Unknown')
                title = getattr(t, 'Title', 'Unknown')
                default_comment = getattr(t, 'Commnt', '')

                with col_show:
                    is_visible = st.checkbox("公開", value=True, key=f"show_{i}")
                
                with col_info:
                    st.markdown(f"**{i+1}: {title}**  \n{artist}")
                
                with col_comm:
                    edited_comment = st.text_input("コメントを編集", value=default_comment, key=f"comm_{i}")
                
                if is_visible:
                    edited_track_data.append({
                        "original_obj": t,
                        "comment": edited_comment
                    })
                st.divider()

        st.header("3. イベント情報を入力")
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
            selected_tags = st.multiselect("既存タグから選択", options=sorted(list(existing_tags)))
            new_tags = st.text_input("新規タグを追加 (カンマ区切り)")

        final_tags = list(set(selected_tags + [t.strip() for t in new_tags.split(",") if t.strip()]))
        description = st.text_area("セットの説明 / コメント")

        if st.button("アーカイブを保存する", type="primary"):
            safe_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
            archive_id = f"{event_date}_{safe_name}"
            
            with st.spinner("保存中..."):
                final_tracks_for_json = []
                for item in edited_track_data:
                    t = item["original_obj"]
                    art_path = extractor.extract(t)
                    final_tracks_for_json.append({
                        "title": getattr(t, 'Title', 'Unknown'),
                        "artist": getattr(t, 'ArtistName', 'Unknown'),
                        "album": getattr(t, 'AlbumName', ''),
                        "comment": item["comment"], # 編集したコメントを使用
                        "artwork": art_path
                    })

                archive_data = {
                    "id": archive_id, "event_name": event_name, "venue": venue,
                    "date": str(event_date), "tags": final_tags,
                    "description": description, "tracks": final_tracks_for_json
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
                    "track_count": len(final_tracks_for_json), "venue": venue, "tags": final_tags
                })
                index_data.sort(key=lambda x: x['date'], reverse=True)
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, indent=4, ensure_ascii=False)
                
                st.success(f"保存しました！ (公開曲数: {len(final_tracks_for_json)}曲)")
                st.balloons()

    except Exception as e:
        st.error(f"エラー: {e}")

with tab2:
    # (以前と同じ削除機能)
    st.header("作成済みアーカイブの管理")
    index_path = Path("data/index.json")
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        for item in index_data:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.write(f"**{item['date']} - {item['event_name']}**")
            with col2:
                if st.button("削除", key=f"del_{item['id']}"):
                    json_file = Path(f"data/archives/{item['id']}.json")
                    if json_file.exists(): os.remove(json_file)
                    new_index = [i for i in index_data if i['id'] != item['id']]
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(new_index, f, indent=4, ensure_ascii=False)
                    st.rerun()
            st.divider()

st.sidebar.header("🚀 Web公開設定")
if st.sidebar.button("GitHubへ公開（プッシュ）"):
    push_to_github("Update archives (Admin Tool)")