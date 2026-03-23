"""
Mevzuat AI — Türk Mevzuatı Yapay Zekâ Asistanı
Hâkimler ve avukatlar için mevzuat.gov.tr tabanlı hukuk araştırma aracı.
Google Gemini (ücretsiz) ile çalışır.
"""

import streamlit as st
from ai_agent import run_agent


# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mevzuat AI",
    page_icon="⚖️",
    layout="centered",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp {
        max-width: 900px;
        margin: 0 auto;
    }
    .block-container {
        padding-top: 2rem;
    }
    .main-header {
        text-align: center;
        padding: 1.5rem 0 1rem 0;
        border-bottom: 2px solid #1a365d;
        margin-bottom: 1.5rem;
    }
    .main-header h1 {
        color: #1a365d;
        font-size: 2rem;
        margin-bottom: 0.25rem;
    }
    .main-header p {
        color: #4a5568;
        font-size: 1rem;
    }
    .stChatMessage {
        border-radius: 12px;
    }
    .sidebar-info {
        background: #f7fafc;
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        margin-bottom: 1rem;
        font-size: 0.9rem;
        line-height: 1.6;
    }
    .free-badge {
        background: #c6f6d5;
        color: #22543d;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ───────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
    <h1>⚖️ Mevzuat AI</h1>
    <p>Türk Mevzuatı Yapay Zekâ Araştırma Asistanı</p>
    <span class="free-badge">✓ Ücretsiz — Google Gemini</span>
</div>
""", unsafe_allow_html=True)

# ── API Key: prefer Streamlit secret, fall back to manual input ──────────────
_secret_key = st.secrets.get("GEMINI_API_KEY", None) if hasattr(st, "secrets") else None

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Ayarlar")

    if _secret_key:
        api_key = _secret_key
        st.success("✅ API anahtarı yapılandırılmış", icon="🔑")
    else:
        api_key = st.text_input(
            "Google Gemini API Anahtarı",
            type="password",
            help="Google AI Studio'dan ücretsiz API anahtarı alın",
        )
        st.markdown(
            '[🔑 Ücretsiz API anahtarı al →](https://aistudio.google.com/apikey)',
            unsafe_allow_html=True,
        )

    st.markdown("---")

    st.markdown("### 📖 Nasıl Kullanılır?")
    st.markdown("""
<div class="sidebar-info">
Sorunuzu doğal Türkçe ile yazmanız yeterlidir. Yapay zekâ sizin için:

1. **mevzuat.gov.tr**'de arama yapar
2. İlgili kanun/yönetmelik metnini okur
3. Sorunuza uygun maddeleri bulur
4. Anlaşılır biçimde yanıt verir
</div>
""", unsafe_allow_html=True)

    st.markdown("### 💡 Örnek Sorular")
    examples = [
        "Türk Ceza Kanunu'nun 141. maddesi ne diyor?",
        "İş Kanunu'na göre yıllık izin hakkı kaç gündür?",
        "Ticaret hukukunda rekabet yasağı hangi kanunda düzenleniyor?",
        "Kamulaştırma Kanunu'ndaki uzlaşma süreci nasıl işliyor?",
        "KVKK'ya göre veri sorumlusunun yükümlülükleri nelerdir?",
    ]
    for ex in examples:
        if st.button(ex, key=ex, use_container_width=True):
            st.session_state["pending_question"] = ex

    st.markdown("---")
    st.markdown(
        '<p style="font-size:0.8rem; color:#718096;">'
        'Kaynak: mevzuat.gov.tr (Adalet Bakanlığı)<br>'
        'Motor: Google Gemini 2.5 Flash (ücretsiz katman)<br>'
        'Bu araç bilgi amaçlıdır, hukuki danışmanlık yerine geçmez.</p>',
        unsafe_allow_html=True,
    )

# ── Session state ────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history" not in st.session_state:
    st.session_state.history = []

# ── Display chat history ─────────────────────────────────────────────────────
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="⚖️" if msg["role"] == "assistant" else "👤"):
        st.markdown(msg["content"])

# ── Handle input ─────────────────────────────────────────────────────────────
user_input = st.chat_input("Hukuki sorunuzu yazın...")

if "pending_question" in st.session_state:
    user_input = st.session_state.pop("pending_question")

if user_input:
    if not api_key:
        st.error(
            "⚠️ Lütfen sol paneldeki ayarlardan Google Gemini API anahtarınızı girin.\n\n"
            "Ücretsiz anahtar almak için: https://aistudio.google.com/apikey"
        )
        st.stop()

    # Show user message
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user", avatar="👤"):
        st.markdown(user_input)

    # Run agent and show response
    with st.chat_message("assistant", avatar="⚖️"):
        with st.spinner("Mevzuat araştırılıyor..."):
            try:
                response_text, updated_history = run_agent(
                    user_input,
                    st.session_state.history,
                    api_key,
                )
                st.session_state.history = updated_history
                st.markdown(response_text)
                st.session_state.messages.append({"role": "assistant", "content": response_text})
            except Exception as e:
                error_msg = str(e)
                if "api_key" in error_msg.lower() or "api key" in error_msg.lower() or "401" in error_msg:
                    st.error(
                        "❌ API anahtarı geçersiz. Lütfen kontrol edin.\n\n"
                        "Yeni anahtar almak için: https://aistudio.google.com/apikey"
                    )
                elif "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
                    st.error(
                        "⏳ Günlük ücretsiz istek limitine ulaşıldı. "
                        "Lütfen birkaç dakika bekleyip tekrar deneyin."
                    )
                else:
                    st.error(f"❌ Bir hata oluştu: {error_msg}")

# ── Empty state ──────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown("""
    <div style="text-align:center; padding: 3rem 1rem; color: #718096;">
        <p style="font-size: 3rem;">⚖️</p>
        <p style="font-size: 1.1rem;">Hoş geldiniz!</p>
        <p>Türk mevzuatıyla ilgili sorunuzu aşağıdaki alana yazabilir<br>
        veya sol paneldeki örnek sorulardan birini seçebilirsiniz.</p>
        <p style="margin-top:1rem; font-size:0.9rem;">
            <strong>Tamamen ücretsiz</strong> — Google Gemini ile çalışır.
        </p>
    </div>
    """, unsafe_allow_html=True)
