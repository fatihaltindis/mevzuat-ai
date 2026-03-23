"""
Mevzuat AI — Türk Mevzuatı Araştırma Aracı
Hâkimler ve avukatlar için mevzuat.gov.tr tabanlı hukuk araştırma aracı.
AI yalnızca sorgu ayrıştırma için kullanılır (~600 token). Sonuçlar doğrudan API'den gösterilir.
"""

import streamlit as st
from mevzuat_client import search_legislation, get_document, get_article, get_article_tree
from query_parser import parse_query, build_manual_params

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mevzuat AI",
    page_icon="⚖️",
    layout="wide",
)

# ── Legislation type labels ──────────────────────────────────────────────────
MEVZUAT_TURLERI = {
    "KANUN": "Kanun",
    "CB_KARARNAME": "CB Kararnamesi",
    "YONETMELIK": "Yönetmelik",
    "CB_YONETMELIK": "CB Yönetmeliği",
    "KHK": "KHK",
    "TUZUK": "Tüzük",
    "KKY": "Kurum/Kuruluş Yönetmeliği",
    "TEBLIGLER": "Tebliğ",
    "MULGA": "Mülga Kanun",
}

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .block-container { padding-top: 1rem; }
    .main-header {
        text-align: center;
        padding: 1rem 0 0.75rem 0;
        border-bottom: 2px solid #1a365d;
        margin-bottom: 1rem;
    }
    .main-header h1 { color: #1a365d; font-size: 1.8rem; margin-bottom: 0.15rem; }
    .main-header p { color: #4a5568; font-size: 0.95rem; margin: 0; }
    .search-params {
        background: #f0f4f8;
        padding: 0.6rem 1rem;
        border-radius: 8px;
        border-left: 4px solid #3182ce;
        margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .result-card {
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 0.5rem;
        background: white;
    }
    .result-card:hover { border-color: #3182ce; }
    .result-title { font-weight: 600; color: #1a365d; font-size: 1rem; }
    .result-meta { color: #718096; font-size: 0.85rem; margin-top: 0.2rem; }
    .toc-item { padding: 0.3rem 0; border-bottom: 1px solid #f0f0f0; }
    .article-content {
        background: #fafafa;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        line-height: 1.8;
        font-size: 0.95rem;
        white-space: pre-wrap;
    }
    .token-badge {
        background: #c6f6d5;
        color: #22543d;
        padding: 0.15rem 0.5rem;
        border-radius: 10px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .sidebar-info {
        background: #f7fafc;
        padding: 0.75rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        font-size: 0.85rem;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚖️ Mevzuat AI</h1>
    <p>Türk Mevzuatı Araştırma Aracı — Hâkimler ve Avukatlar İçin</p>
</div>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")

    _secret_key = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, "secrets") else None

    if _secret_key:
        api_key = _secret_key
        st.success("API anahtarı yapılandırılmış", icon="🔑")
    else:
        api_key = st.text_input(
            "Google Gemini API Anahtarı",
            type="password",
            help="Doğal dil sorguları için gerekli. Manuel arama için gerekmez.",
        )
        st.markdown(
            '[🔑 Ücretsiz API anahtarı al →](https://aistudio.google.com/apikey)',
        )

    st.markdown("---")

    st.markdown("### 📖 Nasıl Çalışır?")
    st.markdown("""
<div class="sidebar-info">
<strong>1.</strong> Sorunuzu doğal dille yazın veya manuel arama yapın<br>
<strong>2.</strong> AI sorunuzu arama parametrelerine çevirir (~600 token)<br>
<strong>3.</strong> Sonuçlar doğrudan mevzuat.gov.tr API'sinden gelir<br>
<strong>4.</strong> İçindekiler ve madde metinleri sıfır token harcar
</div>
""", unsafe_allow_html=True)

    st.markdown("---")

    st.markdown("### 💡 Örnek Sorular")
    examples = [
        "Türk Ceza Kanunu'nun 141. maddesi ne diyor?",
        "İş Kanunu'na göre yıllık izin hakkı kaç gündür?",
        "KVKK'ya göre veri sorumlusunun yükümlülükleri nelerdir?",
        "Son çıkan iş sağlığı yönetmelikleri",
    ]
    for ex in examples:
        if st.button(ex, key=f"ex_{ex}", use_container_width=True):
            st.session_state["pending_question"] = ex
            st.rerun()

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.75rem; color:#718096;">'
        'Kaynak: mevzuat.gov.tr (Adalet Bakanlığı)<br>'
        'Bu araç bilgi amaçlıdır, hukuki danışmanlık yerine geçmez.</p>',
        unsafe_allow_html=True,
    )


# ── Session state init ───────────────────────────────────────────────────────
defaults = {
    "search_results": None,
    "search_params": None,
    "selected_mevzuat": None,
    "toc_data": None,
    "article_content": None,
    "document_content": None,
    "search_history": [],
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ── Helper functions ─────────────────────────────────────────────────────────

def do_search(params: dict):
    """Execute search and store results in session state."""
    result = search_legislation(
        phrase=params.get("phrase"),
        title=params.get("title"),
        types=params.get("types"),
        number=params.get("number"),
        exact=params.get("exact", False),
    )
    st.session_state["search_results"] = result
    st.session_state["search_params"] = params
    # Clear downstream state
    st.session_state["selected_mevzuat"] = None
    st.session_state["toc_data"] = None
    st.session_state["article_content"] = None
    st.session_state["document_content"] = None


def load_toc(mevzuat_id: str, mevzuat_name: str):
    """Load table of contents for a legislation."""
    toc = get_article_tree(mevzuat_id)
    st.session_state["toc_data"] = toc
    st.session_state["selected_mevzuat"] = {"id": mevzuat_id, "name": mevzuat_name}
    st.session_state["article_content"] = None
    st.session_state["document_content"] = None


def load_article(madde_id: str):
    """Load a single article."""
    article = get_article(madde_id)
    st.session_state["article_content"] = article
    st.session_state["document_content"] = None


def load_document(mevzuat_id: str):
    """Load full document."""
    doc = get_document(mevzuat_id)
    st.session_state["document_content"] = doc
    st.session_state["article_content"] = None


# ── Tabs ─────────────────────────────────────────────────────────────────────
tab_search, tab_manual = st.tabs(["🔍 Doğal Dil Arama", "📋 Manuel Arama"])

# ── Tab 1: Natural language search ───────────────────────────────────────────
with tab_search:
    col_input, col_badge = st.columns([6, 1])
    with col_input:
        user_input = st.text_input(
            "Sorunuzu yazın",
            placeholder="Örn: İş Kanunu'nda fazla mesai ücreti nasıl hesaplanır?",
            label_visibility="collapsed",
            key="nl_input",
        )
    with col_badge:
        st.markdown('<span class="token-badge">~600 token</span>', unsafe_allow_html=True)

    # Handle pending question from sidebar
    if "pending_question" in st.session_state:
        user_input = st.session_state.pop("pending_question")

    if user_input:
        if not api_key:
            st.error(
                "Doğal dil araması için API anahtarı gereklidir. "
                "Sol panelden API anahtarınızı girin veya Manuel Arama sekmesini kullanın."
            )
        else:
            with st.spinner("Sorgu ayrıştırılıyor..."):
                try:
                    params = parse_query(user_input, api_key)
                    st.session_state["search_history"].append({
                        "question": user_input,
                        "params": params,
                    })
                except Exception as e:
                    st.error(f"AI sorgu ayrıştırma hatası: {e}")
                    params = None

            if params:
                with st.spinner("Mevzuat aranıyor..."):
                    try:
                        do_search(params)
                    except Exception as e:
                        st.error(f"Arama hatası: {e}")


# ── Tab 2: Manual search ────────────────────────────────────────────────────
with tab_manual:
    st.markdown('<span class="token-badge">0 token</span>', unsafe_allow_html=True)

    mcol1, mcol2 = st.columns(2)
    with mcol1:
        manual_phrase = st.text_input("İçerik Araması", placeholder="Örn: fazla mesai ücreti")
        manual_number = st.text_input("Mevzuat No", placeholder="Örn: 4857")
    with mcol2:
        manual_title = st.text_input("Başlık Araması", placeholder="Örn: iş kanunu")
        manual_exact = st.checkbox("Tam eşleşme")

    manual_types = st.multiselect(
        "Mevzuat Türü",
        options=list(MEVZUAT_TURLERI.keys()),
        format_func=lambda x: MEVZUAT_TURLERI[x],
        default=["KANUN"],
    )

    if st.button("🔍 Ara", key="manual_search", use_container_width=True):
        if not manual_phrase and not manual_title:
            st.warning("Lütfen en az bir arama kriteri girin.")
        else:
            params = build_manual_params(
                phrase=manual_phrase or None,
                title=manual_title or None,
                types=manual_types or None,
                number=manual_number or None,
                exact=manual_exact,
            )
            with st.spinner("Mevzuat aranıyor..."):
                try:
                    do_search(params)
                except Exception as e:
                    st.error(f"Arama hatası: {e}")


# ── Display area (shared between tabs) ───────────────────────────────────────
st.markdown("---")

# Show current search params
if st.session_state["search_params"]:
    params = st.session_state["search_params"]
    parts = []
    if params.get("phrase"):
        parts.append(f"**Arama:** {params['phrase']}")
    if params.get("title"):
        parts.append(f"**Başlık:** {params['title']}")
    if params.get("types"):
        type_labels = [MEVZUAT_TURLERI.get(t, t) for t in params["types"]]
        parts.append(f"**Tür:** {', '.join(type_labels)}")
    if params.get("number"):
        parts.append(f"**No:** {params['number']}")
    if parts:
        st.markdown(f'<div class="search-params">{" | ".join(parts)}</div>', unsafe_allow_html=True)


# ── Search Results ───────────────────────────────────────────────────────────
if st.session_state["search_results"]:
    results = st.session_state["search_results"]
    docs = results.get("documents", [])
    total = results.get("totalRecords", 0)

    st.markdown(f"**{total} sonuç bulundu** (sayfa {results.get('page', 1)})")

    if not docs:
        st.info("Aramanızla eşleşen mevzuat bulunamadı. Farklı anahtar kelimelerle tekrar deneyin.")
    else:
        for i, doc in enumerate(docs):
            tur_label = MEVZUAT_TURLERI.get(doc.get("tur", ""), doc.get("turAciklama", ""))
            rg_tarih = doc.get("resmiGazeteTarihi", "—")
            rg_sayi = doc.get("resmiGazeteSayisi", "")
            mevzuat_no = doc.get("mevzuatNo", "")
            mevzuat_id = doc.get("mevzuatId", "")
            name = doc.get("mevzuatAdi", "Bilinmeyen")

            with st.container():
                col_info, col_actions = st.columns([4, 2])

                with col_info:
                    st.markdown(
                        f'<div class="result-card">'
                        f'<div class="result-title">{name}</div>'
                        f'<div class="result-meta">'
                        f'{tur_label} | No: {mevzuat_no} | '
                        f'R.G.: {rg_tarih} | Sayı: {rg_sayi}'
                        f'</div></div>',
                        unsafe_allow_html=True,
                    )

                with col_actions:
                    bcol1, bcol2 = st.columns(2)
                    with bcol1:
                        if st.button("📑 İçindekiler", key=f"toc_{i}_{mevzuat_id}"):
                            with st.spinner("İçindekiler yükleniyor..."):
                                try:
                                    load_toc(mevzuat_id, name)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")
                    with bcol2:
                        if st.button("📄 Tam Metin", key=f"doc_{i}_{mevzuat_id}"):
                            with st.spinner("Belge yükleniyor..."):
                                try:
                                    load_document(mevzuat_id)
                                    load_toc(mevzuat_id, name)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")


# ── Table of Contents ────────────────────────────────────────────────────────
if st.session_state["toc_data"] and st.session_state["selected_mevzuat"]:
    st.markdown("---")
    mevzuat_info = st.session_state["selected_mevzuat"]
    toc = st.session_state["toc_data"]

    st.markdown(f"### 📑 {mevzuat_info['name']} — İçindekiler")

    if "error" in toc:
        st.error(f"İçindekiler yüklenemedi: {toc['error']}")
    else:
        tree = toc.get("tree", [])
        if not tree:
            st.info("Bu mevzuat için içindekiler bulunamadı.")
        else:
            for j, node in enumerate(tree):
                madde_id = node.get("maddeId")
                madde_no = node.get("maddeNo", "")
                title = node.get("title", "")
                depth = node.get("depth", 0)
                indent = "→ " * depth

                col_title, col_btn = st.columns([5, 1])
                with col_title:
                    label = f"{indent}**{madde_no}** {title}" if madde_no else f"{indent}{title}"
                    st.markdown(label)
                with col_btn:
                    if madde_id:
                        if st.button("Göster", key=f"art_{j}_{madde_id}"):
                            with st.spinner("Madde yükleniyor..."):
                                try:
                                    load_article(madde_id)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")


# ── Article Content ──────────────────────────────────────────────────────────
if st.session_state["article_content"]:
    st.markdown("---")
    article = st.session_state["article_content"]

    if "error" in article:
        st.error(f"Madde yüklenemedi: {article['error']}")
    else:
        st.markdown("### 📄 Madde Metni")
        st.markdown(
            f'<div class="article-content">{article.get("content", "İçerik bulunamadı.")}</div>',
            unsafe_allow_html=True,
        )


# ── Full Document Content ────────────────────────────────────────────────────
if st.session_state["document_content"]:
    st.markdown("---")
    doc = st.session_state["document_content"]

    if "error" in doc:
        st.error(f"Belge yüklenemedi: {doc['error']}")
    else:
        st.markdown("### 📄 Tam Metin")
        content = doc.get("content", "İçerik bulunamadı.")
        st.markdown(
            f'<div class="article-content">{content}</div>',
            unsafe_allow_html=True,
        )


# ── Empty state ──────────────────────────────────────────────────────────────
if not st.session_state["search_results"] and not st.session_state["article_content"]:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color: #718096;">
        <p style="font-size: 3rem;">⚖️</p>
        <p style="font-size: 1.1rem;">Hoş geldiniz!</p>
        <p>Türk mevzuatıyla ilgili sorunuzu yukarıdaki alana yazın<br>
        veya sol paneldeki örnek sorulardan birini seçin.</p>
        <p style="margin-top:1rem; font-size:0.85rem;">
            <strong>Doğal dil araması:</strong> ~600 token (AI sorgu ayrıştırma)<br>
            <strong>Manuel arama:</strong> 0 token<br>
            <strong>İçindekiler ve madde görüntüleme:</strong> 0 token
        </p>
    </div>
    """, unsafe_allow_html=True)
