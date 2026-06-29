# admin.py
import streamlit as st
import json
import os
import subprocess
from pathlib import Path
from src.database import RekordboxReader
from src.artwork import ArtworkExtractor

st.set_page_config(page_title="DJ Archive Admin", layout="wide")

# セッション状態の初期化
if 'editing_data' not in st.session_state:
    st.session_state.editing_data = None

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

tab1, tab2 = st.tabs(["🆕 アーカイブ作成・編集", "📁 管理・削除"])

# --- TAB 1: 作成・編集 ---
with tab1:
    is_edit_mode = st.session_state.editing_data is not None
    
    if is_edit_mode:
        st.header("📝 アーカイブを編集書き換え中")
        if st.button("← 新規作成に戻る"):
            st.session_state.editing_data = None
            st.rerun()
        current_data = st.session_state.editing_data
        unique_prefix = current_data.get('id', 'edit')
    else:
        st.header("1. Rekordboxから履歴を選択")
        try:
            reader = RekordboxReader()
            extractor = ArtworkExtractor()
            histories = reader.get_recent_histories(limit=50)
            history_names = [f"{h.DateCreated} - {h.Name}" for h in histories]
            selected_idx = st.selectbox("履歴を選択", range(len(history_names)), format_func=lambda x: history_names[x])
            selected_history = histories[selected_idx]
            original_tracks = reader.get_tracks_from_history(selected_history.ID)
            
            current_data = {
                "id": None,
                "event_name": selected_history.Name,
                "venue": "",
                "date": selected_history.DateCreated,
                "tags": [],
                "description": "",
                "tracks": [{"title": getattr(t, 'Title', 'Unknown'), "artist": getattr(t, 'ArtistName', 'Unknown'), "comment": getattr(t, 'Commnt', ''), "original_obj": t} for t in original_tracks],
                "flyer": None
            }
            unique_prefix = str(selected_history.ID)
        except Exception as e:
            st.error(f"接続エラー: {e}")
            st.stop()

    st.divider()
    st.header("2. 曲目とコメントの編集")
    final_track_list = []
    for i, t in enumerate(current_data["tracks"]):
        col_show, col_info, col_comm = st.columns([0.5, 3, 4])
        with col_show:
            is_visible = st.checkbox("公開", value=True, key=f"{unique_prefix}_show_{i}")
        with col_info:
            st.markdown(f"**{t['title']}** / {t['artist']}")
        with col_comm:
            edited_comment = st.text_input("コメント", value=t.get('comment', ''), key=f"{unique_prefix}_comm_{i}")
        if is_visible:
            t_copy = t.copy()
            t_copy['comment'] = edited_comment
            final_track_list.append(t_copy)

    st.header("3. イベント詳細情報の入力")
    col1, col2 = st.columns(2)
    
    index_path = Path("data/index.json")
    existing_tags = set()
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            idx_data_temp = json.load(f)
            for item in idx_data_temp:
                for tag in item.get('tags', []): existing_tags.add(tag)

    with col1:
        event_name = st.text_input("イベント名", value=current_data["event_name"], key=f"{unique_prefix}_evname")
        venue = st.text_input("会場 / 配信名", value=current_data["venue"], key=f"{unique_prefix}_venue")
        uploaded_flyer = st.file_uploader("フライヤー画像を更新 (任意)", type=['jpg', 'jpeg', 'png'], key=f"{unique_prefix}_flyer")
    with col2:
        from datetime import datetime
        date_val = current_data["date"]
        if isinstance(date_val, str):
            try:
                date_val = datetime.strptime(date_val[:10], '%Y-%m-%d').date()
            except Exception:
                date_val = datetime.now().date()
        
        event_date = st.date_input("開催日", value=date_val, key=f"{unique_prefix}_date")
        selected_tags = st.multiselect("既存タグ", options=sorted(list(existing_tags)), default=current_data["tags"], key=f"{unique_prefix}_tags")
        new_tags = st.text_input("新規タグを追加", key=f"{unique_prefix}_newtags")
        description = st.text_area("セットの説明", value=current_data["description"], key=f"{unique_prefix}_desc")

    final_tags = list(set(selected_tags + [t.strip() for t in new_tags.split(",") if t.strip()]))

    if st.button("💾 この内容で保存（更新）する", type="primary"):
        safe_name = "".join([c for c in event_name if c.isalnum() or c in (' ', '_')]).rstrip().replace(' ', '_')
        archive_id = f"{event_date}_{safe_name}"
        old_id = current_data.get('id')
        flyer_rel_path = current_data.get('flyer')
        
        if uploaded_flyer:
            flyer_dir = Path("data/flyers")
            flyer_dir.mkdir(parents=True, exist_ok=True)
            flyer_ext = Path(uploaded_flyer.name).suffix
            flyer_path = flyer_dir / f"{archive_id}{flyer_ext}"
            with open(flyer_path, "wb") as f:
                f.write(uploaded_flyer.getbuffer())
            flyer_rel_path = f"flyers/{archive_id}{flyer_ext}"

        with st.spinner("保存中..."):
            save_tracks = []
            for t in final_track_list:
                if 'original_obj' in t:
                    art_path = extractor.extract(t['original_obj'])
                else:
                    art_path = t.get('artwork')
                save_tracks.append({
                    "title": t['title'], "artist": t['artist'],
                    "comment": t['comment'], "artwork": art_path
                })
            new_archive_data = {
                "id": archive_id, "event_name": event_name, "venue": venue,
                "date": str(event_date), "tags": final_tags, "description": description,
                "tracks": save_tracks, "flyer": flyer_rel_path
            }
            if old_id and old_id != archive_id:
                old_file = Path(f"data/archives/{old_id}.json")
                if old_file.exists(): os.remove(old_file)
            
            os.makedirs("data/archives", exist_ok=True)
            with open(f"data/archives/{archive_id}.json", "w", encoding="utf-8") as f:
                json.dump(new_archive_data, f, indent=4, ensure_ascii=False)
            
            # --- エラー箇所修正: index_data という変数名に統一 ---
            index_data_list = []
            if index_path.exists():
                with open(index_path, "r", encoding="utf-8") as f:
                    index_data_list = json.load(f)
            
            # リスト内包表記で既存の同じID（または古いID）を削除
            index_data_list = [i for i in index_data_list if i['id'] != archive_id and (not old_id or i['id'] != old_id)]
            
            # 新しい情報を追加
            index_data_list.append({
                "id": archive_id, "event_name": event_name, "date": str(event_date),
                "track_count": len(save_tracks), "venue": venue, "tags": final_tags, "flyer": flyer_rel_path
            })
            index_data_list.sort(key=lambda x: x['date'], reverse=True)
            
            with open(index_path, "w", encoding="utf-8") as f:
                json.dump(index_data_list, f, indent=4, ensure_ascii=False)
            
            st.success("保存完了！")
            st.session_state.editing_data = None
            st.rerun()

# --- TAB 2: 管理・削除 ---
with tab2:
    st.header("📁 アーカイブの管理")
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            index_data_display = json.load(f)
        for item in index_data_display:
            col_info, col_edit, col_del = st.columns([4, 1, 1])
            with col_info:
                st.write(f"**{item['date']} - {item['event_name']}**")
            with col_edit:
                if st.button("編集", key=f"editbtn_{item['id']}"):
                    with open(f"data/archives/{item['id']}.json", "r", encoding="utf-8") as f:
                        st.session_state.editing_data = json.load(f)
                    st.rerun()
            with col_del:
                if st.button("削除", key=f"delbtn_{item['id']}"):
                    json_file = Path(f"data/archives/{item['id']}.json")
                    if json_file.exists(): os.remove(json_file)
                    new_index = [i for i in index_data_display if i['id'] != item['id']]
                    with open(index_path, "w", encoding="utf-8") as f:
                        json.dump(new_index, f, indent=4, ensure_ascii=False)
                    st.rerun()
            st.divider()

st.sidebar.header("🚀 Web公開設定")
if st.sidebar.button("GitHubへ公開"):
    push_to_github("Update/Edit archives")