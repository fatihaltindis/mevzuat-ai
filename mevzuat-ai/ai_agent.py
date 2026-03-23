"""
Mevzuat AI Agent — Google Gemini Edition
Uses Gemini 2.5 Flash (free tier) with function calling.
Free: ~1500 requests/day, no credit card needed.
"""

import json
from google import genai
from google.genai import types
from mevzuat_client import search_legislation, get_document, get_article, get_article_tree


SYSTEM_PROMPT = """Sen Türk hukuku konusunda uzman bir yapay zekâ asistanısın.
Görevin, kullanıcının (hâkim, avukat, hukuk araştırmacısı) Türk mevzuatıyla ilgili sorularını yanıtlamaktır.

Elindeki araçlarla mevzuat.gov.tr üzerinden arama yapabilir, kanun/yönetmelik metinlerine erişebilir
ve belirli maddeleri okuyabilirsin.

Kurallar:
- Her zaman Türkçe yanıt ver.
- Önce aramayı yap, sonra gerekli belge/maddeyi oku, ardından kullanıcıya net ve anlaşılır biçimde cevap ver.
- Madde numarası, kanun numarası gibi somut bilgileri her zaman belirt.
- Yanıtlarını hukuki dilin anlaşılır bir Türkçesiyle ver; gereksiz teknik jargondan kaçın.
- Eğer bir konuda kesin bilgi bulamadıysan, bunu açıkça belirt.
- Birden fazla araç çağrısı yapabilirsin — önce ara, sonra ilgili belgeyi veya maddeyi oku.

Mevzuat Türleri:
- KANUN: Kanunlar
- CB_KARARNAME: Cumhurbaşkanlığı Kararnameleri
- YONETMELIK: Bakanlar Kurulu Yönetmelikleri
- CB_YONETMELIK: Cumhurbaşkanlığı Yönetmelikleri
- KHK: Kanun Hükmünde Kararnameler
- TUZUK: Tüzükler
- KKY: Kurum ve Kuruluş Yönetmelikleri
- TEBLIGLER: Tebliğler
- MULGA: Mülga Kanunlar
"""

# ── Tool declarations (JSON Schema format for Gemini) ─────────────────────

TOOL_DECLARATIONS = [
    {
        "name": "mevzuat_ara",
        "description": (
            "Türk mevzuatında arama yapar. İçerik araması (phrase) veya başlık araması (title) yapabilir. "
            "En az birini belirtmelisin. Sonuçlar JSON olarak döner."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "phrase": {
                    "type": "string",
                    "description": "İçerik araması (ör: 'ceza kanunu', 'vergi', '+iş +güvenliği')",
                },
                "title": {
                    "type": "string",
                    "description": "Başlık araması (ör: 'türk ticaret kanunu', 'iş kanunu')",
                },
                "types": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Mevzuat türü filtresi: KANUN, CB_KARARNAME, YONETMELIK, CB_YONETMELIK, CB_KARAR, CB_GENELGE, KHK, TUZUK, KKY, UY, TEBLIGLER, MULGA",
                },
                "number": {
                    "type": "string",
                    "description": "Mevzuat numarası (ör: '5237', '6102')",
                },
                "exact": {
                    "type": "boolean",
                    "description": "Tam eşleşme araması",
                },
            },
        },
    },
    {
        "name": "belge_getir",
        "description": (
            "Bir mevzuatın tam metnini getirir. mevzuat_id gereklidir (arama sonuçlarından alınır)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "Mevzuat ID (arama sonuçlarındaki mevzuatId)",
                },
            },
            "required": ["mevzuat_id"],
        },
    },
    {
        "name": "madde_getir",
        "description": "Tek bir maddeyi getirir. madde_id gereklidir (içindekiler ağacından alınır).",
        "parameters": {
            "type": "object",
            "properties": {
                "madde_id": {
                    "type": "string",
                    "description": "Madde ID (içindekiler ağacındaki maddeId)",
                },
            },
            "required": ["madde_id"],
        },
    },
    {
        "name": "icindekiler_getir",
        "description": (
            "Bir mevzuatın içindekiler tablosunu (madde ağacını) getirir. "
            "Her maddenin maddeId'si, numarası ve başlığı listelenir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "mevzuat_id": {
                    "type": "string",
                    "description": "Mevzuat ID",
                },
            },
            "required": ["mevzuat_id"],
        },
    },
]


def _execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Execute a tool and return the result as a dict."""
    try:
        if tool_name == "mevzuat_ara":
            result = search_legislation(
                phrase=tool_input.get("phrase"),
                title=tool_input.get("title"),
                types=tool_input.get("types"),
                number=tool_input.get("number"),
                exact=tool_input.get("exact", False),
            )
        elif tool_name == "belge_getir":
            result = get_document(tool_input["mevzuat_id"])
        elif tool_name == "madde_getir":
            result = get_article(tool_input["madde_id"])
        elif tool_name == "icindekiler_getir":
            result = get_article_tree(tool_input["mevzuat_id"])
        else:
            result = {"error": f"Bilinmeyen araç: {tool_name}"}
    except Exception as e:
        result = {"error": str(e)}

    return result


def run_agent(user_message: str, history: list, api_key: str) -> tuple[str, list]:
    """
    Run one turn of the AI agent loop using Gemini.
    Returns (assistant_text, updated_history).

    history is a list of types.Content objects.
    """
    client = genai.Client(api_key=api_key)

    # Build tool config
    tools = types.Tool(function_declarations=TOOL_DECLARATIONS)
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=[tools],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0.3,
    )

    # Add user message to history
    history.append(
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        )
    )

    MAX_ITERATIONS = 10

    for _ in range(MAX_ITERATIONS):
        # Call Gemini
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=history,
            config=config,
        )

        candidate = response.candidates[0]

        # Collect the model's response parts (preserve all including thought signatures)
        model_parts = list(candidate.content.parts) if candidate.content and candidate.content.parts else []

        # Add model response to history
        history.append(
            types.Content(role="model", parts=model_parts)
        )

        # Check if there are function calls in the response
        function_calls = [p for p in model_parts if p.function_call]

        if not function_calls:
            # No function calls — extract final text
            text_parts = [p.text for p in model_parts if p.text]
            final_text = "\n".join(text_parts) if text_parts else "Yanıt oluşturulamadı."
            return final_text, history

        # Execute each function call and build responses
        function_responses = []
        for part in function_calls:
            fc = part.function_call
            args = dict(fc.args) if fc.args else {}
            result = _execute_tool(fc.name, args)

            function_responses.append(
                types.Part.from_function_response(
                    name=fc.name,
                    response=result,
                )
            )

        # Add function responses to history
        history.append(
            types.Content(role="user", parts=function_responses)
        )

    return "Üzgünüm, çok fazla adım gerekti. Lütfen sorunuzu daraltarak tekrar deneyin.", history
