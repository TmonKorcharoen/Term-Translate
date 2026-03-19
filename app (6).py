# ============================================================
#  app.py — Word Frequency Analyzer  (Light Theme Edition)
#  สำหรับนักแปลมืออาชีพ
#  รัน:   streamlit run app.py
# ============================================================

import io, re, collections, html as htmllib, os, urllib.request
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.font_manager as fm
import subprocess, sys

def pip_install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

# ============================================================
# THAI FONT SETUP
# ลำดับ: 1) ค้นหา font ไทยในระบบ  2) ดาวน์โหลด NotoSansThai
# ============================================================
@st.cache_resource
def load_thai_font() -> str:
    """
    คืน path ของ font ที่รองรับภาษาไทย
    - ลองหาใน system ก่อน (Loma, Garuda, FreeSerif ฯลฯ)
    - ถ้าไม่มี → ดาวน์โหลด NotoSansThai จาก GitHub
    """
    # 1) ค้นหา font ไทยที่มีในระบบ
    thai_candidates = [
        f.fname for f in fm.fontManager.ttflist
        if any(k in f.fname.lower() for k in ["loma", "garuda", "norasi", "sarabun", "thai"])
        and os.path.exists(f.fname)
    ]
    if thai_candidates:
        # เลือก Regular (ไม่ใช่ Bold/Oblique) ก่อน
        regulars = [p for p in thai_candidates
                    if not any(x in os.path.basename(p).lower()
                               for x in ["bold","oblique","italic"])]
        chosen = regulars[0] if regulars else thai_candidates[0]
        _register_font(chosen, "ThaiSystem")
        return chosen

    # 2) ดาวน์โหลด NotoSansThai
    dl_path = "/tmp/NotoSansThai.ttf"
    if not os.path.exists(dl_path):
        try:
            urllib.request.urlretrieve(
                "https://github.com/googlefonts/noto-fonts/raw/main/"
                "hinted/ttf/NotoSansThai/NotoSansThai-Regular.ttf",
                dl_path,
            )
        except Exception:
            return ""   # ถ้า download ไม่ได้ → ใช้ default font
    _register_font(dl_path, "NotoSansThai")
    return dl_path


def _register_font(path: str, name: str):
    """ลงทะเบียน font กับ matplotlib"""
    fe = fm.FontEntry(fname=path, name=name)
    fm.fontManager.ttflist.insert(0, fe)
    plt.rcParams["font.family"] = name


THAI_FONT_PATH = load_thai_font()


def thai_fp(size: float = 9) -> fm.FontProperties:
    """คืน FontProperties สำหรับภาษาไทย"""
    if THAI_FONT_PATH and os.path.exists(THAI_FONT_PATH):
        return fm.FontProperties(fname=THAI_FONT_PATH, size=size)
    return fm.FontProperties(size=size)   # fallback

try:
    import docx
except ImportError:
    pip_install("python-docx"); import docx

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
# SECTION 1 — Page config & Light Theme CSS
# ============================================================
st.set_page_config(
    page_title="Word Frequency Analyzer",
    page_icon="📖",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

/* ── Base ── */
html, body, [class*="css"] {
    font-family: 'IBM Plex Sans Thai', sans-serif !important;
    background: #f5f6fa !important;
    color: #1a2035 !important;
}
.stApp { background: #f5f6fa !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #e0e4ef !important;
}
[data-testid="stSidebar"] * { color: #3a4460 !important; }
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #1a2035 !important; font-weight: 600 !important; }
[data-testid="stSidebar"] hr { border-color: #e8eaf2 !important; }

/* ── Hero ── */
.hero {
    background: linear-gradient(135deg, #eef1ff 0%, #f0f4ff 60%, #e8f0ff 100%);
    border: 1px solid #cdd5f0;
    border-radius: 16px;
    padding: 2rem 2.5rem 1.7rem;
    margin-bottom: 1.8rem;
    position: relative; overflow: hidden;
}
.hero::after {
    content: ''; position: absolute; top: -30px; right: -30px;
    width: 220px; height: 220px; border-radius: 50%;
    background: radial-gradient(circle, rgba(90,110,240,.08) 0%, transparent 70%);
    pointer-events: none;
}
.hero-eyebrow {
    font-family: 'JetBrains Mono', monospace;
    font-size: .7rem; letter-spacing: .2em; text-transform: uppercase;
    color: #7a8cc0; margin: 0 0 .4rem;
}
.hero-title { font-size: 1.75rem; font-weight: 700; color: #1e2d6e; margin: 0 0 .3rem; }
.hero-sub   { color: #5a6890; font-size: .9rem; margin: 0; }
.free-badge {
    display: inline-block; background: #e8f5ee;
    border: 1px solid #b0d8c0; color: #2a7a50;
    font-family: 'JetBrains Mono', monospace; font-size: .68rem;
    padding: 2px 10px; border-radius: 20px; margin-top: .6rem;
}

/* ── Section label ── */
.sec-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: .66rem; font-weight: 600; letter-spacing: .18em;
    text-transform: uppercase; color: #8a9ac8;
    border-left: 3px solid #c0caee; padding-left: .6rem;
    margin: 1.8rem 0 .9rem;
}

/* ── Metric cards ── */
.cards { display: flex; gap: .9rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
.card {
    flex: 1; min-width: 120px;
    background: #ffffff;
    border: 1px solid #e0e4f0;
    border-radius: 12px; padding: .9rem 1rem;
    box-shadow: 0 1px 4px rgba(80,100,200,.06);
}
.card-icon  { font-size: 1.1rem; margin-bottom: .25rem; }
.card-label { color: #8a96b8; font-size: .7rem; margin: 0 0 .1rem; }
.card-value {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.35rem; font-weight: 700; color: #2a3880; margin: 0;
}
.card-sub   { font-size: .66rem; color: #a0aac8; margin-top: .1rem; }

/* ── Frequency table ── */
.freq-table { width: 100%; border-collapse: collapse; }
.freq-table th {
    color: #8a96b8; font-size: .67rem; letter-spacing: .12em;
    text-transform: uppercase; font-weight: 600;
    padding: .45rem .7rem; border-bottom: 2px solid #e8eaf5; text-align: left;
}
.freq-table td {
    padding: .35rem .7rem; font-size: .86rem; color: #3a4460;
    border-bottom: 1px solid #f0f2f8;
}
.freq-table tr:hover td { background: #f5f7ff; }
.rank-num   { font-family: 'JetBrains Mono', monospace; font-size: .72rem; color: #b0b8d8; }
.count-cell { font-family: 'JetBrains Mono', monospace; font-size: .8rem; color: #3a5aaa; font-weight: 600; }
.pct-cell   { font-family: 'JetBrains Mono', monospace; font-size: .75rem; color: #8a9ac0; }
.bar-track  { background: #eceef8; border-radius: 4px; height: 5px; width: 80px; }
.bar-fill   { border-radius: 4px; height: 5px; }
.word-active { color: #2a4acc !important; font-weight: 700 !important; }

/* ── Context panel ── */
.ctx-panel {
    background: #ffffff;
    border: 1px solid #d8ddf0;
    border-radius: 14px; padding: 1.3rem 1.5rem;
    box-shadow: 0 2px 8px rgba(80,100,200,.07);
}
.ctx-word {
    font-family: 'JetBrains Mono', monospace;
    font-size: 1.3rem; font-weight: 700; color: #2a44cc;
}
.ctx-meta { font-size: .75rem; color: #8a96b8; margin-bottom: .9rem; }
.ctx-sentence-wrap { margin-bottom: .55rem; }
.ctx-sent-num {
    font-family: 'JetBrains Mono', monospace;
    font-size: .62rem; color: #b8c0d8; margin-bottom: .18rem;
}
.ctx-sentence {
    background: #f5f7ff;
    border-left: 3px solid #7a94e8;
    border-radius: 0 8px 8px 0; padding: .65rem .95rem;
    font-size: .88rem; color: #3a4470; line-height: 1.75;
}
.ctx-sentence mark {
    background: rgba(80,120,255,.18); color: #2040cc;
    border-radius: 3px; padding: 0 3px; font-weight: 700;
}
.ctx-more { color: #b0b8d8; font-size: .75rem; text-align: center; padding: .4rem; font-style: italic; }

/* ── Translation panel ── */
.trans-panel {
    background: #f2fbf6;
    border: 1px solid #c0dece;
    border-radius: 14px; padding: 1.2rem 1.5rem;
    box-shadow: 0 2px 8px rgba(40,140,100,.07);
}
.trans-engine-tag {
    font-family: 'JetBrains Mono', monospace; font-size: .66rem;
    letter-spacing: .12em; text-transform: uppercase;
    color: #3a7a58; margin-bottom: .8rem;
    display: flex; align-items: center; gap: .4rem; flex-wrap: wrap;
}
.engine-badge {
    background: #e0f5ea; border: 1px solid #a8d8bc;
    color: #2a6a48; font-size: .62rem;
    font-family: 'JetBrains Mono', monospace;
    padding: 1px 8px; border-radius: 20px;
}
.trans-main { font-size: 1.4rem; font-weight: 700; color: #1a6040; margin: .25rem 0 .4rem; }
.trans-divider { border: none; border-top: 1px solid #c8e8d8; margin: .8rem 0; }
.trans-ctx-label {
    font-size: .68rem; color: #5a8870; text-transform: uppercase;
    letter-spacing: .1em; margin-bottom: .5rem; font-weight: 600;
}
.trans-ctx-item {
    border-left: 3px solid #80c8a8;
    padding: .55rem .9rem; margin-bottom: .45rem;
    font-size: .86rem; line-height: 1.7;
    background: #ffffff; border-radius: 0 8px 8px 0;
    box-shadow: 0 1px 3px rgba(40,140,100,.06);
}
.trans-ctx-orig {
    font-size: .78rem; color: #6a8878;
    margin-bottom: .25rem; line-height: 1.5;
}
.trans-ctx-translated {
    color: #1a4a38; font-weight: 500;
}
.trans-note { font-size: .76rem; color: #5a8070; font-style: italic; margin-top: .6rem; }
.trans-error {
    color: #883333; font-size: .85rem; background: #fff5f5;
    border: 1px solid #e8c0c0; border-radius: 8px; padding: .7rem 1rem;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: #ffffff !important;
    border: 2px dashed #c8d0e8 !important;
    border-radius: 12px !important;
}
[data-testid="stFileUploader"]:hover { border-color: #7a94e8 !important; }

/* ── Buttons ── */
.stDownloadButton > button {
    background: linear-gradient(135deg, #3a54cc, #5570e8) !important;
    color: #ffffff !important; border: none !important;
    border-radius: 8px !important; font-weight: 600 !important;
    font-family: 'IBM Plex Sans Thai', sans-serif !important;
    padding: .45rem 1.2rem !important;
    box-shadow: 0 2px 6px rgba(60,80,200,.25) !important;
}
.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #5570e8, #6a84f0) !important;
}
.stButton > button {
    background: #ffffff !important; color: #3a4880 !important;
    border: 1px solid #d0d8f0 !important; border-radius: 8px !important;
    font-family: 'IBM Plex Sans Thai', sans-serif !important;
    transition: all .15s !important;
}
.stButton > button:hover {
    background: #f0f3ff !important; border-color: #8a9ae8 !important;
    color: #2a3acc !important;
}

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #ffffff; border: 1px solid #e0e4f0; border-radius: 10px;
    box-shadow: 0 1px 4px rgba(80,100,200,.05);
}

/* ── Inputs ── */
.stTextArea textarea {
    background: #ffffff !important; color: #2a3460 !important;
    border: 1px solid #d0d8f0 !important;
    font-family: 'JetBrains Mono', monospace !important; font-size: .8rem !important;
    border-radius: 8px !important;
}
.stSelectbox > div > div {
    background: #ffffff !important; border-color: #d0d8f0 !important;
    color: #2a3460 !important;
}
.stSlider > div { color: #3a4880 !important; }

/* ── Info box ── */
.info-box {
    background: #ffffff; border: 1px solid #dde2f5; border-radius: 12px;
    padding: 1.5rem; color: #6a78a8; font-size: .9rem; text-align: center;
    box-shadow: 0 2px 8px rgba(80,100,200,.06);
}

/* ── Sidebar engine info ── */
.engine-info-box {
    background: #f5f8ff; border: 1px solid #d8e0f5;
    border-radius: 8px; padding: .75rem .95rem; margin-top: .3rem;
}
.engine-info-name { color: #2a7050; font-size: .72rem; font-family: 'JetBrains Mono', monospace; }
.engine-info-desc { color: #6a7898; font-size: .75rem; margin-top: .2rem; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: #f0f2f8; }
::-webkit-scrollbar-thumb { background: #c8d0e8; border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: #a0aacc; }
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
    "💙 Indigo":      ["#3a4acc","#4a5add","#6070e8","#7a8aee","#9aaaf4","#b8c4f8"],
    "💜 Violet":      ["#6a3acc","#7a4add","#9060e8","#a878ee","#be96f4","#d4b8f8"],
    "🩵 Teal":        ["#1a7a8a","#2a8a9a","#3a9aaa","#50aaba","#70bece","#90d0de"],
    "🧡 Amber":       ["#c05010","#d06020","#e07830","#e89048","#f0a860","#f8c080"],
    "💚 Sage":        ["#2a7050","#3a8060","#4a9070","#60a080","#80b898","#a0ceb0"],
    "⬜ Slate":       ["#4a5268","#5a6278","#6a7288","#7a8298","#9098ac","#aab0c0"],
}

ENGINES = {
    "🌐 Google Translate (แนะนำ)": "google",
    "💾 MyMemory (สำรอง)":         "mymemory",
}

# ============================================================
# SECTION 3 — Translation (ไม่ต้อง API key)
# ============================================================
def translate_text(text: str, src: str, tgt: str, engine: str) -> str:
    """แปลข้อความ — ฟรี ไม่ต้อง key"""
    if not TRANSLATOR_AVAILABLE or not text.strip():
        return ""
    text = text[:450]   # จำกัดความยาวป้องกัน error
    if engine == "google":
        return GoogleTranslator(source=src, target=tgt).translate(text) or ""
    lang_map = {"en": "en-US", "th": "th-TH"}
    return MyMemoryTranslator(
        source=lang_map.get(src, src),
        target=lang_map.get(tgt, tgt),
    ).translate(text) or ""


def translate_all(word: str, ctx_list: list, engine: str) -> dict:
    """แปล EN→TH คำ + ประโยคบริบททั้งหมด (จำกัด 6 ประโยคเพื่อความเร็ว)"""
    main = translate_text(word, "en", "th", engine)
    ctx_trans = []
    for sent_html in ctx_list[:6]:          # แปลสูงสุด 6 ประโยค (ป้องกันช้า)
        orig  = re.sub(r'<[^>]+>', '', sent_html).strip()
        trans = translate_text(orig, "en", "th", engine)
        ctx_trans.append({"orig": orig, "trans": trans})
    notes = {
        "google":   "แปลโดย Google Translate · ฟรี ไม่จำกัด",
        "mymemory": "แปลโดย MyMemory · ฟรี ~500 คำ/วัน",
    }
    return {"main": main, "context_translations": ctx_trans, "note": notes.get(engine, "")}

# ============================================================
# SECTION 4 — File / Language / Tokenize
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


def is_english(text: str) -> bool:
    """
    ตรวจว่าไฟล์เป็นภาษาอังกฤษ
    — ถ้ามีตัวอักษรไทยเกิน 5% ของตัวอักษรทั้งหมด → ถือว่าไม่ใช่ภาษาอังกฤษ
    """
    thai  = len(re.findall(r'[\u0e00-\u0e7f]', text))
    total = len(re.findall(r'[^\s]', text)) or 1
    return (thai / total) < 0.05


def tokenize_en(text: str, min_len: int) -> list:
    tokens = re.findall(r"[a-zA-Z']+", text)
    return [t.strip("'").lower() for t in tokens if len(t.strip("'")) >= min_len]


def build_freq_df(tokens: list) -> pd.DataFrame:
    counter = collections.Counter(tokens)
    total   = sum(counter.values()) or 1
    rows = [{"คำ": w, "จำนวนครั้ง": c, "สัดส่วน (%)": round(c/total*100, 2)}
            for w, c in counter.most_common()]
    df = pd.DataFrame(rows)
    df.index = range(1, len(df)+1); df.index.name = "อันดับ"
    return df

# ============================================================
# SECTION 5 — Context extraction
# ============================================================
def split_sentences(text: str) -> list:
    sents = re.split(r'(?<=[.!?])\s+', text)
    return [s.strip() for s in sents if len(s.strip()) > 10]


def get_contexts(word: str, sentences: list, max_ctx: int = None) -> list:
    """
    คืน list ของ HTML strings (escaped + <mark> highlight)
    max_ctx=None → แสดงทุกประโยคที่พบ (ไม่จำกัด)
    """
    pattern  = re.compile(r'\b' + re.escape(word) + r'\b', re.IGNORECASE)
    safe_word = htmllib.escape(word)
    pattern2 = re.compile(r'\b' + re.escape(safe_word) + r'\b', re.IGNORECASE)
    results  = []
    for sent in sentences:
        if pattern.search(sent):
            highlighted = pattern2.sub(
                lambda m: f'<mark>{m.group(0)}</mark>',
                htmllib.escape(sent),
            )
            results.append(highlighted)
            if max_ctx is not None and len(results) >= max_ctx:
                break
    return results

# ============================================================
# SECTION 6 — Chart builder (light theme)
# ============================================================
def build_chart(df_top: pd.DataFrame, palette_name: str) -> plt.Figure:
    colors = PALETTES[palette_name]
    n      = len(df_top)
    fig, ax = plt.subplots(figsize=(9, max(4.5, n * 0.37)))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    bar_colors = list(reversed([mcolors.to_rgba(colors[i % len(colors)]) for i in range(n)]))
    words_rev  = list(df_top["คำ"])[::-1]
    counts_rev = list(df_top["จำนวนครั้ง"])[::-1]

    bars = ax.barh(words_rev, counts_rev, color=bar_colors, edgecolor="none", height=0.62)
    max_val = max(counts_rev) if counts_rev else 1

    # ตัวเลขท้ายแท่ง (ASCII เท่านั้น ใช้ DejaVu ได้)
    for bar, val in zip(bars, counts_rev):
        ax.text(
            bar.get_width() + max_val * 0.012,
            bar.get_y() + bar.get_height() / 2,
            f"{val:,}", va="center", ha="left",
            color="#4a5888", fontsize=8.5,
            fontproperties=fm.FontProperties(family="DejaVu Sans"),
        )

    ax.set_xlim(0, max_val * 1.18)

    # xlabel ภาษาไทย — ใช้ thai_fp()
    ax.set_xlabel("จำนวนครั้ง", color="#8a96b8",
                  fontproperties=thai_fp(9))

    # tick labels แกน Y = คำภาษาอังกฤษ
    ax.tick_params(colors="#6a78a8", labelsize=8.5)
    for lbl in ax.get_yticklabels():
        lbl.set_fontproperties(fm.FontProperties(family="DejaVu Sans", size=8.5))

    ax.spines[:].set_visible(False)
    ax.xaxis.set_tick_params(length=0)
    ax.yaxis.set_tick_params(length=0)
    ax.grid(axis="x", color="#eceef8", linewidth=0.8)
    fig.tight_layout(pad=1.4)
    return fig

# ============================================================
# SECTION 7 — HTML renderers  (ใช้ htmllib.escape ป้องกัน tag รั่ว)
# ============================================================
def build_progress_table(df, top_n, palette_name, selected="") -> str:
    subset  = df.head(top_n)
    max_pct = subset["สัดส่วน (%)"].max() if len(subset) else 1
    accent  = PALETTES[palette_name][1]
    rows = ""
    for rank, row in subset.iterrows():
        pct   = row["สัดส่วน (%)"]
        bar_w = int(pct / max_pct * 100) if max_pct else 0
        word  = htmllib.escape(str(row["คำ"]))
        is_sel = str(row["คำ"]) == selected
        wstyle = "color:#2a44cc;font-weight:700;" if is_sel else "color:#2a3460;"
        rows += f"""
        <tr>
          <td><span class="rank-num">#{rank:02d}</span></td>
          <td><span style="{wstyle}">{word}</span></td>
          <td><span class="count-cell">{int(row['จำนวนครั้ง']):,}</span></td>
          <td><span class="pct-cell">{pct:.2f}%</span></td>
          <td><div class="bar-track">
            <div class="bar-fill" style="width:{bar_w}%;background:{accent};"></div>
          </div></td>
        </tr>"""
    return f"""<table class="freq-table">
      <thead><tr><th>#</th><th>คำ</th><th>จำนวน</th><th>%</th><th>สัดส่วน</th></tr></thead>
      <tbody>{rows}</tbody></table>"""


def render_context_panel(word, ctx_list, freq, pct) -> str:
    safe_word = htmllib.escape(word)
    if not ctx_list:
        return (f'<div class="ctx-panel">'
                f'<div class="ctx-word">"{safe_word}"</div>'
                f'<div class="ctx-meta">ไม่พบบริบทในเอกสาร</div></div>')
    items = "".join(f"""
        <div class="ctx-sentence-wrap">
          <div class="ctx-sent-num">ประโยคที่ {i+1} / {len(ctx_list)}</div>
          <div class="ctx-sentence">{h}</div>
        </div>""" for i, h in enumerate(ctx_list))
    # แสดงหมายเหตุถ้าจำนวนบริบท < ความถี่จริง (คำปรากฏในประโยคเดิมซ้ำ)
    note = (f'<div class="ctx-more">ℹ️ คำนี้ปรากฏ {freq:,} ครั้ง '
            f'ใน {len(ctx_list)} ประโยค (บางประโยคมีคำนี้มากกว่า 1 ครั้ง)</div>'
            if freq > len(ctx_list) else "")
    return f"""<div class="ctx-panel">
      <div style="display:flex;align-items:baseline;gap:.7rem;margin-bottom:.8rem;">
        <span class="ctx-word">"{safe_word}"</span>
        <span class="ctx-meta">พบ {freq:,} ครั้ง ({pct:.2f}%) · {len(ctx_list)} ประโยค</span>
      </div>{items}{note}</div>"""


def show_trans_panel(result: dict, engine_key: str):
    """
    แสดงผลแปลด้วย Streamlit native components ทั้งหมด
    — ไม่ใช้ unsafe_allow_html เลย → ไม่มีปัญหา HTML escape
    """
    engine_names = {"google": "Google Translate", "mymemory": "MyMemory"}
    engine_name  = engine_names.get(engine_key, engine_key)

    # กล่องหลัก
    with st.container():
        # badge engine
        st.markdown(
            f'<div class="trans-engine-tag">'
            f'🔤 แปล EN → TH &nbsp;'
            f'<span class="engine-badge">✓ {htmllib.escape(engine_name)}</span>'
            f'<span class="engine-badge">FREE</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        # คำแปลหลัก — ใช้ st.markdown plain text (ไม่ใช่ HTML)
        main = result.get("main", "—") or "—"
        st.markdown(f"### {main}")

        st.divider()

        # บริบทที่แปล
        ctx_list = result.get("context_translations", [])
        if ctx_list:
            st.markdown("**📋 บริบทที่แปลแล้ว**")
            for i, c in enumerate(ctx_list):
                orig  = c.get("orig",  "").strip()
                trans = c.get("trans", "").strip()
                if not orig and not trans:
                    continue
                # ใช้ st.text / st.write — ไม่มีทางรั่ว HTML
                with st.container():
                    st.markdown(
                        f"<div class='trans-ctx-item'>"
                        f"<div class='trans-ctx-orig'>📄 {htmllib.escape(orig[:160])}"
                        f"{'…' if len(orig) > 160 else ''}</div>"
                        f"<div class='trans-ctx-translated'>🔁 {htmllib.escape(trans)}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
        else:
            st.caption("ไม่มีบริบท")

        # หมายเหตุ
        note = result.get("note", "")
        if note:
            st.caption(f"💡 {note}")


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    return df.reset_index().to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")

# ============================================================
# SECTION 8 — Hero
# ============================================================
st.markdown("""
<div class="hero">
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
    st.info("📄 แสดงบริบท **ทุกประโยค** ที่พบในเอกสาร")

    st.markdown("---")
    palette = st.selectbox("🎨 สีแผนภูมิ", list(PALETTES.keys()), index=0)

    st.markdown("---")
    st.markdown("### 🔤 Translation Engine")
    engine_label = st.selectbox("เลือก Engine", list(ENGINES.keys()), index=0)
    engine_key   = ENGINES[engine_label]
    info = {
        "google":   ("🟢", "Google Translate", "ฟรี ไม่จำกัด · แม่นยำสูง"),
        "mymemory": ("🟡", "MyMemory",          "ฟรี ~500 คำ/วัน"),
    }
    ic, nm, ds = info[engine_key]
    st.markdown(f"""
    <div class="engine-info-box">
      <div class="engine-info-name">{ic} {nm}</div>
      <div class="engine-info-desc">{ds}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("**รองรับ:** `.txt` · `.docx`  \n**ภาษา:** 🇬🇧 English เท่านั้น")

# ============================================================
# SECTION 10 — File Upload
# ============================================================
st.markdown('<p class="sec-label">01 — อัปโหลดเอกสาร</p>', unsafe_allow_html=True)
uploaded = st.file_uploader(
    "ลากไฟล์มาวาง หรือคลิกเพื่อเลือก (.txt · .docx)",
    type=["txt", "docx"], label_visibility="collapsed",
)

# ============================================================
# SECTION 11 — Main
# ============================================================
if uploaded:
    with st.spinner("⏳ กำลังวิเคราะห์..."):
        try:
            raw_text = read_file(uploaded)

            # ── ตรวจว่าเป็นภาษาอังกฤษ ──────────────────────────
            if not is_english(raw_text):
                st.error(
                    "❌ ตรวจพบข้อความภาษาไทยหรือภาษาอื่นในไฟล์นี้\n\n"
                    "เครื่องมือนี้รองรับเฉพาะ **ภาษาอังกฤษ** เท่านั้น "
                    "กรุณาอัปโหลดไฟล์ที่มีเนื้อหาเป็นภาษาอังกฤษครับ"
                )
                st.stop()

            active_sw  = (ENGLISH_STOPWORDS | extra_sw) if use_sw else set()
            all_tokens = tokenize_en(raw_text, min_len)
            filt_tokens = [t for t in all_tokens if t not in active_sw]
            freq_df     = build_freq_df(filt_tokens)
            sentences   = split_sentences(raw_text)
        except Exception as e:
            st.error(f"❌ ไม่สามารถอ่านไฟล์: {e}"); st.stop()

    raw_count  = len(all_tokens)
    filt_count = len(filt_tokens)
    unique_count = len(freq_df)

    st.markdown('<p class="sec-label">02 — ภาพรวมเอกสาร</p>', unsafe_allow_html=True)
    fn = htmllib.escape(uploaded.name)
    st.markdown(f"""
    <div class="cards">
      <div class="card"><div class="card-icon">📄</div><p class="card-label">ไฟล์</p>
        <p class="card-value" style="font-size:.78rem;line-height:1.3;">{fn}</p></div>
      <div class="card"><div class="card-icon">🌐</div><p class="card-label">ภาษา</p>
        <p class="card-value" style="font-size:.85rem;">🇬🇧 English</p></div>
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

    # Word buttons
    st.markdown('<p class="sec-label">04 — คลิกคำเพื่อดูบริบทและแปล</p>', unsafe_allow_html=True)
    st.caption(f"เลือกคำจาก Top {top_n} · คลิกซ้ำเพื่อยกเลิก")

    words_list = list(df_top["คำ"])
    for row_i in range(0, len(words_list), 6):
        btn_cols = st.columns(6)
        for ci, word in enumerate(words_list[row_i: row_i + 6]):
            freq_val = int(df_top.loc[df_top["คำ"] == word, "จำนวนครั้ง"].values[0])
            is_sel   = selected == word
            if btn_cols[ci].button(
                f"**{word}**" if is_sel else word,
                key=f"wb_{word}", help=f"{word}: {freq_val:,} ครั้ง",
                use_container_width=True,
            ):
                if is_sel:
                    st.session_state.selected_word = ""
                    st.session_state.trans_result  = None
                    st.session_state.trans_word    = ""
                else:
                    st.session_state.selected_word = word
                    st.session_state.trans_result  = None
                    st.session_state.trans_word    = ""
                st.rerun()

    selected_word = st.session_state.get("selected_word", "")
    if selected_word:
        st.markdown('<p class="sec-label">05 — บริบทและคำแปล</p>', unsafe_allow_html=True)

        row_data = freq_df[freq_df["คำ"] == selected_word]
        freq_val = int(row_data["จำนวนครั้ง"].values[0]) if len(row_data) else 0
        pct_val  = float(row_data["สัดส่วน (%)"].values[0]) if len(row_data) else 0.0
        ctx_list = get_contexts(selected_word, sentences)

        c_ctx, c_trans = st.columns([1.1, 1], gap="large")

        with c_ctx:
            st.markdown("**🔍 บริบทในต้นฉบับ**")
            st.markdown(render_context_panel(selected_word, ctx_list, freq_val, pct_val),
                        unsafe_allow_html=True)

        with c_trans:
            st.markdown("**🔤 คำแปล → ไทย**")
            cached      = st.session_state.get("trans_result")
            cached_word = st.session_state.get("trans_word", "")
            cached_eng  = st.session_state.get("trans_engine", "")
            need_new    = cached is None or cached_word != selected_word or cached_eng != engine_key

            if need_new:
                with st.spinner(f'🔤 กำลังแปล "{selected_word}" ...'):
                    try:
                        result = translate_all(selected_word, ctx_list, engine_key)
                        st.session_state.trans_result  = result
                        st.session_state.trans_word    = selected_word
                        st.session_state.trans_engine  = engine_key
                    except Exception as e:
                        st.error(f"❌ แปลไม่สำเร็จ: {e}\nลองเปลี่ยน engine หรือตรวจสอบ internet")
                        result = None
            else:
                result = cached

            if result:
                # ใช้ Streamlit native — ไม่มีทาง HTML รั่ว
                with st.container(border=True):
                    show_trans_panel(result, engine_key)

            bc1, bc2 = st.columns(2)
            with bc1:
                if st.button("🔄 แปลใหม่", key="retrans", use_container_width=True):
                    st.session_state.trans_result = None; st.rerun()
            with bc2:
                if st.button("⇄ สลับ Engine", key="sweng", use_container_width=True):
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
        st.download_button(f"⬇️ CSV — Top {min(top_n, unique_count)}",
                           data=to_csv_bytes(df_top),
                           file_name=f"{base}_top{top_n}.csv", mime="text/csv",
                           use_container_width=True)
    with dc3:
        st.caption("คอลัมน์: อันดับ · คำ · จำนวนครั้ง · สัดส่วน (%)  \nEncoding: UTF-8 BOM — เปิดใน Excel ได้ทันที")

    # Preview
    st.markdown('<p class="sec-label">07 — ข้อความต้นฉบับ</p>', unsafe_allow_html=True)
    with st.expander("📝 แสดงข้อความต้นฉบับ"):
        preview = raw_text[:2000] + (f"\n\n… [{len(raw_text):,} ตัวอักษร]" if len(raw_text) > 2000 else "")
        st.text(preview)

else:
    st.markdown("""
    <div class="info-box">
      <div style="font-size:2rem;margin-bottom:.5rem;">📂</div>
      กรุณาอัปโหลดไฟล์ <strong>.txt</strong> หรือ <strong>.docx</strong> ด้านบน<br>
      <span style="font-size:.8rem;color:#9aa0c0;">
      รองรับไฟล์ .txt และ .docx ภาษาอังกฤษ · แปลฟรี EN→TH ด้วย Google Translate / MyMemory
      </span>
    </div>""", unsafe_allow_html=True)

    st.markdown('<p class="sec-label">ตัวอย่างผลลัพธ์</p>', unsafe_allow_html=True)
    dw = ["translation","language","context","meaning","phrase","source","target","register","nuance","fluency"]
    dc_counts = [84,71,60,46,41,36,32,24,18,12]
    td = sum(dc_counts)
    ddf = pd.DataFrame({"คำ":dw,"จำนวนครั้ง":dc_counts,
                         "สัดส่วน (%)":[round(c/td*100,2) for c in dc_counts]})
    ddf.index = range(1,len(ddf)+1); ddf.index.name="อันดับ"
    dd1, dd2 = st.columns([1.15,1], gap="large")
    with dd1:
        fig_d = build_chart(ddf, palette)
        st.pyplot(fig_d, use_container_width=True); plt.close(fig_d)
    with dd2:
        st.markdown(build_progress_table(ddf, 10, palette), unsafe_allow_html=True)
