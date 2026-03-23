"""
Mevzuat AI — Türk Mevzuatı ve Yargı Kararları Araştırma Aracı
Hâkimler ve avukatlar için mevzuat.gov.tr tabanlı hukuk araştırma aracı.
AI yalnızca sorgu ayrıştırma için kullanılır (~600 token). Sonuçlar doğrudan API'den gösterilir.
"""

import streamlit as st
from mevzuat_client import search_legislation, get_document, get_article, get_article_tree
from yargi_client import search_decisions, get_decision, COURT_TYPES, CHAMBERS, CHAMBER_GROUPS
from query_parser import (
    parse_query, parse_yargi_query,
    build_manual_params, build_manual_yargi_params,
)

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
        color: #1a202c;
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
        background: #ffffff;
        color: #1a202c;
    }
    .result-card:hover { border-color: #3182ce; }
    .result-title { font-weight: 600; color: #1a365d; font-size: 1rem; }
    .result-meta { color: #4a5568; font-size: 0.85rem; margin-top: 0.2rem; }
    .toc-item { padding: 0.3rem 0; border-bottom: 1px solid #f0f0f0; color: #1a202c; }
    .article-content {
        background: #ffffff;
        color: #1a202c;
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
        color: #1a202c;
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
    <p>Türk Mevzuatı ve Yargı Kararları Araştırma Aracı — Hâkimler ve Avukatlar İçin</p>
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
<strong>4.</strong> İçindekiler ve madde/karar metinleri sıfır token harcar
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.75rem; color:#718096;">'
        'Kaynak: mevzuat.gov.tr (Adalet Bakanlığı)<br>'
        'Bu araç bilgi amaçlıdır, hukuki danışmanlık yerine geçmez.</p>',
        unsafe_allow_html=True,
    )


# ── Session state init ───────────────────────────────────────────────────────
defaults = {
    # Mevzuat state
    "m_search_results": None,
    "m_search_params": None,
    "m_selected_mevzuat": None,
    "m_toc_data": None,
    "m_article_content": None,
    "m_document_content": None,
    "m_sort_by": "relevance",
    # Yargı state
    "y_search_results": None,
    "y_search_params": None,
    "y_decision_content": None,
    "y_sort_by": "relevance",
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ══════════════════════════════════════════════════════════════════════════════
# MEVZUAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def do_mevzuat_search(params: dict, sort_by: str = "relevance"):
    """Execute mevzuat search and store results."""
    result = search_legislation(
        phrase=params.get("phrase"),
        title=params.get("title"),
        types=params.get("types"),
        number=params.get("number"),
        exact=params.get("exact", False),
        sort_by=sort_by,
    )
    st.session_state["m_search_results"] = result
    st.session_state["m_search_params"] = params
    st.session_state["m_selected_mevzuat"] = None
    st.session_state["m_toc_data"] = None
    st.session_state["m_article_content"] = None
    st.session_state["m_document_content"] = None


def load_toc(mevzuat_id: str, mevzuat_name: str):
    toc = get_article_tree(mevzuat_id)
    st.session_state["m_toc_data"] = toc
    st.session_state["m_selected_mevzuat"] = {"id": mevzuat_id, "name": mevzuat_name}
    st.session_state["m_article_content"] = None
    st.session_state["m_document_content"] = None


def load_article(madde_id: str):
    article = get_article(madde_id)
    st.session_state["m_article_content"] = article
    st.session_state["m_document_content"] = None


def load_document(mevzuat_id: str):
    doc = get_document(mevzuat_id)
    st.session_state["m_document_content"] = doc
    st.session_state["m_article_content"] = None


# ══════════════════════════════════════════════════════════════════════════════
# YARGI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def do_yargi_search(params: dict, sort_by: str = "relevance"):
    """Execute yargı search and store results."""
    result = search_decisions(
        phrase=params.get("phrase"),
        court_types=params.get("court_types"),
        chamber=params.get("chamber", "ALL"),
        date_start=params.get("date_start"),
        date_end=params.get("date_end"),
        sort_by=sort_by,
    )
    st.session_state["y_search_results"] = result
    st.session_state["y_search_params"] = params
    st.session_state["y_decision_content"] = None


def load_decision(document_id: str):
    decision = get_decision(document_id)
    st.session_state["y_decision_content"] = decision


# ══════════════════════════════════════════════════════════════════════════════
# MAIN TABS
# ══════════════════════════════════════════════════════════════════════════════

main_tab_mevzuat, main_tab_yargi = st.tabs(["📜 Mevzuat", "⚖️ Yargı Kararları"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: MEVZUAT
# ══════════════════════════════════════════════════════════════════════════════

with main_tab_mevzuat:
    m_sub_nl, m_sub_manual = st.tabs(["🔍 Doğal Dil Arama", "📋 Manuel Arama"])

    # ── Mevzuat NL Search ────────────────────────────────────────────────────
    with m_sub_nl:
        col_input, col_badge = st.columns([6, 1])
        with col_input:
            m_nl_input = st.text_input(
                "Sorunuzu yazın",
                placeholder="Örn: İş Kanunu'nda fazla mesai ücreti nasıl hesaplanır?",
                label_visibility="collapsed",
                key="m_nl_input",
            )
        with col_badge:
            st.markdown('<span class="token-badge">~600 token</span>', unsafe_allow_html=True)

        if m_nl_input:
            if not api_key:
                st.error(
                    "Doğal dil araması için API anahtarı gereklidir. "
                    "Sol panelden API anahtarınızı girin veya Manuel Arama sekmesini kullanın."
                )
            else:
                with st.spinner("Sorgu ayrıştırılıyor..."):
                    try:
                        m_params = parse_query(m_nl_input, api_key)
                    except Exception as e:
                        st.error(f"AI sorgu ayrıştırma hatası: {e}")
                        m_params = None

                if m_params:
                    with st.spinner("Mevzuat aranıyor..."):
                        try:
                            do_mevzuat_search(m_params)
                        except Exception as e:
                            st.error(f"Arama hatası: {e}")

    # ── Mevzuat Manual Search ────────────────────────────────────────────────
    with m_sub_manual:
        st.markdown('<span class="token-badge">0 token</span>', unsafe_allow_html=True)

        mcol1, mcol2 = st.columns(2)
        with mcol1:
            manual_phrase = st.text_input("İçerik Araması", placeholder="Örn: fazla mesai ücreti", key="m_phrase")
            manual_number = st.text_input("Mevzuat No", placeholder="Örn: 4857", key="m_number")
        with mcol2:
            manual_title = st.text_input("Başlık Araması", placeholder="Örn: iş kanunu", key="m_title")
            manual_exact = st.checkbox("Tam eşleşme", key="m_exact")

        manual_types = st.multiselect(
            "Mevzuat Türü",
            options=list(MEVZUAT_TURLERI.keys()),
            format_func=lambda x: MEVZUAT_TURLERI[x],
            default=["KANUN"],
            key="m_types",
        )

        if st.button("🔍 Ara", key="m_manual_search", use_container_width=True):
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
                        do_mevzuat_search(params)
                    except Exception as e:
                        st.error(f"Arama hatası: {e}")

    # ── Mevzuat Display Area ─────────────────────────────────────────────────
    st.markdown("---")

    # Sort toggle
    if st.session_state["m_search_params"]:
        sort_col, _ = st.columns([2, 4])
        with sort_col:
            m_sort_options = {"Alakaya göre": "relevance", "Tarihe göre (yeni → eski)": "date"}
            current_m_sort = st.session_state.get("m_sort_by", "relevance")
            current_m_label = [k for k, v in m_sort_options.items() if v == current_m_sort][0]
            selected_m_sort = st.selectbox(
                "Sıralama",
                options=list(m_sort_options.keys()),
                index=list(m_sort_options.keys()).index(current_m_label),
                key="m_sort_select",
            )
            new_m_sort = m_sort_options[selected_m_sort]
            if new_m_sort != st.session_state.get("m_sort_by", "relevance"):
                st.session_state["m_sort_by"] = new_m_sort
                with st.spinner("Yeniden sıralanıyor..."):
                    try:
                        do_mevzuat_search(st.session_state["m_search_params"], sort_by=new_m_sort)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Arama hatası: {e}")

    # Search params display
    if st.session_state["m_search_params"]:
        params = st.session_state["m_search_params"]
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

    # Search results
    if st.session_state["m_search_results"]:
        results = st.session_state["m_search_results"]
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

    # Table of contents
    if st.session_state["m_toc_data"] and st.session_state["m_selected_mevzuat"]:
        st.markdown("---")
        mevzuat_info = st.session_state["m_selected_mevzuat"]
        toc = st.session_state["m_toc_data"]

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

    # Article content
    if st.session_state["m_article_content"]:
        st.markdown("---")
        article = st.session_state["m_article_content"]
        if "error" in article:
            st.error(f"Madde yüklenemedi: {article['error']}")
        else:
            st.markdown("### 📄 Madde Metni")
            st.markdown(
                f'<div class="article-content">{article.get("content", "İçerik bulunamadı.")}</div>',
                unsafe_allow_html=True,
            )

    # Full document content
    if st.session_state["m_document_content"]:
        st.markdown("---")
        doc = st.session_state["m_document_content"]
        if "error" in doc:
            st.error(f"Belge yüklenemedi: {doc['error']}")
        else:
            st.markdown("### 📄 Tam Metin")
            st.markdown(
                f'<div class="article-content">{doc.get("content", "İçerik bulunamadı.")}</div>',
                unsafe_allow_html=True,
            )

    # Mevzuat empty state
    if not st.session_state["m_search_results"] and not st.session_state["m_article_content"]:
        st.markdown("""
        <div style="text-align:center; padding: 2rem 1rem; color: #718096;">
            <p style="font-size: 2.5rem;">📜</p>
            <p style="font-size: 1rem;">Türk mevzuatında arama yapın</p>
            <p style="font-size: 0.85rem;">
                Doğal dil ile sorun veya manuel arama yapın.
            </p>
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: YARGI KARARLARI
# ══════════════════════════════════════════════════════════════════════════════

with main_tab_yargi:
    y_sub_nl, y_sub_manual = st.tabs(["🔍 Doğal Dil Arama", "📋 Manuel Arama"])

    # ── Yargı NL Search ──────────────────────────────────────────────────────
    with y_sub_nl:
        col_input, col_badge = st.columns([6, 1])
        with col_input:
            y_nl_input = st.text_input(
                "Sorunuzu yazın",
                placeholder="Örn: İş kazası tazminatıyla ilgili Yargıtay kararları",
                label_visibility="collapsed",
                key="y_nl_input",
            )
        with col_badge:
            st.markdown('<span class="token-badge">~600 token</span>', unsafe_allow_html=True)

        if y_nl_input:
            if not api_key:
                st.error(
                    "Doğal dil araması için API anahtarı gereklidir. "
                    "Sol panelden API anahtarınızı girin veya Manuel Arama sekmesini kullanın."
                )
            else:
                with st.spinner("Sorgu ayrıştırılıyor..."):
                    try:
                        y_params = parse_yargi_query(y_nl_input, api_key)
                    except Exception as e:
                        st.error(f"AI sorgu ayrıştırma hatası: {e}")
                        y_params = None

                if y_params:
                    with st.spinner("Yargı kararları aranıyor..."):
                        try:
                            do_yargi_search(y_params)
                        except Exception as e:
                            st.error(f"Arama hatası: {e}")

    # ── Yargı Manual Search ──────────────────────────────────────────────────
    with y_sub_manual:
        st.markdown('<span class="token-badge">0 token</span>', unsafe_allow_html=True)

        ycol1, ycol2 = st.columns(2)
        with ycol1:
            y_phrase = st.text_input(
                "Arama",
                placeholder="Örn: iş kazası tazminat",
                key="y_phrase",
            )
        with ycol2:
            y_court_types = st.multiselect(
                "Mahkeme Türü",
                options=list(COURT_TYPES.keys()),
                format_func=lambda x: COURT_TYPES[x],
                default=["YARGITAYKARARI", "DANISTAYKARAR"],
                key="y_court_types",
            )

        ycol3, ycol4 = st.columns(2)
        with ycol3:
            # Build flat chamber list for selectbox
            chamber_display = {"Tümü (filtre yok)": "ALL"}
            for group_name, codes in CHAMBER_GROUPS.items():
                if group_name == "Tümü":
                    continue
                for code in codes:
                    full_name = CHAMBERS.get(code, code)
                    if full_name:
                        chamber_display[f"{full_name} ({code})"] = code

            y_chamber = st.selectbox(
                "Daire / Kurul",
                options=list(chamber_display.keys()),
                index=0,
                key="y_chamber",
            )
            selected_chamber_code = chamber_display[y_chamber]

        with ycol4:
            y_date_col1, y_date_col2 = st.columns(2)
            with y_date_col1:
                y_date_start = st.date_input("Başlangıç Tarihi", value=None, key="y_date_start")
            with y_date_col2:
                y_date_end = st.date_input("Bitiş Tarihi", value=None, key="y_date_end")

        if st.button("🔍 Ara", key="y_manual_search", use_container_width=True):
            if not y_phrase:
                st.warning("Lütfen bir arama terimi girin.")
            else:
                params = build_manual_yargi_params(
                    phrase=y_phrase,
                    court_types=y_court_types or None,
                    chamber=selected_chamber_code,
                )
                if y_date_start:
                    params["date_start"] = y_date_start.strftime("%Y-%m-%d")
                if y_date_end:
                    params["date_end"] = y_date_end.strftime("%Y-%m-%d")

                with st.spinner("Yargı kararları aranıyor..."):
                    try:
                        do_yargi_search(params)
                    except Exception as e:
                        st.error(f"Arama hatası: {e}")

    # ── Yargı Display Area ───────────────────────────────────────────────────
    st.markdown("---")

    # Sort toggle
    if st.session_state["y_search_params"]:
        sort_col, _ = st.columns([2, 4])
        with sort_col:
            y_sort_options = {"Alakaya göre": "relevance", "Tarihe göre (yeni → eski)": "date"}
            current_y_sort = st.session_state.get("y_sort_by", "relevance")
            current_y_label = [k for k, v in y_sort_options.items() if v == current_y_sort][0]
            selected_y_sort = st.selectbox(
                "Sıralama",
                options=list(y_sort_options.keys()),
                index=list(y_sort_options.keys()).index(current_y_label),
                key="y_sort_select",
            )
            new_y_sort = y_sort_options[selected_y_sort]
            if new_y_sort != st.session_state.get("y_sort_by", "relevance"):
                st.session_state["y_sort_by"] = new_y_sort
                with st.spinner("Yeniden sıralanıyor..."):
                    try:
                        do_yargi_search(st.session_state["y_search_params"], sort_by=new_y_sort)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Arama hatası: {e}")

    # Search params display
    if st.session_state["y_search_params"]:
        params = st.session_state["y_search_params"]
        parts = []
        if params.get("phrase"):
            parts.append(f"**Arama:** {params['phrase']}")
        if params.get("court_types"):
            ct_labels = [COURT_TYPES.get(ct, ct) for ct in params["court_types"]]
            parts.append(f"**Mahkeme:** {', '.join(ct_labels)}")
        if params.get("chamber") and params["chamber"] != "ALL":
            chamber_name = CHAMBERS.get(params["chamber"], params["chamber"])
            parts.append(f"**Daire:** {chamber_name}")
        if parts:
            st.markdown(f'<div class="search-params">{" | ".join(parts)}</div>', unsafe_allow_html=True)

    # Search results
    if st.session_state["y_search_results"]:
        results = st.session_state["y_search_results"]
        decisions = results.get("decisions", [])
        total = results.get("totalRecords", 0)

        st.markdown(f"**{total} karar bulundu** (sayfa {results.get('page', 1)})")

        if not decisions:
            st.info("Aramanızla eşleşen karar bulunamadı. Farklı anahtar kelimelerle tekrar deneyin.")
        else:
            for i, dec in enumerate(decisions):
                court_label = COURT_TYPES.get(dec.get("courtType", ""), dec.get("courtTypeLabel", ""))
                birim = dec.get("birimAdi", "")
                esas_no = dec.get("esasNo", "")
                karar_no = dec.get("kararNo", "")
                karar_tarih = dec.get("kararTarihiStr", "")
                doc_id = dec.get("documentId", "")

                with st.container():
                    col_info, col_action = st.columns([5, 1])
                    with col_info:
                        title_parts = [court_label]
                        if birim:
                            title_parts.append(birim)
                        title_str = " — ".join(title_parts)

                        meta_parts = []
                        if esas_no:
                            meta_parts.append(f"Esas: {esas_no}")
                        if karar_no:
                            meta_parts.append(f"Karar: {karar_no}")
                        if karar_tarih:
                            meta_parts.append(f"Tarih: {karar_tarih}")
                        meta_str = " | ".join(meta_parts)

                        st.markdown(
                            f'<div class="result-card">'
                            f'<div class="result-title">{title_str}</div>'
                            f'<div class="result-meta">{meta_str}</div>'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    with col_action:
                        if st.button("📄 Oku", key=f"ydoc_{i}_{doc_id}"):
                            with st.spinner("Karar yükleniyor..."):
                                try:
                                    load_decision(doc_id)
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")

    # Decision content
    if st.session_state["y_decision_content"]:
        st.markdown("---")
        decision = st.session_state["y_decision_content"]
        if "error" in decision:
            st.error(f"Karar yüklenemedi: {decision['error']}")
        else:
            st.markdown("### 📄 Karar Metni")
            source_url = decision.get("sourceUrl", "")
            if source_url:
                st.markdown(f"[Kaynağa git →]({source_url})")
            st.markdown(
                f'<div class="article-content">{decision.get("content", "İçerik bulunamadı.")}</div>',
                unsafe_allow_html=True,
            )

    # Yargı empty state
    if not st.session_state["y_search_results"] and not st.session_state["y_decision_content"]:
        st.markdown("""
        <div style="text-align:center; padding: 2rem 1rem; color: #718096;">
            <p style="font-size: 2.5rem;">⚖️</p>
            <p style="font-size: 1rem;">Yargı kararlarında arama yapın</p>
            <p style="font-size: 0.85rem;">
                Yargıtay, Danıştay ve diğer mahkeme kararlarını arayın.
            </p>
        </div>
        """, unsafe_allow_html=True)
