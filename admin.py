# admin.py (最新版)
import streamlit as st
import json
import os
import subprocess
from pathlib import Path
from src.database import RekordboxReader
from src.artwork import ArtworkExtractor
from PIL import Image

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

        original_tracks = reader.get_tracks_from_history(selected_history.ID)
        st.header("2. 曲目の編集")
        edited_track_data = []
        with st.expander("曲目リストとコメントを編集", expanded=False):
            for i, t in enumerate(original_tracks):
                col_show, col_info, col_comm = st.columns([0.5, 3, 4])
                artist, title, default_comment = getattr(t, 'ArtistName', 'Unknown'), getattr(t, 'Title', 'Unknown'), getattr(t, 'Commnt', '')
                with col_show: is_visible = st.checkbox("公開", value=True, key=f"show_{i}")
                with col_info: st.markdown(f"**{title}** / {artist}")
                with col_comm: edited_comment = st.text_input("コメント", value=default_comment, key=f"comm_{i}")
                if is_visible: edited_track_data.append({"original_obj": t, "comment": edited_comment})

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
            uploaded_flyer = st.file_uploader("フライヤー画像をアップロード (任意)", type=['jpg', 'jpeg', 'png'])
        with col2:
            event_date = st.date_input("開催日", value=selected_history.DateCreated)
            selected_tags = st.multiselect("既存タグ", options=sorted(list(existing_tags)))
            new_tags = st.text_input("新規タグ")
            description = st.text_area("セットの説明")

        final_tags = list(set(selected_tags + [t.strip() for t in new_tags.split(",") if t.strip()]))

        if st.button("アーカイブを保存する", type="primary"):
            safe_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
            archive_id = f"{event_date}_{safe_name}"
            
            # フライヤーの処理
            flyer_rel_path = None
            if uploaded_flyer:
                flyer_dir = Path("data/flyers")
                flyer_dir.mkdir(parents=True, exist_ok=True)
                flyer_ext = Path(uploaded_flyer.name).suffix
                flyer_path = flyer_dir / f"{archive_id}{flyer_ext}"
                with open(flyer_path, "wb") as f:
                    f.write(uploaded_flyer.getbuffer())
                flyer_rel_path = f"flyers/{archive_id}{flyer_ext}"

            with st.spinner("保存中..."):
                final_tracks_for_json = []
                for item in edited_track_data:
                    t = item["original_obj"]
                    art_path = extractor.extract(t)
                    final_tracks_for_json.append({
                        "title": getattr(t, 'Title', 'Unknown'), "artist": getattr(t, 'ArtistName', 'Unknown'),
                        "comment": item["comment"], "artwork": art_path
                    })

                archive_data = {
                    "id": archive_id, "event_name": event_name, "venue": venue,
                    "date": str(event_date), "tags": final_tags, "description": description,
                    "tracks": final_tracks_for_json, "flyer": flyer_rel_path
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
                    "track_count": len(final_tracks_for_json), "venue": venue, "tags": final_tags,
                    "flyer": flyer_rel_path
                })
                index_data.sort(key=lambda x: x['date'], reverse=True)
                with open(index_path, "w", encoding="utf-8") as f:
                    json.dump(index_data, f, indent=4, ensure_ascii=False)
                st.success("保存完了しました！")
                st.balloons()
    except Exception as e:
        st.error(f"エラー: {e}")

with tab2:
    st.header("アーカイブ管理")
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f: index_data = json.load(f)
        for item in index_data:
            col1, col2 = st.columns([4, 1])
            with col1: st.write(f"**{item['date']} - {item['event_name']}**")
            with col2:
                if st.button("削除", key=f"del_{item['id']}"):
                    json_file = Path(f"data/archives/{item['id']}.json")
                    if json_file.exists(): os.remove(json_file)
                    # フライヤーも削除
                    if item.get('flyer'):
                        f_path = Path("data") / item['flyer']
                        if f_path.exists(): os.remove(f_path)
                    new_index = [i for i in index_data if i['id'] != item['id']]
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(new_index, f, indent=4, ensure_ascii=False)
                    st.rerun()
            st.divider()

st.sidebar.header("🚀 Web公開設定")
if st.sidebar.button("GitHubへ公開"): push_to_github("Update archives")