import os

from dotenv import load_dotenv
import google.generativeai as genai


class LLMManager:
    def __init__(self) -> None:
        # .envファイルの読み込み
        load_dotenv()

        # API-KEYの設定
        GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
        genai.configure(api_key=GOOGLE_API_KEY)
        self.gemini_model = genai.GenerativeModel("gemini-2.0-flash")

    def infer(self, prompt: str) -> str:
        return self.gemini_model.generate_context(prompt)
