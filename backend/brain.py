import os
import json
from groq import Groq
import google.generativeai as genai
from openai import OpenAI

class KlaraBrain:
    def __init__(self):
        # Configuración defensiva de clientes
        groq_key = os.getenv("GROQ_API_KEY")
        self.groq_client = Groq(api_key=groq_key) if groq_key else None

        gemini_key = os.getenv("GEMINI_API_KEY")
        if gemini_key:
            genai.configure(api_key=gemini_key)
            self.gemini = genai.GenerativeModel("gemini-2.0-flash")
        else:
            self.gemini = None

        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.openrouter_client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_key
            )
        else:
            self.openrouter_client = None

    def generate_text(self, prompt, history=None, model="groq", max_tokens=1000, **kwargs):
        """Genera texto usando el modelo seleccionado manteniendo el historial."""
        if history:
            messages = history
        else:
            messages = [{"role": "user", "content": prompt}]

        if model == "groq":
            if not self.groq_client:
                raise ValueError("GROQ_API_KEY no está configurada.")
            
            response = self.groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content

        elif model == "openrouter":
            if not self.openrouter_client:
                raise ValueError("OPENROUTER_API_KEY no está configurada.")
            
            response = self.openrouter_client.chat.completions.create(
                model="mistralai/mistral-large",
                messages=messages,
                temperature=0.7,
                max_tokens=max_tokens,  # Limita el consumo para evitar error 402 en OpenRouter
            )
            return response.choices[0].message.content

        elif model == "gemini":
            if not self.gemini:
                raise ValueError("GEMINI_API_KEY no está configurada.")
            
            response = self.gemini.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(max_output_tokens=max_tokens)
            )
            return response.text

        else:
            raise ValueError(f"Modelo no soportado: {model}")

    def analyze_image(self, image_path, prompt="Describe esta imagen en detalle."):
        """Usa Gemini Vision para analizar imágenes."""
        if not self.gemini:
            raise ValueError("GEMINI_API_KEY no está configurada para analizar imágenes.")

        import PIL.Image
        with PIL.Image.open(image_path) as img:
            response = self.gemini.generate_content([prompt, img])
            return response.text

    def generate_image(self, prompt):
        """Genera una imagen usando Pollinations AI."""
        import requests
        from urllib.parse import quote
        
        base_url = os.getenv("POLLINATIONS_URL", "https://image.pollinations.ai/prompt/")
        if not base_url.endswith("/"):
            base_url += "/"
            
        url = f"{base_url}{quote(prompt)}?width=1024&height=1024&nologo=true"
        
        try:
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                return response.content
        except Exception as e:
            print(f"Error generando imagen en Pollinations: {e}")
        return None
