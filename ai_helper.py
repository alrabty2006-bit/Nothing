import os
import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY", ""))
model = genai.GenerativeModel("gemini-1.5-flash")


def ask_ai(question: str) -> str:
    try:
        prompt = (
            "أنت مساعد ذكاء اصطناعي مفيد باسم ATOM. "
            "أجب على السؤال التالي باختصار وبشكل واضح باللغة العربية أو الإنجليزية حسب لغة السؤال:\n\n"
            + question
        )
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"عذراً، حدث خطأ في الذكاء الاصطناعي: {str(e)}"
