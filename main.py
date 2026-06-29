# main.py
import json
import os
from rich.console import Console
from rich.table import Table
from src.database import RekordboxReader
from src.artwork import ArtworkExtractor

console = Console()

def main():
    # フォルダの準備
    os.makedirs("data/artworks", exist_ok=True)
    
    reader = RekordboxReader()
    extractor = ArtworkExtractor()
    
    console.rule("[bold]DJ Archive Manager[/bold]")
    
    # 1. 履歴の選択
    try:
        histories = reader.get_recent_histories()
    except Exception as e:
        console.print(f"[red]Database Error: {e}[/red]")
        return

    table = Table(title="Select History to Archive")
    table.add_column("No.", justify="right", style="cyan")
    table.add_column("Date", style="magenta")
    table.add_column("Name", style="green")
    
    for i, h in enumerate(histories):
        table.add_row(str(i+1), str(h.DateCreated), h.Name)
    
    console.print(table)
    choice = console.input("\nどの履歴を処理しますか？ (番号を入力): ")
    
    try:
        selected = histories[int(choice)-1]
    except (ValueError, IndexError):
        console.print("[red]正しい番号を入力してください。[/red]")
        return
    
    # 2. 曲の取得とアートワーク抽出
    tracks = reader.get_tracks_from_history(selected.ID)
    playlist_data = {
        "history_name": selected.Name,
        "date": str(selected.DateCreated),
        "tracks": []
    }
    
    console.print(f"\n[bold yellow]{selected.Name}[/bold yellow] を処理中...")
    
    with console.status("[bold green]Extracting artworks...") as status:
        for t in tracks:
            art_path = extractor.extract(t)
            
            playlist_data["tracks"].append({
                "id": t.ID,
                "title": getattr(t, 'Title', 'Unknown'),
                "artist": getattr(t, 'ArtistName', 'Unknown'),
                "album": getattr(t, 'AlbumName', ''),
                "artwork": art_path
            })
    
    # 3. JSONとして保存
    output_file = "data/history.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(playlist_data, f, indent=4, ensure_ascii=False)
        
    console.rule("Process Completed!")
    console.print(f"JSON data saved to: [bold cyan]{output_file}[/bold cyan]")
    console.print(f"Artworks extracted to: [bold cyan]data/artworks/[/bold cyan]")

if __name__ == "__main__":
    main()