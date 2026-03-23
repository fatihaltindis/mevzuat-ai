"""
Mevzuat AI — Türk Mevzuatı ve Yargı Kararları Araştırma Aracı
Hâkimler ve avukatlar için mevzuat.gov.tr tabanlı hukuk araştırma aracı.
AI yalnızca sorgu ayrıştırma için kullanılır (~600 token). Sonuçlar doğrudan API'den gösterilir.
"""

import os
import math
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

# ── Load CSS from file ───────────────────────────────────────────────────────
_css_path = os.path.join(os.path.dirname(__file__), "style.css")
with open(_css_path) as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

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

PAGE_SIZE = 10

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
    "m_sort_by": "relevance",
    "m_page": 1,
    "m_expanded_id": None,    # which mevzuat result is expanded
    "m_expanded_type": None,  # "toc", "doc", or "article"
    "m_expanded_data": None,  # the loaded content
    "m_toc_data": None,       # TOC for expanded mevzuat
    # Yargı state
    "y_search_results": None,
    "y_search_params": None,
    "y_page": 1,
    "y_expanded_id": None,    # which decision is expanded
    "y_expanded_data": None,  # the loaded decision content
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ══════════════════════════════════════════════════════════════════════════════
# MEVZUAT HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def do_mevzuat_search(params: dict, sort_by: str = "relevance", page: int = 1):
    """Execute mevzuat search and store results."""
    result = search_legislation(
        phrase=params.get("phrase"),
        title=params.get("title"),
        types=params.get("types"),
        number=params.get("number"),
        exact=params.get("exact", False),
        sort_by=sort_by,
        page=page,
        page_size=PAGE_SIZE,
    )
    st.session_state["m_search_results"] = result
    st.session_state["m_search_params"] = params
    st.session_state["m_page"] = page
    st.session_state["m_expanded_id"] = None
    st.session_state["m_expanded_type"] = None
    st.session_state["m_expanded_data"] = None
    st.session_state["m_toc_data"] = None


# ══════════════════════════════════════════════════════════════════════════════
# YARGI HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def do_yargi_search(params: dict, sort_by: str = "relevance", page: int = 1):
    """Execute yargı search and store results."""
    result = search_decisions(
        phrase=params.get("phrase"),
        court_types=params.get("court_types"),
        chamber=params.get("chamber", "ALL"),
        date_start=params.get("date_start"),
        date_end=params.get("date_end"),
        sort_by=sort_by,
        page=page,
        page_size=PAGE_SIZE,
    )
    st.session_state["y_search_results"] = result
    st.session_state["y_search_params"] = params
    st.session_state["y_page"] = page
    st.session_state["y_expanded_id"] = None
    st.session_state["y_expanded_data"] = None


# ══════════════════════════════════════════════════════════════════════════════
# PAGINATION HELPER
# ══════════════════════════════════════════════════════════════════════════════

def render_pagination(total: int, current_page: int, page_size: int, key_prefix: str):
    """Render prev/next pagination and return new page if changed, else None."""
    total_pages = max(1, math.ceil(total / page_size))

    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_info:
        st.markdown(
            f'<div class="pagination-info" style="text-align:center;">'
            f'Sayfa {current_page} / {total_pages} ({total} sonuç)'
            f'</div>',
            unsafe_allow_html=True,
        )
    with col_prev:
        if current_page > 1:
            if st.button("← Önceki", key=f"{key_prefix}_prev", use_container_width=True):
                return current_page - 1
    with col_next:
        if current_page < total_pages:
            if st.button("Sonraki →", key=f"{key_prefix}_next", use_container_width=True):
                return current_page + 1
    return None


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
        with st.form("m_nl_form", clear_on_submit=False):
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
            m_nl_submitted = st.form_submit_button("🔍 Ara", use_container_width=True)

        if m_nl_submitted and m_nl_input:
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
        with st.form("m_manual_form", clear_on_submit=False):
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

            m_manual_submitted = st.form_submit_button("🔍 Ara", use_container_width=True)

        if m_manual_submitted:
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
        current_page = st.session_state["m_page"]

        # Top pagination
        new_page = render_pagination(total, current_page, PAGE_SIZE, "m_top")
        if new_page:
            with st.spinner("Sayfa yükleniyor..."):
                do_mevzuat_search(
                    st.session_state["m_search_params"],
                    sort_by=st.session_state["m_sort_by"],
                    page=new_page,
                )
                st.rerun()

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
                                        toc = get_article_tree(mevzuat_id)
                                        st.session_state["m_expanded_id"] = mevzuat_id
                                        st.session_state["m_expanded_type"] = "toc"
                                        st.session_state["m_toc_data"] = toc
                                        st.session_state["m_expanded_data"] = {"name": name}
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Hata: {e}")
                        with bcol2:
                            if st.button("📄 Tam Metin", key=f"doc_{i}_{mevzuat_id}"):
                                with st.spinner("Belge yükleniyor..."):
                                    try:
                                        doc_content = get_document(mevzuat_id)
                                        toc = get_article_tree(mevzuat_id)
                                        st.session_state["m_expanded_id"] = mevzuat_id
                                        st.session_state["m_expanded_type"] = "doc"
                                        st.session_state["m_expanded_data"] = doc_content
                                        st.session_state["m_toc_data"] = toc
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"Hata: {e}")

                    # ── Inline expanded content (right below this result) ────
                    if st.session_state["m_expanded_id"] == mevzuat_id:
                        exp_type = st.session_state["m_expanded_type"]
                        exp_data = st.session_state["m_expanded_data"]
                        toc_data = st.session_state.get("m_toc_data")

                        # Show TOC
                        if toc_data and exp_type in ("toc", "doc", "article"):
                            with st.expander(f"📑 {name} — İçindekiler", expanded=(exp_type == "toc")):
                                if "error" in toc_data:
                                    st.error(f"İçindekiler yüklenemedi: {toc_data['error']}")
                                else:
                                    tree = toc_data.get("tree", [])
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
                                                    if st.button("Göster", key=f"art_{i}_{j}_{madde_id}"):
                                                        with st.spinner("Madde yükleniyor..."):
                                                            try:
                                                                article = get_article(madde_id)
                                                                st.session_state["m_expanded_type"] = "article"
                                                                st.session_state["m_expanded_data"] = article
                                                                st.rerun()
                                                            except Exception as e:
                                                                st.error(f"Hata: {e}")

                        # Show article content
                        if exp_type == "article" and exp_data:
                            with st.expander("📄 Madde Metni", expanded=True):
                                if "error" in exp_data:
                                    st.error(f"Madde yüklenemedi: {exp_data['error']}")
                                else:
                                    st.markdown(
                                        f'<div class="article-content">{exp_data.get("content", "İçerik bulunamadı.")}</div>',
                                        unsafe_allow_html=True,
                                    )

                        # Show full document
                        if exp_type == "doc" and exp_data and "content" in exp_data:
                            with st.expander("📄 Tam Metin", expanded=True):
                                if "error" in exp_data:
                                    st.error(f"Belge yüklenemedi: {exp_data['error']}")
                                else:
                                    st.markdown(
                                        f'<div class="article-content">{exp_data.get("content", "İçerik bulunamadı.")}</div>',
                                        unsafe_allow_html=True,
                                    )

            # Bottom pagination
            new_page_bottom = render_pagination(total, current_page, PAGE_SIZE, "m_bottom")
            if new_page_bottom:
                with st.spinner("Sayfa yükleniyor..."):
                    do_mevzuat_search(
                        st.session_state["m_search_params"],
                        sort_by=st.session_state["m_sort_by"],
                        page=new_page_bottom,
                    )
                    st.rerun()

    # Mevzuat empty state
    if not st.session_state["m_search_results"]:
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
        with st.form("y_nl_form", clear_on_submit=False):
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
            y_nl_submitted = st.form_submit_button("🔍 Ara", use_container_width=True)

        if y_nl_submitted and y_nl_input:
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
        with st.form("y_manual_form", clear_on_submit=False):
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

            y_manual_submitted = st.form_submit_button("🔍 Ara", use_container_width=True)

        if y_manual_submitted:
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
        current_page = st.session_state["y_page"]

        # Top pagination
        new_page = render_pagination(total, current_page, PAGE_SIZE, "y_top")
        if new_page:
            with st.spinner("Sayfa yükleniyor..."):
                do_yargi_search(
                    st.session_state["y_search_params"],
                    sort_by="date",
                    page=new_page,
                )
                st.rerun()

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
                                    decision_data = get_decision(doc_id)
                                    st.session_state["y_expanded_id"] = doc_id
                                    st.session_state["y_expanded_data"] = decision_data
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"Hata: {e}")

                    # ── Inline decision content (right below this result) ────
                    if st.session_state["y_expanded_id"] == doc_id:
                        exp_data = st.session_state["y_expanded_data"]
                        if exp_data:
                            with st.expander("📄 Karar Metni", expanded=True):
                                if "error" in exp_data:
                                    st.error(f"Karar yüklenemedi: {exp_data['error']}")
                                else:
                                    source_url = exp_data.get("sourceUrl", "")
                                    if source_url:
                                        st.markdown(f"[Kaynağa git →]({source_url})")
                                    st.markdown(
                                        f'<div class="article-content">{exp_data.get("content", "İçerik bulunamadı.")}</div>',
                                        unsafe_allow_html=True,
                                    )

            # Bottom pagination
            new_page_bottom = render_pagination(total, current_page, PAGE_SIZE, "y_bottom")
            if new_page_bottom:
                with st.spinner("Sayfa yükleniyor..."):
                    do_yargi_search(
                        st.session_state["y_search_params"],
                        sort_by="date",
                        page=new_page_bottom,
                    )
                    st.rerun()

    # Yargı empty state
    if not st.session_state["y_search_results"]:
        st.markdown("""
        <div style="text-align:center; padding: 2rem 1rem; color: #718096;">
            <p style="font-size: 2.5rem;">⚖️</p>
            <p style="font-size: 1rem;">Yargı kararlarında arama yapın</p>
            <p style="font-size: 0.85rem;">
                Yargıtay, Danıştay ve diğer mahkeme kararlarını arayın.
            </p>
        </div>
        """, unsafe_allow_html=True)
