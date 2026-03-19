# ============================================================
#  app.py — Word Frequency Analyzer  (Free Translation Edition)
#  สำหรับนักแปลมืออาชีพ
#  รัน:   streamlit run app.py
#  แปลภาษา: ไม่ต้อง API key — ใช้ deep-translator library
#            รองรับ Google Translate / MyMemory / LibreTranslate
# ============================================================

import io, re, collections
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# ── auto-install dependencies ─────────────────────────────────
import subprocess, sys

def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

try:
    import docx
except ImportError:
    pip_install("python-docx")
    import docx

try:
    from deep_translator import GoogleTranslator, MyMemoryTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    pip_install("deep-translator")
    try:
        from deep_translator import GoogleTranslator, MyMemoryTranslator
        TRANSLATOR_AVAILABLE = True
    except Exception:
        TRANSLATOR_AVAILABLE = False

# ============================================================
# SECTION 1 — Page config & CSS
# ============================================================
st.set_page_config(
    page_title="Word Frequency Analyzer",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600&family=JetBrains+Mono:wght@400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Thai', sans-serif;
    background: #0b0e18 !important; color: #d4ddf5;
}
.stApp { background: #0b0e18; }
[data-testid="stSidebar"] { background:#0f1322 !important; border-right:1px solid #1e2540; }
[data-testid="stSidebar"] * { color:#a8b4d4 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color:#c8d4f0 !important; }

.hero {
    background:linear-gradient(135deg,#111830 0%,#0d1628 50%,#131c38 100%);
    border:1px solid #1e2d54; border-radius:16px;
    padding:2rem 2.5rem 1.6rem; margin-bottom:1.8rem;
    position:relative; overflow:hidden;
}
.hero::after {
    content:''; position:absolute; top:-40px; right:-40px;
    width:240px; height:240px; border-radius:50%;
    background:radial-gradient(circle,rgba(80,120,255,.10) 0%,transparent 70%);
    pointer-events:none;
}
.hero-eyebrow {
    font-family:'JetBrains Mono',monospace; font-size:.7rem;
    letter-spacing:.2em; text-transform:uppercase; color:#4e6aaa; margin:0 0 .4rem;
}
.hero-title { font-size:1.7rem; font-weight:600; color:#c8d8ff; margin:0 0 .3rem; }
.hero-sub   { color:#6a7a9a; font-size:.88rem; margin:0; }
.free-badge {
    display:inline-block; background:rgba(50,180,100,.12);
    border:1px solid rgba(50,180,100,.3); color:#50b878;
    font-family:'JetBrains Mono',monospace; font-size:.68rem;
    padding:2px 10px; border-radius:20px; margin-top:.6rem;
}

.sec-label {
    font-family:'JetBrains Mono',monospace; font-size:.66rem; font-weight:600;
    letter-spacing:.18em; text-transform:uppercase; color:#3d5488;
    border-left:3px solid #2a3d70; padding-left:.6rem; margin:1.8rem 0 .9rem;
}

.cards { display:flex; gap:.9rem; margin-bottom:1.5rem; flex-wrap:wrap; }
.card {
    flex:1; min-width:120px; background:#111828;
    border:1px solid #1e2d50; border-radius:12px; padding:.9rem 1rem;
}
.card-icon  { font-size:1.1rem; margin-bottom:.25rem; }
.card-label { color:#4e6088; font-size:.7rem; margin:0 0 .1rem; }
.card-value { font-family:'JetBrains Mono',monospace; font-size:1.35rem; font-weight:600; color:#a8c0ff; margin:0; }
.card-sub   { font-size:.66rem; color:#3d5070; margin-top:.1rem; }

.freq-table { width:100%; border-collapse:collapse; }
.freq-table th {
    color:#3d5488; font-size:.67rem; letter-spacing:.12em; text-transform:uppercase;
    font-weight:600; padding:.45rem .7rem; border-bottom:1px solid #1a2340; text-align:left;
}
.freq-table td { padding:.32rem .7rem; font-size:.85rem; color:#a0b0cc; border-bottom:1px solid #111828; }
.freq-table tr:hover td { background:#111828; }
.rank-num   { font-family:'JetBrains Mono',monospace; font-size:.72rem; color:#3a4e78; }
.count-cell { font-family:'JetBrains Mono',monospace; font-size:.8rem; color:#7a9acc; }
.pct-cell   { font-family:'JetBrains Mono',monospace; font-size:.75rem; color:#4e6488; }
.bar-track  { background:#131c30; border-radius:4px; height:5px; width:80px; }
.bar-fill   { border-radius:4px; height:5px; }

.ctx-panel {
    background:#0d1320; border:1px solid #1e2e58;
    border-radius:14px; padding:1.3rem 1.5rem;
}
.ctx-word { font-family:'JetBrains Mono',monospace; font-size:1.35rem; font-weight:700; color:#7aadff; }
.ctx-meta { font-size:.75rem; color:#3d5488; margin-bottom:.9rem; }
.ctx-sentence-wrap { margin-bottom:.55rem; }
.ctx-sent-num { font-family:'JetBrains Mono',monospace; font-size:.62rem; color:#2a3d60; margin-bottom:.18rem; }
.ctx-sentence {
    background:#111828; border-left:3px solid #2a4080;
    border-radius:0 8px 8px 0; padding:.65rem .95rem;
    font-size:.88rem; color:#8a9ab8; line-height:1.7;
}
.ctx-sentence mark {
    background:rgba(80,150,255,.22); color:#90c4ff;
    border-radius:3px; padding:0 2px; font-weight:700;
}
.ctx-more { color:#2a3d60; font-size:.75rem; text-align:center; padding:.4rem; font-style:italic; }

/* translation result panel */
.trans-panel {
    background:#0a1614; border:1px solid #183028;
    border-radius:14px; padding:1.2rem 1.5rem;
}
.trans-engine-tag {
    font-family:'JetBrains Mono',monospace; font-size:.65rem; letter-spacing:.15em;
    text-transform:uppercase; color:#3a7060; margin-bottom:.7rem;
    display:flex; align-items:center; gap:.4rem; flex-wrap:wrap;
}
.engine-badge {
    background:rgba(50,180,100,.12); border:1px solid rgba(50,180,100,.25);
    color:#40a864; font-size:.62rem; font-family:'JetBrains Mono',monospace;
    padding:1px 8px; border-radius:20px;
}
.trans-main { font-size:1.3rem; font-weight:700; color:#6dcba8; margin:.3rem 0; }
.trans-divider { border:none; border-top:1px solid #1a3028; margin:.8rem 0; }
.trans-ctx-label {
    font-size:.68rem; color:#3a6050; text-transform:uppercase;
    letter-spacing:.1em; margin-bottom:.5rem;
}
.trans-ctx-item {
    border-left:3px solid #1a4a38; padding:.5rem .85rem;
    margin-bottom:.45rem; font-size:.86rem; color:#5a9080;
    line-height:1.68; background:rgba(20,50,40,.3); border-radius:0 6px 6px 0;
}
.trans-ctx-orig {
    font-size:.75rem; color:#2a5040; font-style:italic; margin-bottom:.2rem;
}
.trans-note { font-size:.76rem; color:#2a5040; font-style:italic; margin-top:.6rem; }
.trans-error {
    color:#884444; font-size:.85rem; background:#1a1010;
    border:1px solid #3a2020; border-radius:8px; padding:.7rem 1rem;
}
.trans-no-key {
    text-align:center; color:#3a5040; padding:1.5rem;
    font-size:.88rem;
}

[data-testid="stFileUploader"] {
    background:#0f1728 !important; border:2px dashed #1e2d50 !important; border-radius:12px !important;
}
.stDownloadButton > button {
    background:linear-gradient(135deg,#1e3070,#2a44a0) !important;
    color:#c8d8ff !important; border:1px solid #2a44a0 !important;
    border-radius:8px !important; font-weight:600 !important;
    font-family:'IBM Plex Sans Thai',sans-serif !important; padding:.45rem 1.2rem !important;
}
[data-testid="stExpander"] { background:#0f1322; border:1px solid #1a2540; border-radius:10px; }
.stTextArea textarea {
    background:#0f1728 !important; color:#a0b4cc !important;
    border:1px solid #1e2d50 !important;
    font-family:'JetBrains Mono',monospace !important; font-size:.8rem !important;
}
.info-box {
    background:#0f1728; border:1px solid #1a2d50; border-radius:10px;
    padding:1.1rem 1.4rem; color:#5a7090; font-size:.88rem; text-align:center;
}
::-webkit-scrollbar { width:5px; } 
::-webkit-scrollbar-track { background:#0b0e18; }
::-webkit-scrollbar-thumb { background:#1e2d50; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# SECTION 2 — Stopwords
# ============================================================
ENGLISH_STOPWORDS = {
    "a","an","the","this","that","these","those","some","any","each",
    "every","either","neither","all","both","few","more","most","much",
    "many","other","another","such","no","own","same","enough",
    "in","on","at","to","for","of","with","by","from","about","above",
    "after","before","between","into","through","during","until","against",
    "along","among","around","behind","below","beside","beyond","but",
    "down","except","inside","near","off","onto","out","outside",
    "over","past","since","than","under","up","upon","via",
    "within","without","toward","towards",
    "and","or","nor","so","yet","although","because","if","unless",
    "while","whereas","whether","though","even","once","when","where","as",
    "i","you","he","she","it","we","they","me","him","her","us","them",
    "my","your","his","its","our","their","mine","yours","hers","ours",
    "theirs","myself","yourself","himself","herself","itself","ourselves",
    "themselves","who","whom","whose","which","what",
    "is","are","was","were","be","been","being","have","has","had",
    "do","does","did","will","would","could","should","may","might",
    "shall","can","need","ought","used","let","get","got","go","came",
    "come","went","make","made","see","say","said","know","think","take",
    "give","find","tell","ask","seem","feel","try","leave","call","keep",
    "put","set","become","show","hear","run","bring","hold",
    "not","just","also","too","very","well","now","then","here","there",
    "why","how","still","already","always","never","ever",
    "often","sometimes","usually","however","therefore","thus","hence",
    "indeed","else","instead","rather","quite","almost","again","back",
    "further","maybe","perhaps","really","only","yet","soon",
    "later","early","twice","first","second","last",
    "s","t","re","ve","ll","d","m","n","e","o","p","r","c","x",
    "g","h","y","z","w","f","v","k","j","q","u","b",
}

PALETTES = {
    "💙 Ocean Blue":  ["#1a3a7a","#2a5aaa","#4a7acc","#6a9add","#8abcee","#aad4ff"],
    "💜 Violet Dusk": ["#2a1a5a","#4a2a8a","#6a3aaa","#8a4acc","#aa6add","#cc8aee"],
    "🩵 Cyan Frost":  ["#0a3a4a","#1a5a6a","#2a7a8a","#3a9aaa","#4ab4cc","#6ad0ee"],
    "🧡 Ember":       ["#4a1a0a","#7a2a10","#aa4020","#cc6030","#dd8040","#eea060"],
    "💚 Moss":        ["#0a2a1a","#1a4a2a","#2a6a3a","#3a8a4a","#4aaa5a","#6acc70"],
    "⬜ Mono":        ["#1a2030","#2a3040","#3a4050","#5a6070","#7a8090","#9aa0b0"],
}

# ============================================================
# SECTION 3 — Translation engines (ไม่ต้อง API key)
# ============================================================
ENGINES = {
    "🌐 Google Translate (แนะนำ)": "google",
    "💾 MyMemory (สำรอง)":        "mymemory",
}

def translate_word(word: str, src: str, tgt: str, engine: str) -> str:
    """
    แปลคำเดี่ยว — ไม่ต้อง API key
    src/tgt: 'en' หรือ 'th'
    """
    if not TRANSLATOR_AVAILABLE:
        raise RuntimeError("deep-translator ไม่พร้อมใช้งาน")

    if engine == "google":
        result = GoogleTranslator(source=src, target=tgt).translate(word)
    elif engine == "mymemory":
        lang_map = {"en": "en-US", "th": "th-TH"}
        result = MyMemoryTranslator(
            source=lang_map.get(src, src),
            target=lang_map.get(tgt, tgt)
        ).translate(word)
    else:
        result = GoogleTranslator(source=src, target=tgt).translate(word)
    return result or ""


def translate_sentence(sentence: str, src: str, tgt: str, engine: str) -> str:
    """แปลประโยค — ตัดคำ HTML tag ออกก่อน แล้วแปล"""
    clean = re.sub(r'<[^>]+>', '', sentence).strip()
    if not clean:
        return ""
    # จำกัดความยาวเพื่อไม่เกิน limit ของแต่ละ engine
    clean = clean[:400]
    return translate_word(clean, src, tgt, engine)


def translate_all(word: str, ctx_list: list, src: str, tgt: str, engine: str) -> dict:
    """
    แปลคำ + ประโยคบริบท
    คืน dict: main, context_translations (list of dict orig/trans), note
    """
    main = translate_word(word, src, tgt, engine)

    ctx_trans = []
    for sent_html in ctx_list[:4]:   # แปลแค่ 4 ประโยคแรก
        orig  = re.sub(r'<[^>]+>', '', sent_html).strip()
        trans = translate_sentence(sent_html, src, tgt, engine)
        ctx_trans.append({"orig": orig, "trans": trans})

    # หมายเหตุสั้นๆ ตาม engine
    notes = {
        "google":   "แปลโดย Google Translate · ฟรี ไม่จำกัด · ควรตรวจทานคำแปลบริบทเฉพาะทาง",
        "mymemory": "แปลโดย MyMemory · ฟรี 500 คำ/วัน · เหมาะกับงานทั่วไป",
    }
    return {"main": main, "context_translations": ctx_trans,
            "note": notes.get(engine, "")}

# ============================================================
# SECTION 4 — File / Language / Tokenize helpers
# ============================================================
def read_file(uploaded) -> str:
    raw = uploaded.read()
    ext = uploaded.name.rsplit(".", 1)[-1].lower()
    if ext == "docx":
        doc = docx.Document(io.BytesIO(raw))
        return "\n".join(p.text for p in doc.paragraphs)
    for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def detect_language(text: str) -> str:
    thai  = len(re.findall(r'[\u0e00-\u0e7f]', text))
    latin = len(re.findall(r'[a-zA-Z]', text))
    return 'th' if thai > latin * 0.3 else 'en'


def tokenize_en(text: str, min_len: int) -> list:
    tokens = re.findall(r"[a-zA-Z']+", text)
    return [t.strip("'").lower() for t in tokens if len(t.strip("'")) >= min_len]


def tokenize_th(text: str, min_len: int) -> list:
    tokens = re.findall(r'[\u0e00-\u0e7f]+', text)
    return [t for t in tokens if len(t) >= min_len]


def build_freq_df(tokens: list) -> pd.DataFrame:
    counter = collections.Counter(tokens)
    total   = sum(counter.values()) or 1
    rows = [{"คำ": w, "จำนวนครั้ง": c, "สัดส่วน (%)": round(c / total * 100, 2)}
            for w, c in counter.most_common()]
    df = pd.DataFrame(rows)
    df.index = range(1, len(df) + 1)
    df.index.name = "อันดับ"
    return df

# ============================================================
# SECTION 5 — Context extraction
# ============================================================
def split_sentences(text: str, lang: str) -> list:
    if lang == 'en':
        sents = re.split(r'(?<=[.!?])\s+', text)
    else:
        sents = re.split(r'(?<=[.!?ฯ])\s*\n*|\n{2,}', text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def get_contexts(word: str, sentences: list, lang: str, max_ctx: int = 6) -> list:
    pattern = re.compile(
        r'\b' + re.escape(word) + r'\b' if lang == 'en' else re.escape(word),
        re.IGNORECASE,
    )
    results = []
    for sent in sentences:
        if pattern.search(sent):
            highlighted = pattern.sub(lambda m: f'<mark>{m.group(0)}</mark>', sent)
            results.append(highlighted)
            if len(results) >= max_ctx:
                break
    return results

# ============================================================
# SECTION 6 — Chart builder
# ============================================================
def build_chart(df_top: pd.DataFrame, palette_name: str) -> plt.Figure:
    colors = PALETTES[palette_name]
    n      = len(df_top)
    fig, ax = plt.subplots(figsize=(9, max(4.5, n * 0.36)))
    fig.patch.set_facecolor("#0f1322")
    ax.set_facecolor("#0f1322")
    bar_colors = list(reversed([mcolors.to_rgba(colors[i % len(colors)]) for i in range(n)]))
    words_rev  = list(df_top["คำ"])[::-1]
    counts_rev = list(df_top["จำนวนครั้ง"])[::-1]
    bars = ax.barh(words_rev, counts_rev, color=bar_colors, edgecolor="none", height=0.62)
    max_val = max(counts_rev) if counts_rev else 1
    for bar, val in zip(bars, counts_rev):
        ax.text(bar.get_width() + max_val * 0.012,
                bar.get_y() + bar.get_height() / 2,
                f"{val:,}", va="center", ha="left",
                color="#8aaad0", fontsize=8, fontfamily="monospace")
    ax.set_xlim(0, max_val * 1.18)
    ax.set_xlabel("จำนวนครั้ง", color="#3d5488", fontsize=9)
    ax.tick_params(colors="#5a7090", labelsize=8.5)
    ax.spines[:].set_visible(False)
    ax.xaxis.set_tick_params(length=0); ax.yaxis.set_tick_params(length=0)
    ax.grid(axis="x", color="#1a2540", linewidth=0.7)
    fig.tight_layout(pad=1.4)
    return fig

# ============================================================
# SECTION 7 — HTML renderers
# ============================================================
def build_progress_table(df, top_n, palette_name, selected="") -> str:
    subset  = df.head(top_n)
    max_pct = subset["สัดส่วน (%)"].max() if len(subset) else 1
    accent  = PALETTES[palette_name][2]
    rows = ""
    for rank, row in subset.iterrows():
        pct   = row["สัดส่วน (%)"]
        bar_w = int(pct / max_pct * 100) if max_pct else 0
        word  = row["คำ"]
        wcls  = 'word-active' if word == selected else ''
        wclr  = '#80b4ff' if word == selected else '#c0d0f0'
        rows += f"""
        <tr>
          <td><span class="rank-num">#{rank:02d}</span></td>
          <td><span class="{wcls}" style="color:{wclr};font-weight:{'700' if word==selected else '400'}">{word}</span></td>
          <td><span class="count-cell">{int(row['จำนวนครั้ง']):,}</span></td>
          <td><span class="pct-cell">{pct:.2f}%</span></td>
          <td><div class="bar-track"><div class="bar-fill" style="width:{bar_w}%;background:{accent};"></div></div></td>
        </tr>"""
    return f"""<table class="freq-table">
      <thead><tr><th>#</th><th>คำ</th><th>จำนวน</th><th>%</th><th>สัดส่วน</th></tr></thead>
      <tbody>{rows}</tbody></table>"""


def render_context_panel(word, ctx_list, freq, pct) -> str:
    if not ctx_list:
        return f'<div class="ctx-panel"><div class="ctx-word">"{word}"</div><div class="ctx-meta">ไม่พบบริบทในเอกสาร</div></div>'
    items = "".join(f"""
        <div class="ctx-sentence-wrap">
          <div class="ctx-sent-num">ประโยคที่ {i+1}</div>
          <div class="ctx-sentence">{h}</div>
        </div>""" for i, h in enumerate(ctx_list))
    more = f'<div class="ctx-more">… และอีก {freq - len(ctx_list)} ครั้งในเอกสาร</div>' if freq > len(ctx_list) else ""
    return f"""<div class="ctx-panel">
      <div style="display:flex;align-items:baseline;gap:.7rem;margin-bottom:.8rem;">
        <span class="ctx-word">"{word}"</span>
        <span class="ctx-meta">พบ {freq:,} ครั้ง ({pct:.2f}%) · แสดง {len(ctx_list)} บริบท</span>
      </div>{items}{more}</div>"""


def render_trans_panel(word, result, src_lang, engine_key) -> str:
    engine_names = {"google": "Google Translate", "mymemory": "MyMemory"}
    engine_name  = engine_names.get(engine_key, engine_key)
    tgt_label    = "ไทย" if src_lang == 'en' else "English"

    ctx_items = ""
    for c in result.get("context_translations", []):
        ctx_items += f"""
        <div class="trans-ctx-item">
          <div class="trans-ctx-orig">📄 {c['orig'][:120]}{'…' if len(c['orig'])>120 else ''}</div>
          <div>🔁 {c['trans']}</div>
        </div>"""

    note = result.get("note", "")
    return f"""<div class="trans-panel">
      <div class="trans-engine-tag">
        🔤 แปล → {tgt_label}
        <span class="engine-badge">✓ {engine_name}</span>
        <span class="engine-badge" style="color:#3a8060;border-color:rgba(50,180,100,.2);">FREE</span>
      </div>
      <div class="trans-main">{result.get('main','—')}</div>
      <hr class="trans-divider">
      <div class="trans-ctx-label">บริบทที่แปลแล้ว</div>
      {ctx_items if ctx_items else '<div class="trans-ctx-item" style="color:#2a5040;">ไม่มีบริบท</div>'}
      {f'<div class="trans-note">💡 {note}</div>' if note else ''}
    </div>"""


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.reset_index().to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

# ============================================================
# SECTION 8 — Hero
# ============================================================
st.markdown("""
<div class="hero">
  <p class="hero-eyebrow">translator toolkit · context-aware · free translation</p>
  <p class="hero-title">📖 Word Frequency Analyzer</p>
  <p class="hero-sub">วิเคราะห์ความถี่คำ · ดูบริบท · แปลภาษาอัตโนมัติ — สำหรับนักแปลมืออาชีพ</p>
  <span class="free-badge">✓ ไม่ต้อง API key · ใช้ได้ฟรีทันที</span>
</div>
""", unsafe_allow_html=True)

# ============================================================
# SECTION 9 — Sidebar
# ============================================================
with st.sidebar:
    st.markdown("## ⚙️ ตั้งค่า")
    st.markdown("---")

    top_n   = st.slider("🏆 แสดง Top N คำ", 5, 50, 20, 5)
    min_len = st.slider("🔡 ความยาวคำขั้นต่ำ", 1, 6, 2)
    use_sw  = st.toggle("🚫 กรอง Stopwords", value=True)

    extra_sw: set = set()
    if use_sw:
        extra_raw = st.text_area(
            "➕ Stopwords เพิ่มเติม (คั่น , หรือ Enter)",
            placeholder="chapter, figure, table",
            height=75,
        )
        extra_sw = {w.strip().lower() for w in re.split(r"[,\n]+", extra_raw) if w.strip()}

    max_ctx = st.slider("📄 บริบทสูงสุด", 3, 12, 5)

    st.markdown("---")
    palette = st.selectbox("🎨 สีแผนภูมิ", list(PALETTES.keys()), index=0)

    st.markdown("---")
    st.markdown("### 🔤 Translation Engine")

    engine_label = st.selectbox(
        "เลือก Translation Engine",
        list(ENGINES.keys()),
        index=0,
        help="ทุก engine ใช้ฟรี ไม่ต้อง API key",
    )
    engine_key = ENGINES[engine_label]

    # แสดง info แต่ละ engine
    engine_info = {
        "google":   ("Google Translate", "ฟรี · แม่นยำสูง · รองรับ 100+ ภาษา", "🟢"),
        "mymemory": ("MyMemory",         "ฟรี ~500 คำ/วัน · เน้นงานแปลอาชีพ",   "🟡"),
    }
    icon, name, desc = engine_info[engine_key][2], engine_info[engine_key][0], engine_info[engine_key][1]
    st.markdown(f"""
    <div style="background:#111828;border:1px solid #1e2d50;border-radius:8px;padding:.7rem .9rem;margin-top:.3rem;">
      <div style="color:#4a9060;font-size:.7rem;font-family:'JetBrains Mono',monospace;">
        {icon} {name}
      </div>
      <div style="color:#4e6088;font-size:.75rem;margin-top:.2rem;">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

    if not TRANSLATOR_AVAILABLE:
        st.error("⚠️ deep-translator ยังไม่ติดตั้ง — รีสตาร์ท app")

    st.markdown("---")
    st.markdown("""
**รองรับ:** `.txt` · `.docx`  
**ภาษา:** อังกฤษ / ไทย (auto-detect)  
**Translation:** ฟรี ไม่ต้อง key
""")

# ============================================================
# SECTION 10 — File Upload
# ============================================================
st.markdown('<p class="sec-label">01 — อัปโหลดเอกสาร</p>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "ลากไฟล์มาวาง หรือคลิกเพื่อเลือก (.txt · .docx)",
    type=["txt", "docx"],
    label_visibility="collapsed",
)

# ============================================================
# SECTION 11 — Main processing
# ============================================================
if uploaded:
    with st.spinner("⏳ กำลังอ่านและวิเคราะห์ไฟล์..."):
        try:
            raw_text = read_file(uploaded)
            lang     = detect_language(raw_text)
            if lang == 'en':
                active_sw  = (ENGLISH_STOPWORDS | extra_sw) if use_sw else set()
                all_tokens = tokenize_en(raw_text, min_len)
            else:
                active_sw  = set()
                all_tokens = tokenize_th(raw_text, min_len)
            filt_tokens = [t for t in all_tokens if t not in active_sw]
            freq_df     = build_freq_df(filt_tokens)
            sentences   = split_sentences(raw_text, lang)
        except Exception as e:
            st.error(f"❌ ไม่สามารถอ่านไฟล์: {e}")
            st.stop()

    lang_label   = "🇬🇧 English" if lang == 'en' else "🇹🇭 ภาษาไทย"
    raw_count    = len(all_tokens)
    filt_count   = len(filt_tokens)
    unique_count = len(freq_df)

    # Metric cards
    st.markdown('<p class="sec-label">02 — ภาพรวมเอกสาร</p>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="cards">
      <div class="card"><div class="card-icon">📄</div><p class="card-label">ไฟล์</p>
        <p class="card-value" style="font-size:.78rem;line-height:1.3;">{uploaded.name}</p></div>
      <div class="card"><div class="card-icon">🌐</div><p class="card-label">ภาษา</p>
        <p class="card-value" style="font-size:.85rem;">{lang_label}</p></div>
      <div class="card"><div class="card-icon">🔤</div><p class="card-label">คำทั้งหมด</p>
        <p class="card-value">{raw_count:,}</p><p class="card-sub">raw tokens</p></div>
      <div class="card"><div class="card-icon">✅</div><p class="card-label">หลังกรอง</p>
        <p class="card-value">{filt_count:,}</p><p class="card-sub">−{raw_count-filt_count:,} SW</p></div>
      <div class="card"><div class="card-icon">🗂️</div><p class="card-label">คำไม่ซ้ำ</p>
        <p class="card-value">{unique_count:,}</p></div>
      <div class="card"><div class="card-icon">📝</div><p class="card-label">ประโยค</p>
        <p class="card-value">{len(sentences):,}</p></div>
    </div>""", unsafe_allow_html=True)

    # Chart + Table
    st.markdown('<p class="sec-label">03 — แผนภูมิและตารางความถี่</p>', unsafe_allow_html=True)
    df_top   = freq_df.head(top_n)
    selected = st.session_state.get("selected_word", "")

    c_chart, c_table = st.columns([1.15, 1], gap="large")
    with c_chart:
        st.markdown("**📊 Bar Chart**")
        fig = build_chart(df_top, palette)
        st.pyplot(fig, use_container_width=True); plt.close(fig)
    with c_table:
        st.markdown("**📋 ตารางสัดส่วน**")
        st.markdown(build_progress_table(freq_df, top_n, palette, selected),
                    unsafe_allow_html=True)

    # Word selector buttons
    st.markdown('<p class="sec-label">04 — คลิกคำเพื่อดูบริบทและแปล</p>', unsafe_allow_html=True)
    st.markdown(
        f"<div style='color:#3d5488;font-size:.78rem;margin-bottom:.6rem;'>"
        f"เลือกคำจาก Top {top_n} · คลิกซ้ำเพื่อยกเลิก</div>",
        unsafe_allow_html=True,
    )

    words_list = list(df_top["คำ"])
    for row_i in range(0, len(words_list), 6):
        btn_cols = st.columns(6)
        for ci, word in enumerate(words_list[row_i: row_i + 6]):
            freq_val = int(df_top.loc[df_top["คำ"] == word, "จำนวนครั้ง"].values[0])
            is_sel   = selected == word
            if btn_cols[ci].button(
                f"**{word}**" if is_sel else word,
                key=f"wb_{word}",
                help=f"{word}: {freq_val:,} ครั้ง",
                use_container_width=True,
            ):
                if is_sel:
                    st.session_state.selected_word  = ""
                    st.session_state.trans_result   = None
                    st.session_state.trans_word     = ""
                else:
                    st.session_state.selected_word  = word
                    st.session_state.trans_result   = None
                    st.session_state.trans_word     = ""
                st.rerun()

    # Context + Translation panel
    selected_word = st.session_state.get("selected_word", "")
    if selected_word:
        st.markdown('<p class="sec-label">05 — บริบทและคำแปล</p>', unsafe_allow_html=True)

        row_data = freq_df[freq_df["คำ"] == selected_word]
        freq_val = int(row_data["จำนวนครั้ง"].values[0]) if len(row_data) else 0
        pct_val  = float(row_data["สัดส่วน (%)"].values[0]) if len(row_data) else 0.0
        ctx_list = get_contexts(selected_word, sentences, lang, max_ctx)

        tgt_lang = "th" if lang == "en" else "en"

        c_ctx, c_trans = st.columns([1.1, 1], gap="large")

        with c_ctx:
            tgt_label = "ไทย" if lang == "en" else "English"
            st.markdown("**🔍 บริบทในต้นฉบับ**")
            st.markdown(render_context_panel(selected_word, ctx_list, freq_val, pct_val),
                        unsafe_allow_html=True)

        with c_trans:
            st.markdown(f"**🔤 คำแปล → {tgt_label}**")

            # ดึง cache หรือแปลใหม่
            cached      = st.session_state.get("trans_result")
            cached_word = st.session_state.get("trans_word", "")
            cached_eng  = st.session_state.get("trans_engine", "")

            need_retrans = (
                cached is None
                or cached_word != selected_word
                or cached_eng  != engine_key
            )

            if need_retrans:
                with st.spinner(f"🔤 กำลังแปล "{selected_word}" ..."):
                    try:
                        result = translate_all(
                            word     = selected_word,
                            ctx_list = ctx_list,
                            src      = lang,
                            tgt      = tgt_lang,
                            engine   = engine_key,
                        )
                        st.session_state.trans_result = result
                        st.session_state.trans_word   = selected_word
                        st.session_state.trans_engine = engine_key
                    except Exception as e:
                        st.markdown(
                            f'<div class="trans-panel"><div class="trans-error">❌ แปลไม่สำเร็จ: {e}<br>'
                            f'<span style="font-size:.75rem;color:#664444;">ลองเปลี่ยน engine หรือตรวจสอบ connection</span></div></div>',
                            unsafe_allow_html=True,
                        )
                        result = None
            else:
                result = cached

            if result:
                st.markdown(render_trans_panel(selected_word, result, lang, engine_key),
                            unsafe_allow_html=True)

            # ปุ่มสลับ engine และ refresh
            btn_c1, btn_c2 = st.columns(2)
            with btn_c1:
                if st.button("🔄 แปลใหม่", key="retrans", use_container_width=True):
                    st.session_state.trans_result = None
                    st.rerun()
            with btn_c2:
                other_engines = [k for k, v in ENGINES.items() if v != engine_key]
                if other_engines and st.button("⇄ สลับ Engine", key="sweng", use_container_width=True):
                    # สลับ engine — user ต้องเปลี่ยนใน sidebar แต่นี่เป็น hint
                    st.info("💡 เปลี่ยน engine ได้ที่ sidebar ด้านซ้าย")

    # Download
    st.markdown('<p class="sec-label">06 — ดาวน์โหลด</p>', unsafe_allow_html=True)
    base = uploaded.name.rsplit(".", 1)[0]
    dc1, dc2, dc3 = st.columns([1, 1, 2], gap="medium")
    with dc1:
        st.download_button("⬇️ CSV — ทุกคำ", data=to_csv_bytes(freq_df),
                           file_name=f"{base}_all_words.csv", mime="text/csv",
                           use_container_width=True)
    with dc2:
        st.download_button(f"⬇️ CSV — Top {min(top_n,unique_count)}", data=to_csv_bytes(df_top),
                           file_name=f"{base}_top{top_n}.csv", mime="text/csv",
                           use_container_width=True)
    with dc3:
        st.markdown(
            "<div style='color:#3d5488;font-size:.76rem;padding:.4rem 0;'>"
            "คอลัมน์: <code>อันดับ · คำ · จำนวนครั้ง · สัดส่วน (%)</code><br>"
            "Encoding: UTF-8 BOM — เปิดใน Excel ได้ทันที</div>",
            unsafe_allow_html=True,
        )

    # Preview
    st.markdown('<p class="sec-label">07 — ข้อความต้นฉบับ</p>', unsafe_allow_html=True)
    with st.expander("📝 แสดงข้อความต้นฉบับ"):
        preview = raw_text[:2000] + (f"\n\n… [{len(raw_text):,} ตัวอักษร]" if len(raw_text) > 2000 else "")
        st.text(preview)

else:
    st.markdown("""
    <div class="info-box">
      📂 กรุณาอัปโหลดไฟล์ <strong>.txt</strong> หรือ <strong>.docx</strong><br>
      <span style="font-size:.78rem;color:#3d5070;">
      รองรับ ภาษาอังกฤษ & ไทย · แปลภาษาฟรีด้วย Google Translate / MyMemory
      </span>
    </div>""", unsafe_allow_html=True)

    # Demo
    st.markdown('<p class="sec-label">ตัวอย่างผลลัพธ์</p>', unsafe_allow_html=True)
    dw = ["translation","language","context","meaning","phrase","source","target","register","nuance","fluency"]
    dc = [84,71,60,46,41,36,32,24,18,12]
    td = sum(dc)
    ddf = pd.DataFrame({"คำ":dw,"จำนวนครั้ง":dc,"สัดส่วน (%)":[round(c/td*100,2) for c in dc]})
    ddf.index = range(1,len(ddf)+1); ddf.index.name="อันดับ"
    dd1, dd2 = st.columns([1.15,1], gap="large")
    with dd1:
        fig_d = build_chart(ddf, palette)
        st.pyplot(fig_d, use_container_width=True); plt.close(fig_d)
    with dd2:
        st.markdown(build_progress_table(ddf, 10, palette), unsafe_allow_html=True)
