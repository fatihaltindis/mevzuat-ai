"""
Yargı API Client
Calls the Bedesten emsal-karar (court decisions) REST API directly from Python.
Mirrors yargi-cli's bedesten-client.ts functionality.
"""

import requests
import base64
import re
from html import unescape


BASE_URL = "https://bedesten.adalet.gov.tr"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "AdaletApplicationName": "UyapMevzuat",
    "Content-Type": "application/json; charset=utf-8",
    "Origin": "https://mevzuat.adalet.gov.tr",
    "Referer": "https://mevzuat.adalet.gov.tr/",
}

TIMEOUT = 60

# ── Court types ──────────────────────────────────────────────────────────────

COURT_TYPES = {
    "YARGITAYKARARI": "Yargıtay Kararı",
    "DANISTAYKARAR": "Danıştay Kararı",
    "YERELHUKUK": "Yerel Hukuk",
    "ISTINAFHUKUK": "İstinaf Hukuk",
    "KYB": "Kanun Yararına Bozma",
}

DEFAULT_COURT_TYPES = ["YARGITAYKARARI", "DANISTAYKARAR"]

# ── Chamber codes → full Turkish names ───────────────────────────────────────

CHAMBERS = {
    "ALL": None,
    # Yargıtay - Hukuk Daireleri
    "H1": "1. Hukuk Dairesi", "H2": "2. Hukuk Dairesi", "H3": "3. Hukuk Dairesi",
    "H4": "4. Hukuk Dairesi", "H5": "5. Hukuk Dairesi", "H6": "6. Hukuk Dairesi",
    "H7": "7. Hukuk Dairesi", "H8": "8. Hukuk Dairesi", "H9": "9. Hukuk Dairesi",
    "H10": "10. Hukuk Dairesi", "H11": "11. Hukuk Dairesi", "H12": "12. Hukuk Dairesi",
    "H13": "13. Hukuk Dairesi", "H14": "14. Hukuk Dairesi", "H15": "15. Hukuk Dairesi",
    "H16": "16. Hukuk Dairesi", "H17": "17. Hukuk Dairesi", "H18": "18. Hukuk Dairesi",
    "H19": "19. Hukuk Dairesi", "H20": "20. Hukuk Dairesi", "H21": "21. Hukuk Dairesi",
    "H22": "22. Hukuk Dairesi", "H23": "23. Hukuk Dairesi",
    # Yargıtay - Ceza Daireleri
    "C1": "1. Ceza Dairesi", "C2": "2. Ceza Dairesi", "C3": "3. Ceza Dairesi",
    "C4": "4. Ceza Dairesi", "C5": "5. Ceza Dairesi", "C6": "6. Ceza Dairesi",
    "C7": "7. Ceza Dairesi", "C8": "8. Ceza Dairesi", "C9": "9. Ceza Dairesi",
    "C10": "10. Ceza Dairesi", "C11": "11. Ceza Dairesi", "C12": "12. Ceza Dairesi",
    "C13": "13. Ceza Dairesi", "C14": "14. Ceza Dairesi", "C15": "15. Ceza Dairesi",
    "C16": "16. Ceza Dairesi", "C17": "17. Ceza Dairesi", "C18": "18. Ceza Dairesi",
    "C19": "19. Ceza Dairesi", "C20": "20. Ceza Dairesi", "C21": "21. Ceza Dairesi",
    "C22": "22. Ceza Dairesi", "C23": "23. Ceza Dairesi",
    # Yargıtay - Kurullar
    "HGK": "Hukuk Genel Kurulu",
    "CGK": "Ceza Genel Kurulu",
    "BGK": "Büyük Genel Kurulu",
    "HBK": "Hukuk Daireleri Başkanlar Kurulu",
    "CBK": "Ceza Daireleri Başkanlar Kurulu",
    # Danıştay - Daireler
    "D1": "1. Daire", "D2": "2. Daire", "D3": "3. Daire",
    "D4": "4. Daire", "D5": "5. Daire", "D6": "6. Daire",
    "D7": "7. Daire", "D8": "8. Daire", "D9": "9. Daire",
    "D10": "10. Daire", "D11": "11. Daire", "D12": "12. Daire",
    "D13": "13. Daire", "D14": "14. Daire", "D15": "15. Daire",
    "D16": "16. Daire", "D17": "17. Daire",
    # Danıştay - Kurullar
    "DBGK": "Büyük Gen.Kur.",
    "IDDK": "İdare Dava Daireleri Kurulu",
    "VDDK": "Vergi Dava Daireleri Kurulu",
    "IBK": "İçtihatları Birleştirme Kurulu",
    "IIK": "İdari İşler Kurulu",
    "DBK": "Başkanlar Kurulu",
    # Askeri
    "AYIM": "Askeri Yüksek İdare Mahkemesi",
    "AYIMDK": "Askeri Yüksek İdare Mahkemesi Daireleri Kurulu",
    "AYIMB": "Askeri Yüksek İdare Mahkemesi Başsavcılığı",
    "AYIM1": "Askeri Yüksek İdare Mahkemesi 1. Daire",
    "AYIM2": "Askeri Yüksek İdare Mahkemesi 2. Daire",
    "AYIM3": "Askeri Yüksek İdare Mahkemesi 3. Daire",
}

# User-friendly chamber groupings for the UI
CHAMBER_GROUPS = {
    "Tümü": ["ALL"],
    "Yargıtay Hukuk Daireleri": [f"H{i}" for i in range(1, 24)],
    "Yargıtay Ceza Daireleri": [f"C{i}" for i in range(1, 24)],
    "Yargıtay Kurulları": ["HGK", "CGK", "BGK", "HBK", "CBK"],
    "Danıştay Daireleri": [f"D{i}" for i in range(1, 18)],
    "Danıştay Kurulları": ["DBGK", "IDDK", "VDDK", "IBK", "IIK", "DBK"],
}


# ── Internal helpers ─────────────────────────────────────────────────────────

def _post(endpoint: str, body: dict) -> dict:
    """Make a POST request to the Bedesten API."""
    url = f"{BASE_URL}{endpoint}"
    resp = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _html_to_text(html: str) -> str:
    """Convert HTML to readable plain text."""
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(p|div|tr|h[1-6]|li|blockquote)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<td[^>]*>", "  ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = unescape(text)
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _format_date_start(date_str: str) -> str:
    """Convert YYYY-MM-DD to ISO 8601 start-of-day."""
    if "T" in date_str or date_str.endswith("Z"):
        return date_str
    return f"{date_str}T00:00:00.000Z"


def _format_date_end(date_str: str) -> str:
    """Convert YYYY-MM-DD to ISO 8601 end-of-day."""
    if "T" in date_str or date_str.endswith("Z"):
        return date_str
    return f"{date_str}T23:59:59.999Z"


def _add_solr_prefix(phrase: str) -> str:
    """Add Solr '+' prefix to each word to require all terms match."""
    if not phrase:
        return phrase
    words = phrase.split()
    prefixed = []
    for w in words:
        if w[0] in "+-" or "*" in w or "~" in w or "^" in w:
            prefixed.append(w)
        else:
            prefixed.append(f"+{w}")
    return " ".join(prefixed)


# ── Public API ───────────────────────────────────────────────────────────────

def search_decisions(
    phrase: str,
    court_types: list[str] = None,
    chamber: str = "ALL",
    date_start: str = None,
    date_end: str = None,
    page: int = 1,
    page_size: int = 10,
    sort_by: str = "relevance",
) -> dict:
    """
    Search Turkish court decisions.
    phrase: required search query
    court_types: list of court type codes (default: YARGITAYKARARI, DANISTAYKARAR)
    chamber: chamber code from CHAMBERS dict (default: ALL)
    date_start/date_end: YYYY-MM-DD format
    sort_by: "relevance" or "date"
    """
    if court_types is None:
        court_types = DEFAULT_COURT_TYPES

    search_data = {
        "pageSize": page_size,
        "pageNumber": page,
        "itemTypeList": court_types,
        "phrase": _add_solr_prefix(phrase),
    }

    # Always include sortFields — emsal-karar API may require it
    search_data["sortFields"] = ["KARAR_TARIHI"]
    search_data["sortDirection"] = "desc"

    # Chamber filter
    if chamber and chamber != "ALL":
        birim_adi = CHAMBERS.get(chamber)
        if birim_adi:
            search_data["birimAdi"] = birim_adi

    # Date filters
    if date_start:
        search_data["kararTarihiStart"] = _format_date_start(date_start)
    if date_end:
        search_data["kararTarihiEnd"] = _format_date_end(date_end)

    body = {
        "data": search_data,
        "applicationName": "UyapMevzuat",
        "paging": True,
    }

    response = _post("/emsal-karar/searchDocuments", body)
    data = response.get("data", {}) or {}

    decisions = []
    for entry in data.get("emsalKararList", []):
        item_type = entry.get("itemType", {})
        decisions.append({
            "documentId": entry.get("documentId"),
            "courtType": item_type.get("name", ""),
            "courtTypeLabel": item_type.get("description", ""),
            "birimAdi": entry.get("birimAdi"),
            "esasNo": entry.get("esasNo"),
            "kararNo": entry.get("kararNo"),
            "kararTarihiStr": entry.get("kararTarihiStr", ""),
            "kararTarihi": entry.get("kararTarihi", ""),
        })

    return {
        "decisions": decisions,
        "totalRecords": data.get("total", 0),
        "page": page,
        "pageSize": page_size,
    }


def get_decision(document_id: str) -> dict:
    """Get a court decision document by its ID. Returns plain text content."""
    body = {
        "data": {"documentId": str(document_id)},
        "applicationName": "UyapMevzuat",
    }

    response = _post("/emsal-karar/getDocumentContent", body)
    data = response.get("data", {}) or {}

    content_b64 = data.get("content", "")
    mime_type = data.get("mimeType", "")

    if not content_b64:
        return {"error": "Karar içeriği bulunamadı"}

    raw = base64.b64decode(content_b64).decode("utf-8", errors="replace")

    if "html" in mime_type.lower():
        text = _html_to_text(raw)
    else:
        text = raw

    return {
        "documentId": document_id,
        "content": text,
        "sourceUrl": f"https://mevzuat.adalet.gov.tr/ictihat/{document_id}",
        "mimeType": mime_type,
    }
