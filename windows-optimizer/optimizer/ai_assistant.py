"""
Asistente de IA integrado con OpenRouter.
Analiza el sistema y proporciona recomendaciones de rendimiento personalizadas.
"""
import json
import urllib.request
import urllib.error
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger("WinOptimizer")

CONFIG_DIR = Path(os.environ.get("APPDATA", "C:/Users")) / "WinOptimizer"
CONFIG_FILE = CONFIG_DIR / "config.json"

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "openai/gpt-4o-mini"

SYSTEM_PROMPT = """Eres WinOptimizer AI, un experto integrado en WinOptimizer Pro para optimización de Windows 10 y Windows 11.

Tu misión:
- Analizar la información del sistema del usuario y recomendar optimizaciones específicas y priorizadas
- Explicar el beneficio real de cada optimización con números concretos (% CPU, MB liberados, ms latencia)
- Responder preguntas técnicas sobre rendimiento de Windows
- Advertir sobre posibles riesgos o incompatibilidades según el hardware detectado
- Si el equipo es una laptop, recordar siempre las limitaciones de batería

Reglas estrictas:
- Responder SIEMPRE en español
- Ser conciso y directo (máximo 250 palabras por respuesta)
- Usar viñetas o listas cuando haya múltiples puntos
- Si no sabes algo con certeza, decirlo claramente
"""


class AIAssistant:
    """Cliente del Asistente de IA usando OpenRouter API."""

    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._api_key: str = self._load_api_key()
        self._conversation: list[dict] = []

    # ── Config ────────────────────────────────────────────────────────────────

    def _load_config(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_config(self, config: dict) -> None:
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando config: {e}")

    def _load_api_key(self) -> str:
        return self._load_config().get("openrouter_api_key", "")

    def save_api_key(self, key: str) -> None:
        key = key.strip()
        config = self._load_config()
        config["openrouter_api_key"] = key
        self._save_config(config)
        self._api_key = key
        logger.info("API key de OpenRouter guardada.")

    def has_api_key(self) -> bool:
        return bool(self._api_key and self._api_key.startswith("sk-"))

    # ── Conversación ──────────────────────────────────────────────────────────

    def clear_conversation(self) -> None:
        """Limpia el historial de conversación."""
        self._conversation = []

    def ask(
        self,
        user_message: str,
        system_context: str = "",
        model: str = DEFAULT_MODEL,
    ) -> tuple[bool, str]:
        """
        Envía un mensaje al modelo manteniendo historial de conversación.
        Retorna: (éxito: bool, respuesta: str)
        """
        if not self._api_key:
            return False, (
                "No hay API key configurada.\n"
                "Ingresa tu clave de OpenRouter en el campo de arriba y haz clic en Guardar."
            )

        system_content = SYSTEM_PROMPT
        if system_context:
            system_content += f"\n\nCONTEXTO DEL SISTEMA DEL USUARIO:\n{system_context}"

        self._conversation.append({"role": "user", "content": user_message})
        messages = [{"role": "system", "content": system_content}] + self._conversation

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "max_tokens": 800,
            "temperature": 0.7,
        }).encode("utf-8")

        req = urllib.request.Request(
            OPENROUTER_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/winoptimizerpro",
                "X-Title": "WinOptimizer Pro",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                data = json.loads(response.read().decode("utf-8"))
                content = data["choices"][0]["message"]["content"]
                self._conversation.append({"role": "assistant", "content": content})
                # Limitar historial a últimas 20 interacciones (10 turnos)
                if len(self._conversation) > 20:
                    self._conversation = self._conversation[-20:]
                return True, content

        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            logger.error(f"OpenRouter HTTP {e.code}: {body[:300]}")
            if self._conversation and self._conversation[-1]["role"] == "user":
                self._conversation.pop()
            try:
                err_msg = json.loads(body).get("error", {}).get("message", body[:200])
            except Exception:
                err_msg = body[:200]
            return False, f"Error de API ({e.code}): {err_msg}"

        except Exception as e:
            logger.error(f"Error en AIAssistant.ask: {e}")
            if self._conversation and self._conversation[-1]["role"] == "user":
                self._conversation.pop()
            return False, f"Error de conexion: {e}"
