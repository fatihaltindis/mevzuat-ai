"""
Mevzuat API Client
Calls the Bedesten (mevzuat.gov.tr) REST API directly from Python.
No Node.js or npm required.
"""

import requests
import base64
import re
from html import unescape


BASE_URL = "https://bedesten.adalet.gov.tr/mevzuat"

HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
    "AdaletApplicationName": "UyapMevzuat",
    "Content-Type": "application/json; charset=utf-8",
    "Origin": "https://mevzuat.adalet.gov.tr",
    "Referer": "https://mevzuat.adalet.gov.tr/",
}

TIMEOUT = 60


def _post(endpoint: str, body: dict) -> dict:
    """Make a POST request to the Bedesten API."""
    url = f"{BASE_URL}{endpoint}"
    resp = requests.post(url, json=body, headers=HEADERS, timeout=TIMEOUT)
    resp.raise_for_status()
    return resp.json()


def _html_to_text(html: str) -> str:
    """Convert HTML to readable plain text (lightweight, no dependencies)."""
    # Remove style/script blocks
    text = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # Convert <br>, <p>, <div>, <tr>, headings to newlines
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(p|div|tr|h[1-6]|li|blockquote)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<td[^>]*>", "  ", text, flags=re.IGNORECASE)
    # Remove all remaining tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entities
    text = unescape(text)
    # Normalize whitespace
    lines = [line.strip() for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    # Collapse multiple newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def search_legislation(
    phrase: str = None,
    title: str = None,
    types: list[str] = None,
    number: str = None,
    exact: bool = False,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    Search Turkish legislation.
    At least one of phrase or title must be provided.
    types: list of e.g. ["KANUN", "KHK", "YONETMELIK"]
    """
    search_data = {
        "pageSize": page_size,
        "pageNumber": page,
        "sortFields": ["RESMI_GAZETE_TARIHI"],
        "sortDirection": "desc",
    }
    if phrase:
        search_data["phrase"] = phrase
    if title:
        search_data["mevzuatAdi"] = title
    if types:
        search_data["mevzuatTurList"] = types
    if number:
        search_data["mevzuatNo"] = number
    if exact:
        search_data["tamCumle"] = True

    body = {
        "data": search_data,
        "applicationName": "UyapMevzuat",
        "paging": True,
    }

    response = _post("/searchDocuments", body)
    data = response.get("data", {})

    documents = []
    for doc in data.get("mevzuatList", []):
        documents.append({
            "mevzuatId": doc.get("mevzuatId"),
            "mevzuatNo": doc.get("mevzuatNo"),
            "mevzuatAdi": doc.get("mevzuatAdi"),
            "tur": doc.get("mevzuatTur", {}).get("name", ""),
            "turAciklama": doc.get("mevzuatTur", {}).get("description", ""),
            "resmiGazeteTarihi": doc.get("resmiGazeteTarihi"),
            "resmiGazeteSayisi": doc.get("resmiGazeteSayisi"),
            "gerekceId": doc.get("gerekceId"),
        })

    return {
        "documents": documents,
        "totalRecords": data.get("total", 0),
        "page": page,
        "pageSize": page_size,
    }


def get_document(mevzuat_id: str) -> dict:
    """Get full legislation document content by mevzuatId."""
    body = {
        "data": {"documentType": "MEVZUAT", "id": str(mevzuat_id)},
        "applicationName": "UyapMevzuat",
    }

    response = _post("/getDocumentContent", body)

    meta = response.get("metadata", {})
    if meta.get("FMTY") != "SUCCESS":
        return {"error": meta.get("FMTE", "Belge alınamadı")}

    data = response.get("data", {})
    content_b64 = data.get("content", "")
    if not content_b64:
        return {"error": "Belge içeriği boş"}

    html = base64.b64decode(content_b64).decode("utf-8")
    text = _html_to_text(html)

    return {
        "mevzuatId": mevzuat_id,
        "content": text,
    }


def get_article(madde_id: str) -> dict:
    """Get a single article by maddeId."""
    body = {
        "data": {"documentType": "MADDE", "id": str(madde_id)},
        "applicationName": "UyapMevzuat",
    }

    response = _post("/getDocumentContent", body)

    meta = response.get("metadata", {})
    if meta.get("FMTY") != "SUCCESS":
        return {"error": meta.get("FMTE", "Madde alınamadı")}

    data = response.get("data", {})
    content_b64 = data.get("content", "")
    if not content_b64:
        return {"error": "Madde içeriği boş"}

    html = base64.b64decode(content_b64).decode("utf-8")
    text = _html_to_text(html)

    return {
        "maddeId": madde_id,
        "content": text,
    }


def get_article_tree(mevzuat_id: str) -> dict:
    """Get the table of contents / article tree for a legislation."""
    body = {
        "data": {"mevzuatId": str(mevzuat_id)},
        "applicationName": "UyapMevzuat",
    }

    response = _post("/mevzuatMaddeTree", body)

    meta = response.get("metadata", {})
    if meta.get("FMTY") != "SUCCESS":
        return {"error": meta.get("FMTE", "İçindekiler alınamadı")}

    data = response.get("data", {})
    children = data.get("children", [])

    def flatten(nodes, depth=0):
        items = []
        for node in nodes:
            items.append({
                "maddeId": node.get("maddeId"),
                "maddeNo": node.get("maddeNo"),
                "title": node.get("title", node.get("maddeBaslik", "")),
                "gerekceId": node.get("gerekceId"),
                "depth": depth,
            })
            if node.get("children"):
                items.extend(flatten(node["children"], depth + 1))
        return items

    flat_tree = flatten(children)

    return {
        "mevzuatId": mevzuat_id,
        "totalNodes": len(flat_tree),
        "tree": flat_tree,
    }
