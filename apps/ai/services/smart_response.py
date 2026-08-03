import json
import logging
import re
from .response_generator import RESPONSE_SYSTEM_PROMPT
from .metadata_builder import build_metadata
from .product_search import search_products

logger = logging.getLogger(__name__)

def generate_smart_response(provider, conversation_messages, intent, max_tokens=4000):
    system = RESPONSE_SYSTEM_PROMPT
    
    if intent == "greeting":
        system += (
            "\nDIQQAT: Foydalanuvchi faqat salomlashmoqda. "
            "JAVOBING JUDA QISQA BO'LSIN (1-2 gap). "
            "Misol: 'Assalomu alaykum! ZIG ZAG pardalar do'koniga xush kelibsiz. Sizga qanday yordam bera olaman?' "
            "Qo'shimcha maslahat yoki ma'lumot YOZMA!"
        )
    elif intent in ["product_search", "information_question"]:
        metadata = build_metadata()
        system += (
            f"\n\nDO'KON BAZASI (Faqat ma'lumot uchun):\n{json.dumps(metadata, ensure_ascii=False)}\n\n"
            "DIQQAT: Agar foydalanuvchi aniq bir turdagi, rangdagi yoki xonaga mos mahsulot qidirayotganini bilsang, "
            "javobingning ENG OXIRIGA qidiruv filtrini quyidagi formatda qo'sh (albatta <filters> taglari ichida):\n"
            "<filters>\n{\n  \"materials\": [\"Blackout\"],\n  \"colors\": [\"Oq\"],\n  \"room\": \"Yotoqxona\",\n  \"style\": \"Klassika\",\n  \"category\": \"Jalyuzi\"\n}\n</filters>\n"
            "MUHIM QOIDA: <filters> ichidagi qiymatlar ALBATTA yuqoridagi DO'KON BAZASI dagi qatorlarga so'zma-so'z to'g'ri kelishi shart! Tarjima qilmang! "
            "QOIDA 2: Hech qachon DO'KON BAZASI dagi hamma variantlarni ro'yxat qilib mijozga sanab bermang (masalan 'Ranglardan oq, qora, qizil bor...' demang). Mijozdan faqat 'Sizga qanday rang yoki uslubdagi parda ma'qul keladi?' deb tabiiy so'rang, misollar keltirmang.\n"
            "Tabiiy tildagi javobingda esa bemalol tarjima qilib ishlataver. Agar qidiruv talab qilinmasa, <filters> tagini yozma."
        )

    result = provider.chat(
        system=system,
        messages=conversation_messages,
        max_tokens=max_tokens,
    )
    
    response_text = (result.content or "").strip()
    suggestions = []
    
    # Extract filters
    match = re.search(r"<filters>(.*?)</filters>", response_text, re.DOTALL)
    if match:
        filter_json = match.group(1).strip()
        try:
            filters_data = json.loads(filter_json)
            suggestions = search_products(filters_data)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse smart filters: {filter_json}")
        
        # Remove the <filters> block from the response shown to the user
        response_text = re.sub(r"<filters>.*?</filters>", "", response_text, flags=re.DOTALL).strip()
        
    if not response_text:
        response_text = "Kechirasiz, javob yaratishda xatolik yuz berdi."
        
    return response_text, result, suggestions
