import os
from datetime import datetime, timezone
from supabase import create_client, Client

class KlaraMemory:
    def __init__(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        
        if not url or not key:
            print("⚠️ ADVERTENCIA: SUPABASE_URL o SUPABASE_KEY no están configuradas en el entorno.")
            self.supabase = None
        else:
            try:
                self.supabase: Client = create_client(url, key)
            except Exception as e:
                print(f"❌ Error al conectar con Supabase: {e}")
                self.supabase = None

    def save_conversation(self, chat_id, role, content):
        """Guarda un mensaje en la conversación."""
        if not self.supabase:
            return
        try:
            self.supabase.table("conversations").insert({
                "chat_id": str(chat_id),
                "role": role,
                "content": content,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error guardando conversación en Supabase: {e}")

    def get_recent_conversation(self, chat_id, limit=20):
        """Obtiene los últimos mensajes de un chat."""
        if not self.supabase:
            return []
        try:
            result = self.supabase.table("conversations") \
                .select("*") \
                .eq("chat_id", str(chat_id)) \
                .order("timestamp", desc=True) \
                .limit(limit) \
                .execute()
            
            data = result.data[::-1] if result.data else []
            return [{"role": d["role"], "content": d["content"]} for d in data]
        except Exception as e:
            print(f"Error leyendo historial desde Supabase: {e}")
            return []

    def save_long_term_memory(self, key, value):
        """Guarda o actualiza un hecho en memoria a largo plazo."""
        if not self.supabase:
            return
        try:
            self.supabase.table("long_term_memory").upsert({
                "key": key,
                "value": value,
                "updated_at": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error guardando memoria a largo plazo: {e}")

    def get_long_term_memory(self, key):
        """Recupera un hecho de memoria a largo plazo."""
        if not self.supabase:
            return None
        try:
            result = self.supabase.table("long_term_memory") \
                .select("value") \
                .eq("key", key) \
                .execute()
            if result.data:
                return result.data[0]["value"]
            return None
        except Exception as e:
            print(f"Error leyendo memoria a largo plazo: {e}")
            return None

    def update_device_status(self, device_id, status):
        """Actualiza el estado de un dispositivo."""
        if not self.supabase:
            return
        try:
            self.supabase.table("device_status").upsert({
                "device_id": device_id,
                "status": status,
                "last_seen": datetime.now(timezone.utc).isoformat()
            }).execute()
        except Exception as e:
            print(f"Error actualizando estado de dispositivo: {e}")