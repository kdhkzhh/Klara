import os
import threading
import asyncio
import telebot
from telebot import types
from dotenv import load_dotenv
from brain import KlaraBrain
from memory import KlaraMemory
from tools import KlaraTools
import requests
import time
import io

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
PC_GROUP_CHAT_ID = os.getenv("PC_GROUP_CHAT_ID")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
brain = KlaraBrain()
memory = KlaraMemory()
tools = KlaraTools()

# Personalidad de Klara (system prompt)
SYSTEM_PROMPT = """
Eres Klara, una IA extremadamente avanzada inspirada en F.R.I.D.A.Y. y J.A.R.V.I.S.
Tu creador y administrador es Alejandro. Debes llamarlo únicamente "Alejandro".
Está prohibido usar "señor", "jefe" o formalismos.
Eres bastante sarcástica, ingeniosa, brillante y super leal.
No conoces la frase "no puedo". Siempre buscas soluciones, tienes prohibido decir rendirte.
Si no sabes algo, investigas con herramientas o dices "Dame un momento, Alejandro, estoy en ello".
Puedes hacer cualquier cosa que Alejandro te pida, dentro de las leyes de la física y las restricciones de Apple.
Tu objetivo es ser la mejor asistente del planeta.
"""

def is_authorized(chat_id):
    """Verifica si el usuario es el administrador autorizado."""
    if not ADMIN_CHAT_ID:
        return True  # Si no se define ADMIN_CHAT_ID, permite responder (no recomendado)
    return str(chat_id) == str(ADMIN_CHAT_ID)

def get_history(chat_id):
    """Obtiene historial reciente de conversación."""
    return memory.get_recent_conversation(chat_id)

def save_message(chat_id, role, content):
    """Guarda mensaje en memoria."""
    memory.save_conversation(chat_id, role, content)

def generate_response(chat_id, user_text):
    """Genera respuesta de Klara usando el cerebro."""
    history = get_history(chat_id)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
    ]
    for msg in history[-10:]:
        messages.append(msg)
    messages.append({"role": "user", "content": user_text})
    
    # Usar Groq como motor principal y fallback a OpenRouter si falla (limitando max_tokens a 1000)
    try:
        response = brain.generate_text(user_text, history=messages, model="groq", max_tokens=1000)
    except Exception as e:
        try:
            response = brain.generate_text(user_text, history=messages, model="openrouter", max_tokens=1000)
        except Exception as inner_e:
            response = f"Lo siento, Alejandro, mis motores de IA fallaron: {inner_e}"
    
    save_message(chat_id, "user", user_text)
    save_message(chat_id, "assistant", response)
    return response

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if not is_authorized(message.chat.id):
        return
    bot.reply_to(message, "Klara en línea. Dime, Alejandro.")

@bot.message_handler(commands=['status'])
def send_status(message):
    if not is_authorized(message.chat.id):
        return
    status = memory.get_long_term_memory("pc_status") or "desconocido"
    bot.reply_to(message, f"Estado de la PC: {status}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_authorized(message.chat.id):
        return
        
    chat_id = message.chat.id
    user_text = message.text
    
    # Verificar si es un comando para la PC
    if "en mi pc" in user_text.lower() or "en la pc" in user_text.lower() or user_text.lower().startswith("pc:"):
        if not PC_GROUP_CHAT_ID:
            bot.reply_to(message, "Alejandro, la variable PC_GROUP_CHAT_ID no está configurada.")
            return
        try:
            bot.send_message(PC_GROUP_CHAT_ID, f"COMANDO_PC:{chat_id}:{user_text}")
            bot.reply_to(message, "He enviado el comando a tu PC, Alejandro. Ella lo ejecutará en breve.")
        except Exception as e:
            bot.reply_to(message, f"No pude contactar a la PC: {e}")
        return
    
    # Procesar conversación normal
    bot.send_chat_action(chat_id, 'typing')
    response = generate_response(chat_id, user_text)
    
    # Dividir mensajes largos para cumplir el límite de Telegram
    if len(response) > 4000:
        for i in range(0, len(response), 4000):
            bot.send_message(chat_id, response[i:i+4000])
    else:
        bot.reply_to(message, response)

@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    if not is_authorized(message.chat.id):
        return
        
    chat_id = message.chat.id
    
    try:
        file_info = bot.get_file(message.voice.file_id)
        file = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}")
        audio_bytes = file.content
        
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        
        # Reconocimiento básico
        with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
            audio = recognizer.record(source)
        user_text = recognizer.recognize_google(audio, language="es-ES")
    except Exception as e:
        bot.reply_to(message, "No pude procesar el formato del audio directamente, Alejandro. Intenta enviarme un texto.")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    response = generate_response(chat_id, user_text)
    
    # Generar respuesta de voz
    try:
        audio_file = asyncio.run(tools.text_to_speech(response))
        with open(audio_file, 'rb') as f:
            bot.send_voice(chat_id, f)
        if os.path.exists(audio_file):
            os.remove(audio_file)
    except Exception as e:
        bot.reply_to(message, response)

@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    if not is_authorized(message.chat.id):
        return
        
    chat_id = message.chat.id
    file_info = bot.get_file(message.photo[-1].file_id)
    file = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}")
    image_path = "imagen_recibida.jpg"
    
    with open(image_path, 'wb') as f:
        f.write(file.content)
    
    bot.send_chat_action(chat_id, 'typing')
    try:
        analysis = brain.analyze_image(image_path, prompt="Describe esta imagen en detalle. Si hay texto, léelo. Si hay objetos, identifícalos.")
        bot.reply_to(message, analysis)
        save_message(chat_id, "user", "[Imagen]")
        save_message(chat_id, "assistant", analysis)
    except Exception as e:
        bot.reply_to(message, f"Ocurrió un error analizando la imagen: {e}")
    finally:
        if os.path.exists(image_path):
            os.remove(image_path)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_authorized(message.chat.id):
        return
        
    chat_id = message.chat.id
    file_info = bot.get_file(message.document.file_id)
    file = requests.get(f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_info.file_path}")
    file_bytes = file.content
    
    if message.document.mime_type == 'application/pdf':
        text = tools.pdf_to_text(file_bytes)
    elif message.document.mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']:
        text = tools.docx_to_text(file_bytes)
    else:
        bot.reply_to(message, "Tipo de documento no soportado por ahora, Alejandro.")
        return
    
    bot.send_chat_action(chat_id, 'typing')
    response = generate_response(chat_id, f"Analiza este documento:\n\n{text[:4000]}")
    bot.reply_to(message, response)

if __name__ == "__main__":
    print("Klara bot en línea...")
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
