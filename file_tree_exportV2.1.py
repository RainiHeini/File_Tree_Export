import sys
if sys.platform.startswith("win"):
    import ctypes
    if ctypes.windll.kernel32.GetConsoleWindow() == 0:
        ctypes.windll.kernel32.AllocConsole()

import os, html, time, webbrowser, threading, itertools, traceback
from datetime import datetime

# ----------------------
# Konfiguration
# ----------------------
excluded_extensions = {".vob", ".ifo", ".bup"}
excluded_filenames  = {"thumbs.db", ".ds_store"}

# ----------------------
# Hilfsfunktionen
# ----------------------
def format_size(size_bytes):
    gb = size_bytes / (1024**3)
    return f"{gb:.2f} GB" if gb > 1 else f"{size_bytes/1024**2:.2f} MB"

def print_progress(cur, tot):
    if tot == 0:
        return
    bar_len = 30
    filled = int(bar_len * cur / tot)
    perc = int(100 * cur / tot)
    bar = "█" * filled + "-" * (bar_len - filled)
    sys.stdout.write(f"\r📄 Generiere HTML: [{bar}] {perc}% ({cur}/{tot})")
    sys.stdout.flush()

# ----------------------
# 1) Scannen mit Spinner + Timer
# ----------------------
def scan_directory(path):
    tree, total_files, total_dirs, total_size = {}, 0, 0, 0
    start = time.time()
    done = [False]
    def spinner():
        for c in itertools.cycle("|/-\\"):
            if done[0]:
                break
            elapsed = int(time.time() - start)
            sys.stdout.write(f"\r🔁 Scanne Verzeichnis... {c} ⏱️ {elapsed}s")
            sys.stdout.flush()
            time.sleep(0.1)
    t = threading.Thread(target=spinner, daemon=True)
    t.start()

    for root, dirs, files in os.walk(path):
        rel = os.path.relpath(root, path)
        node = tree
        if rel != ".":
            for part in rel.split(os.sep):
                node = node.setdefault(part, {})

        dvd_cnt = dvd_sz = 0
        for d in dirs:
            node[d] = {}
        for f in files:
            lf = f.lower()
            if lf in excluded_filenames:
                continue
            ext = os.path.splitext(f)[1].lower()
            full = os.path.join(root, f)
            if ext in excluded_extensions:
                try:
                    dvd_sz += os.path.getsize(full)
                except:
                    pass
                dvd_cnt += 1
                continue
            try:
                sz = os.path.getsize(full)
                node[f] = sz
                total_size += sz
            except:
                node[f] = None
            total_files += 1

        if dvd_cnt > 0:
            node["_DVD_PLACEHOLDER_"] = {"count": dvd_cnt, "size": dvd_sz}

        total_dirs += len(dirs)

    done[0] = True
    t.join()
    print(f"\r✅ Scan fertig nach {int(time.time() - start)}s")
    return tree, total_files, total_dirs, total_size

# ----------------------
# 2) Rekursiver HTML-Baum mit Fortschritt
# ----------------------
def build_html_from_tree(tree, depth=0, prog=[0], total=1):
    lines = []
    indent = "  " * depth
    dirs = sorted(k for k, v in tree.items() if isinstance(v, dict) and k != "_DVD_PLACEHOLDER_")
    files = sorted(k for k, v in tree.items() if not isinstance(v, dict))
    placeholder = tree.get("_DVD_PLACEHOLDER_")

    for d in dirs:
        lines.append(f"{indent}<li><details><summary>📁 {html.escape(d)}</summary><ul>")
        lines += build_html_from_tree(tree[d], depth + 1, prog, total)
        lines.append(f"{indent}</ul></details></li>")

    for f in files:
        sz = tree[f]
        if sz is None:
            lines.append(f"{indent}<li>📄 {html.escape(f)} <span class=\"size\">(Zugriff verweigert)</span></li>")
        else:
            lines.append(f"{indent}<li>📄 {html.escape(f)} <span class=\"size\">({format_size(sz)})</span></li>")
        prog[0] += 1
        print_progress(prog[0], total)

    if placeholder:
        cnt, sz = placeholder["count"], placeholder["size"]
        lines.append(
            f"{indent}<li><em>📦 {cnt} DVD-Datei(en) ausgeblendet, insgesamt {format_size(sz)}</em></li>"
        )

    return lines

# ----------------------
# 3) Hauptfunktion
# ----------------------
def main():
    try:
        root = os.path.dirname(os.path.abspath(__file__))
        print(f"📂 Arbeitsordner: {root}")
        print("🔕 Hinweis zu ausgeschlossenen Dateien:")
        print("   📦 DVD-Dateien (.vob, .ifo, .bup) werden im HTML gruppiert angezeigt")
        print("   🚫 Systemdateien (Thumbs.db, .DS_Store) werden vollständig ignoriert\n")

        tree, fc, dc, ts = scan_directory(root)
        print(f"🔎 Gefunden: {fc} Dateien in {dc} Ordnern  📦 Gesamtgröße: {format_size(ts)}\n")

        print("📄 Erzeuge HTML:")
        lines = build_html_from_tree(tree, prog=[0], total=fc)
        print()  # Neue Zeile nach Balken

        html_tree = "\n".join(lines)
        now = datetime.now()
        generated = now.strftime("%Y-%m-%d %H:%M")
        outname = f"file_tree_export_{os.path.basename(root).replace(' ','_')}_{now.strftime('%Y%m%d_%H%M')}.html"
        outpath = os.path.join(root, outname)

        html_content = f"""<!DOCTYPE html>
<html lang="de"><head><meta charset="UTF-8"><title>File Tree Export</title><style>
body {{font-family:'Courier New',monospace;background:#111;color:#e0e0e0;padding:20px}}
.meta {{color:#aaa;font-size:0.9em;margin-bottom:1.5em;line-height:1.6em}}
ul {{list-style:none;padding-left:1em;line-height:1.4em}}
summary {{cursor:pointer;font-weight:bold;color:#00ccff}}
.size {{color:#888;font-size:0.9em}}
li {{margin-left:0.5em}}
details>summary::marker {{content:"▸ "}}
details[open]>summary::marker {{content:"▾ "}}
em {{color:#aaa}}
.controls {{margin-bottom:20px}}
input#search {{background:#222;color:#eee;border:1px solid #444;padding:5px 10px;width:200px}}
button.clear-btn {{margin-left:5px;padding:5px 8px;cursor:pointer;}}
.light-mode input#search {{background:#fff;color:#111;border:1px solid #aaa}}
button {{background:#222;border:1px solid #444;color:#eee;padding:5px 10px;margin-right:10px;cursor:pointer}}
button:hover {{background:#333}}
.light-mode {{background:#fefefe;color:#111}}
.light-mode summary {{color:#003366}}
.light-mode .size,.light-mode em,.light-mode .meta {{color:#555}}
.light-mode button{{background:#ddd;color:#000;border:1px solid #aaa}}
</style></head><body>
<h1>📁 File Tree Export</h1>
<div class="meta">
Basisordner: {html.escape(root)}<br>
Erstellt: {generated}<br>
📁 Ordner: {dc} &nbsp;&nbsp; 📄 Dateien: {fc} &nbsp;&nbsp; 💾 Gesamtgröße: {format_size(ts)}
</div>
<div class="controls">
  <input type="text" id="search" placeholder="🔍 Suchen…" oninput="filterTree()"/>
  <button class="clear-btn" onclick="document.getElementById('search').value='';filterTree()">✖</button>
  <span id="results" style="margin-left:1em;font-size:0.9em;color:#aaa"></span><br><br>
  <button onclick="toggleAll(true)">Alle aufklappen</button>
  <button onclick="toggleAll(false)">Alle einklappen</button>
  <button onclick="toggleTheme()">🌗 Dark/Light</button>
</div>
<ul>
{html_tree}
</ul>
<script>
function toggleAll(expand) {{document.querySelectorAll("details").forEach(d=>d.open=expand);}}
function toggleTheme() {{document.body.classList.toggle("light-mode");}}
function filterTree() {{
  const term = document.getElementById("search").value.toLowerCase();
  const details = document.querySelectorAll("details");
  const items   = document.querySelectorAll("li");
  if(term==="") {{
    details.forEach(d=>d.open=false);
    items.forEach(i=>i.style.display="");
    document.getElementById("results").textContent="";
    return;
  }}
  let count = 0;
  items.forEach(item=>{{ 
    const txt = item.textContent.toLowerCase();
    const m   = txt.includes(term);
    item.style.display = m ? "" : "none";
    if(m) {{
      let p = item.parentElement;
      while(p && p.tagName!=='BODY') {{ if(p.tagName==='DETAILS') p.open=true; p=p.parentElement; }}
      if(item.textContent.trim().startsWith("📄")) count++;
    }}
  }});
  document.getElementById("results").textContent = `📄 ${{count}} Treffer`;
}}
// Accordion: nur Geschwister im gleichen <ul> schließen, nur bei echtem Klick
document.querySelectorAll("summary").forEach(summary=>{{
  summary.addEventListener("click",function() {{
    const detail = this.parentElement, li=detail.parentElement, ul=li.parentElement;
    setTimeout(()=>{{
      if(!detail.open) return;
      Array.from(ul.children).forEach(sibLi=>{{
        if(sibLi===li) return;
        const sibDetail = sibLi.querySelector("details");
        if(sibDetail) sibDetail.open=false;
      }});
    }},0);
  }});
}});
</script>
</body></html>"""

        # schreiben + öffnen
        with open(outpath, "w", encoding="utf-8") as f:
            f.write(html_content)
        print(f"📝 HTML-Datei erzeugt als: {outpath}")        
        print("\n🌐 Öffne HTML-Datei im Standardbrowser…")
        webbrowser.open(f"file://{outpath}", new=0)
        # Konsole wieder in den Vordergrund holen
        if sys.platform.startswith("win"):
            time.sleep(1)
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 5)  # SW_SHOW
                ctypes.windll.user32.SetForegroundWindow(hwnd)
        input("✅ Fertig. Drücke Enter zum Beenden…")

    except Exception as e:
        print("❌ Fehler:", e)
        traceback.print_exc()
        input("🔒 Drücke Enter zum Beenden…")

if __name__ == "__main__":
    main()
