"""
Query Parser — Converts natural language to Bedesten API search parameters.
Uses a single Gemini call (~600 tokens) instead of a multi-iteration agent loop.
"""

import json
from google import genai
from google.genai import types


PARSER_PROMPT = """Sen bir arama sorgusu çıkarıcısın. Kullanıcının doğal dilde yazdığı hukuki soruyu,
Bedesten mevzuat API'si için yapılandırılmış arama parametrelerine dönüştür.

Yanıtını YALNIZCA aşağıdaki JSON formatında ver, başka hiçbir şey yazma:

{
  "phrase": "arama kelimesi veya ifadesi",
  "title": "mevzuat başlığı (varsa)",
  "types": ["KANUN"],
  "number": "mevzuat numarası (varsa)",
  "exact": false
}

Kurallar:
- phrase: Ana arama terimi. Kullanıcının sorduğu konunun özünü yaz.
- title: Belirli bir kanun/yönetmelik adı geçiyorsa onu yaz. Yoksa null.
- types: Uygun mevzuat türlerini seç. Birden fazla olabilir. Boş bırakma, en az bir tür seç.
  Türler: KANUN, CB_KARARNAME, YONETMELIK, CB_YONETMELIK, KHK, TUZUK, KKY, TEBLIGLER, MULGA
  Eğer tür belli değilse ["KANUN", "YONETMELIK", "CB_YONETMELIK", "KHK", "KKY", "TEBLIGLER"] yaz.
- number: Kanun numarası belirtilmişse (ör: "5237 sayılı kanun") → "5237". Yoksa null.
- exact: Tam eşleşme gerekiyorsa true, genelde false.

Örnekler:
Soru: "İş Kanunu'nda fazla mesai ücreti nasıl hesaplanır?"
→ {"phrase": "fazla mesai ücreti", "title": "iş kanunu", "types": ["KANUN"], "number": null, "exact": false}

Soru: "6098 sayılı Borçlar Kanunu'nun 49. maddesi ne diyor?"
→ {"phrase": "haksız fiil tazminat", "title": "borçlar kanunu", "types": ["KANUN"], "number": "6098", "exact": false}

Soru: "Son çıkan iş sağlığı yönetmelikleri nelerdir?"
→ {"phrase": "iş sağlığı", "title": null, "types": ["YONETMELIK", "CB_YONETMELIK", "KKY"], "number": null, "exact": false}

Soru: "KVKK'ya göre veri sorumlusunun yükümlülükleri"
→ {"phrase": "veri sorumlusu yükümlülük", "title": "kişisel verilerin korunması", "types": ["KANUN"], "number": "6698", "exact": false}

YALNIZCA JSON döndür. Açıklama, yorum veya başka metin yazma."""


def parse_query(user_message: str, api_key: str) -> dict:
    """
    Parse a natural language legal question into structured search parameters.
    Returns dict with keys: phrase, title, types, number, exact.
    Uses ~600 tokens total.
    """
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[user_message],
        config=types.GenerateContentConfig(
            system_instruction=PARSER_PROMPT,
            temperature=0.1,
            max_output_tokens=200,
        ),
    )

    text = response.text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        params = json.loads(text)
    except json.JSONDecodeError:
        # Fallback: use the user's message as a plain search
        params = {
            "phrase": user_message,
            "title": None,
            "types": ["KANUN", "YONETMELIK", "CB_YONETMELIK", "KHK", "KKY", "TEBLIGLER"],
            "number": None,
            "exact": False,
        }

    # Normalize nulls
    for key in ["phrase", "title", "number"]:
        if params.get(key) in (None, "", "null"):
            params[key] = None

    if not params.get("types"):
        params["types"] = ["KANUN", "YONETMELIK", "CB_YONETMELIK", "KHK", "KKY", "TEBLIGLER"]

    if "exact" not in params:
        params["exact"] = False

    return params


def build_manual_params(phrase: str = None, title: str = None, types: list = None,
                        number: str = None, exact: bool = False) -> dict:
    """Build search params manually (no AI, zero tokens)."""
    return {
        "phrase": phrase or None,
        "title": title or None,
        "types": types or ["KANUN", "YONETMELIK", "CB_YONETMELIK", "KHK", "KKY", "TEBLIGLER"],
        "number": number or None,
        "exact": exact,
    }
