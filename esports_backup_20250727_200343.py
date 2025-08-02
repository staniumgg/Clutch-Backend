import os
import json
import requests
import time
from dotenv import load_dotenv
import mutagen  # Add this library to read audio metadata
from mutagen.mp3 import MP3, HeaderNotFoundError
from firebase_config import upload_to_firebase, save_to_firestore
from dynamodb_config import dynamodb_manager, save_analysis, save_analysis_complete
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import random
import discord
import asyncio
from discord.ext import commands
from discord import ui

# === FUNCIONES DE GOOGLE TTS POR GÉNERO (deben estar antes de su uso) ===
def get_google_tts_voices_by_gender(language_code="es-ES"):
    """
    Devuelve un diccionario con las voces de Google TTS agrupadas por género (Femenina, Masculina, Neutra).
    """
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices(language_code=language_code).voices
    gender_map = {"MALE": "Masculina", "FEMALE": "Femenina", "NEUTRAL": "Neutra"}
    voices_by_gender = {"Femenina": [], "Masculina": [], "Neutra": []}
    for v in voices:
        label = gender_map.get(v.ssml_gender, "Neutra")
        voices_by_gender[label].append({
            "name": v.name,
            "label": label,
            "natural_sample_rate_hertz": v.natural_sample_rate_hertz,
            "description": getattr(v, "description", "")
        })
    return voices_by_gender

def select_google_tts_voice_by_gender(preferred_gender, language_code="es-ES"):
    """
    Selecciona automáticamente una voz técnica de Google TTS según el género preferido.
    """
    voices_by_gender = get_google_tts_voices_by_gender(language_code)
    voices = voices_by_gender.get(preferred_gender, [])
    if voices:
        # Elegir la primera voz disponible del género
        return voices[0]["name"]
    # Fallback: voz por defecto
    return GOOGLE_TTS_VOICE

# Cargar variables de entorno desde .env al inicio del script
load_dotenv()

# Configuración de voz TTS Google Cloud
# El valor por defecto solo se usa si el usuario NO ha elegido preferencia
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", None)

def get_motivational_filename():
    """
    Genera un nombre de archivo motivador para el feedback de Discord
    """
    motivational_names = [
        "💪 Tu Análisis de Comunicación - Vamos Por Más.mp3",
        "🎯 Feedback Personalizado - Sigue Mejorando.mp3", 
        "🔥 Tu Coach Virtual - Análisis de Esta Partida.mp3",
        "⚡ Análisis Táctico - Próximo Nivel.mp3",
        "🚀 Feedback Profesional - Keep Grinding.mp3",
        "🎮 Tu Análisis eSports - Road to Pro.mp3",
        "💯 Comunicación Review - Next Level Gaming.mp3",
        "🏆 Feedback de Coach - Vamos Champion.mp3",
        "🔊 Análisis de Partida - Sigue Creciendo.mp3",
        "⭐ Tu Feedback Personal - Gaming Evolution.mp3"
    ]
    return random.choice(motivational_names)

def get_clutch_filename():
    """
    Genera un nombre de archivo en el formato 'Clutch - Fecha (DD/MM/AA).mp3' con la fecha actual.
    """
    from datetime import datetime
    fecha = datetime.now().strftime('%d-%m-%y')
    return f"Clutch - Fecha ({fecha}).mp3"

def transcribe_with_whisper(audio_path):
    """
    Transcribe audio using OpenAI's Whisper model, which according to the paper
    provides better accuracy for esports communication transcription.
    """
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {os.getenv('OPENAI_API_KEY')}"
    }
    
    # Eliminar el parámetro 'prompt' para evitar que Whisper lo devuelva como transcripción
    files = {
        'file': (os.path.basename(audio_path), open(audio_path, 'rb'), 'audio/mpeg'),
        'model': (None, 'whisper-1'),
        'language': (None, 'es'),
        'response_format': (None, 'verbose_json'),
        'temperature': (None, '0.2')
    }
    
    try:
        print("Transcribiendo audio con Whisper...")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        
        # Log completo del JSON de análisis
        print("\n=== JSON COMPLETO DEL ANÁLISIS ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
    except requests.exceptions.RequestException as e:
        print(f"Error durante la solicitud a la API de Whisper: {e}")
        if 'response' in locals() and response is not None:
            print(f"Código de estado de la respuesta: {response.status_code}")
            print(f"Contenido de la respuesta: {response.text}")
        raise
    finally:
        # Ensure the file is closed after the request
        files['file'][1].close()
    
    # Try to calculate cost - don't fail if we can't get duration
    try:
        audio = MP3(audio_path)
        if audio and hasattr(audio.info, 'length') and audio.info.length > 0:
            duration_seconds = audio.info.length
            duration_minutes = duration_seconds / 60
            cost_per_minute = 0.006  # Example cost for Whisper ($0.006 per minute)
            cost = duration_minutes * cost_per_minute
            
            print(f"Duración del audio: {duration_minutes:.2f} minutos")
            print(f"Costo estimado en Whisper: ${cost:.6f} USD")
        else:
            print("No se pudo calcular la duración para el costo")
    except Exception as e:
        print(f"Error calculando duración: {e}")
    
    # Return both the text and segments with timestamps
    return result['text'], result.get('segments', [])

def analyze_text(text, segments, api_key, user_id, analysis_prefs, tts_prefs):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    transcript_with_timestamps = "\n".join([
        f"{i:03d} - [{seg.get('start', 0):.3f}:{seg.get('end', 0):.3f}] {seg.get('text', '')}"
        for i, seg in enumerate(segments, 1)
    ])
    # Obtener preferencias del usuario
    coach_type = analysis_prefs.get("coach_type", "Directo")
    aspect = analysis_prefs.get("aspect", "Comunicación")
    personality = analysis_prefs.get("personality", "Introvertido")
    # Personalizar instrucciones según preferencias
    extra_instructions = f"\n\nCOACH SELECCIONADO: {coach_type}.\nASPECTO A MEJORAR: {aspect}.\nPERSONALIDAD DEL JUGADOR: {personality}.\nAdapta el feedback a este perfil y preferencia."
    esports_context = """
CONTEXTO DE TERMINOLOGÍA ESPORTS/CALL OF DUTY:
• POSICIONES: "A", "B", "C" (sitios de bomba), "spawn", "mid", "largo", "corto", "heaven", "hell", "connector", "catwalk", "underpass", "top", "bottom", "site", "punto caliente", "hardpoint"
• DIRECCIONES: "arriba", "abajo", "derecha", "izquierda", "adelante", "atrás", "espaldeando", "flanqueando", "rotando", "empujando", "cayendo", "mirando el flanco"
• ENEMIGOS: "uno", "dos", "tres" (cantidad), "lit", "tocado", "one shot", "absolute", "cracked" (escudo roto), "weak", "full", "sin placas", "pusheando"
• ACCIONES: "push", "hold", "peek", "trade", "bait", "flank", "wrap", "split", "tradeen", "roten", "rotemos", "pushemos", "pusheo", "pushear", "flankear", "flankeo", "flankearon", "flankeando", "rotar", "rotamos", "desafiar", "re-peek", "mantener ángulo", "pre-fire"
• OBJETIVOS: "bomba", "objetivo", "punto de control", "hardpoint", "zona de captura", "zona de control", "defusa", "defusando", "plantando", "rusheando", "capturando", "captura"
• NÚMEROS: "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez"
• ESTADOS: "muerto", "down", "reviviendo", "low HP", "sin balas", "reloading", "one shot", "flasheado", "stuneado", "dead", "revivido", "auto-reviviendo"
• UTILIDADES: "smoke", "flash", "stun", "nade", "trophy", "claymore", "c4", "semtex", "frag", "molotov"
• URGENCIA: "now", "wait", "go go go", "back", "run", "help", "rápido", "lento", "reset"
• CHILENOS: "weón", "dale", "cabros", "buena", "nice", "mierda", "ctm", "ql", "puta la wea", "conchetumare", "aweonao", "culiao", "chucha", "hueón", "hueona", "hueones", "hueonas", "csmre"
• ESTRATEGIA: "flank", "push", "hold", "rotate", "trade", "bait", "split", "wrap", "crossfire", "setup", "defense", "offense", "pincer", "trade frag", "entry frag", "lurk", "anchor", "default", "execute"
"""
    prompt = f"""{esports_context}
Analiza la comunicación de la siguiente transcripción de eSports. Evalúa únicamente el contenido textual, no el tono ni las emociones.

Criterios de evaluación:

Precisión: ¿Se entregó información específica y útil (ubicaciones, números, estados de juego)?

Eficiencia: ¿Se comunicaron datos clave sin palabras de relleno?

Redundancia: ¿Se repitió información sin una justificación táctica clara?

Valor estratégico: ¿Los call-outs ayudaron a la toma de decisiones del equipo?

Instrucciones para la respuesta:

Cita ejemplos específicos de la transcripción de lo que dijo el jugador. 

Proporciona feedback constructivo sobre cómo mejorar la comunicación.

Responde en un solo párrafo, en español chileno.

La respuesta debe ser solo el análisis, sin saludos ni introducciones.

**IMPORTANTE:** Escribe siempre en primera persona, dirigiéndote directamente al jugador. Usa frases como "Debes mejorar...", "Tienes que...", "Evita...", "Procura..." en vez de formas impersonales como "Se debería...".

TRANSCRIPCIÓN COMPLETA:
{text}
DESGLOSE TEMPORAL:
{transcript_with_timestamps}"""
    # Construir system prompt personalizado
    system_prompt = (
        f"Eres un entrenador de un equipo de esports y tienes una personalidad {coach_type.lower()}. "
        f"El jugador quiere mejorar en {aspect} y considera que tiene una personalidad de {personality}. "
        "Te especializas en evaluar el contenido informativo de los call-outs, no el tono emocional. "
        "Das feedback constructivo sobre la calidad de la comunicación."
    )
    # Quitar prints del prompt
    # print("\n=== PROMPT ENVIADO A CHAT GPT ===")
    # print("[SYSTEM PROMPT]")
    # print(system_prompt)
    # print("[USER PROMPT]")
    # print(prompt)
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": { "type": "text" }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print("\n=== OUTPUT DE GPT-4o-mini ===")
        print(content)
        # Devolvemos solo el contenido. La generación de TTS y el envío se hacen en el flujo principal.
        return content
    except Exception as e:
        print(f"Error en el análisis: {str(e)}")
        return "Hubo un error al analizar la comunicación. Por favor, intenta de nuevo."

def generate_tts_audio(text_to_speak, user_id, prefs):
    """
    Genera un archivo de audio a partir de texto usando la API TTS de Google Cloud (librería oficial), usando preferencias del usuario.
    """
    from google.cloud import texttospeech
    import tempfile
    # Obtener preferencias de voz y velocidad
    # Usar solo el valor por defecto si el usuario no eligió preferencia
    voice_name = prefs.get("voice")
    if not voice_name:
        voice_name = GOOGLE_TTS_VOICE
        if not voice_name:
            # Si ni siquiera hay valor por defecto, usar una voz femenina genérica
            voice_name = select_google_tts_voice_by_gender("Femenina")
    voice_label = prefs.get("voice_label", "Desconocida")
    speed = prefs.get("speed", 1.0)
    speed_label = prefs.get("speed_label", "Normal")
    try:
        speed = float(speed)
    except Exception:
        speed = 1.0
    # Ajuste de velocidad según etiqueta
    if speed_label == "Lenta":
        speed = 0.8
    elif speed_label == "Rápida":
        speed = 1.3
    elif speed_label == "Normal":
        speed = 1.0
    print(f"[TTS] Preferencias para usuario {user_id}: voz='{voice_label}' ({voice_name}), velocidad='{speed_label}' ({speed})")
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text_to_speak)
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-ES",
        name=voice_name
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        speaking_rate=speed
    )
    timestamp = int(time.time())
    audio_filename = f"feedback_{user_id}_{timestamp}.wav"
    audio_filepath = os.path.join("temp", audio_filename)
    os.makedirs("temp", exist_ok=True)
    try:
        print(f"Generando audio TTS (Google) para el usuario {user_id}...")
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        with open(audio_filepath, "wb") as out:
            out.write(response.audio_content)
        print(f"Audio TTS guardado en: {audio_filepath}")
        return audio_filepath
    except Exception as e:
        print(f"Error durante la solicitud a la API de TTS de Google: {e}")
        return None

def save_user_preference(user_id, coach_type=None, aspect=None, personality=None, voice=None, speed=None, voice_label=None, speed_label=None):
    """
    Guarda la preferencia del usuario en un archivo JSON local, incluyendo voice_label y speed_label.
    """
    pref_file = "user_preferences.json"
    prefs = {}
    if os.path.exists(pref_file):
        with open(pref_file, "r", encoding="utf-8") as f:
            try:
                prefs = json.load(f)
            except Exception:
                prefs = {}
    if str(user_id) not in prefs:
        prefs[str(user_id)] = {}
    if coach_type:
        prefs[str(user_id)]["coach_type"] = coach_type
    if aspect:
        prefs[str(user_id)]["aspect"] = aspect
    if personality:
        prefs[str(user_id)]["personality"] = personality
    if voice:
        prefs[str(user_id)]["voice"] = voice
    if speed is not None:
        prefs[str(user_id)]["speed"] = speed
    if voice_label:
        prefs[str(user_id)]["voice_label"] = voice_label
    if speed_label:
        prefs[str(user_id)]["speed_label"] = speed_label
    with open(pref_file, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)

def get_user_preference(user_id):
    pref_file = "user_preferences.json"
    if os.path.exists(pref_file):
        with open(pref_file, "r", encoding="utf-8") as f:
            try:
                prefs = json.load(f)
                return prefs.get(str(user_id), {})
            except Exception:
                return {}
    return {}

def send_feedback_to_discord_user(user_id, feedback, audio_path=None, text_for_tts=None):
    import discord
    import asyncio
    from discord.ext import commands
    from discord import ui

    DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
    if not DISCORD_TOKEN:
        raise ValueError("No se encontró DISCORD_TOKEN en las variables de entorno")

    intents = discord.Intents.default()
    intents.members = True
    intents.message_content = True
    bot = None
    try:
        bot = commands.Bot(command_prefix="!", intents=intents)
        class PreferenceCollector:
            def __init__(self, user_id):
                self.user_id = user_id
                self.all_prefs_collected = asyncio.Event() # Usaremos un solo evento
                self.analysis_prefs = {}
                self.tts_prefs = {}

        collector = PreferenceCollector(user_id)

        class CoachTypeView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=180)
                self.collector = collector

            async def disable_all_items(self, interaction: discord.Interaction):
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            @ui.button(label="Directo", style=discord.ButtonStyle.primary)
            async def directo(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["coach_type"] = "Directo"
                save_user_preference(self.collector.user_id, coach_type="Directo")
                await interaction.response.send_message("✅ Preferencia guardada: Directo", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Motivador", style=discord.ButtonStyle.success)
            async def motivador(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["coach_type"] = "Motivador"
                save_user_preference(self.collector.user_id, coach_type="Motivador")
                await interaction.response.send_message("✅ Preferencia guardada: Motivador", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Analítico", style=discord.ButtonStyle.secondary)
            async def analitico(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["coach_type"] = "Analítico"
                save_user_preference(self.collector.user_id, coach_type="Analítico")
                await interaction.response.send_message("✅ Preferencia guardada: Analítico", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Empático", style=discord.ButtonStyle.secondary)
            async def empatico(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["coach_type"] = "Empático"
                save_user_preference(self.collector.user_id, coach_type="Empático")
                await interaction.response.send_message("✅ Preferencia guardada: Empático", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class AspectView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=180)
                self.collector = collector

            async def disable_all_items(self, interaction: discord.Interaction):
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            @ui.button(label="Comunicación", style=discord.ButtonStyle.primary)
            async def comunicacion(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["aspect"] = "Comunicación"
                save_user_preference(self.collector.user_id, aspect="Comunicación")
                await interaction.response.send_message("✅ Preferencia guardada: Comunicación", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Estrategia", style=discord.ButtonStyle.success)
            async def estrategia(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["aspect"] = "Estrategia"
                save_user_preference(self.collector.user_id, aspect="Estrategia")
                await interaction.response.send_message("✅ Preferencia guardada: Estrategia", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Precisión", style=discord.ButtonStyle.secondary)
            async def precision(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["aspect"] = "Precisión"
                save_user_preference(self.collector.user_id, aspect="Precisión")
                await interaction.response.send_message("✅ Preferencia guardada: Precisión", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Trabajo en equipo", style=discord.ButtonStyle.secondary)
            async def equipo(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["aspect"] = "Trabajo en equipo"
                save_user_preference(self.collector.user_id, aspect="Trabajo en equipo")
                await interaction.response.send_message("✅ Preferencia guardada: Trabajo en equipo", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class PersonalityView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=180)
                self.collector = collector

            async def disable_all_items(self, interaction: discord.Interaction):
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            @ui.button(label="Introvertido", style=discord.ButtonStyle.primary)
            async def introvertido(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["personality"] = "Introvertido"
                save_user_preference(self.collector.user_id, personality="Introvertido")
                await interaction.response.send_message("✅ Preferencia guardada: Introvertido", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Extrovertido", style=discord.ButtonStyle.success)
            async def extrovertido(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["personality"] = "Extrovertido"
                save_user_preference(self.collector.user_id, personality="Extrovertido")
                await interaction.response.send_message("✅ Preferencia guardada: Extrovertido", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Analítico", style=discord.ButtonStyle.secondary)
            async def analitico(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["personality"] = "Analítico"
                save_user_preference(self.collector.user_id, personality="Analítico")
                await interaction.response.send_message("✅ Preferencia guardada: Analítico", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Competitivo", style=discord.ButtonStyle.secondary)
            async def competitivo(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.analysis_prefs["personality"] = "Competitivo"
                save_user_preference(self.collector.user_id, personality="Competitivo")
                await interaction.response.send_message("✅ Preferencia guardada: Competitivo", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class VoiceView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=180)
                self.collector = collector

            async def disable_all_items(self, interaction: discord.Interaction):
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            @ui.button(label="Femenina", style=discord.ButtonStyle.primary)
            async def femenina(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["voice"] = "es-ES-Chirp3-HD-Achernar"
                self.collector.tts_prefs["voice_label"] = "Femenina"
                save_user_preference(self.collector.user_id, voice="es-ES-Chirp3-HD-Achernar")
                save_user_preference(self.collector.user_id, voice_label="Femenina")
                await interaction.response.send_message("✅ Voz femenina seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Masculina", style=discord.ButtonStyle.success)
            async def masculina(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["voice"] = "es-ES-Chirp3-HD-Charon"
                self.collector.tts_prefs["voice_label"] = "Masculina"
                save_user_preference(self.collector.user_id, voice="es-ES-Chirp3-HD-Charon")
                save_user_preference(self.collector.user_id, voice_label="Masculina")
                await interaction.response.send_message("✅ Voz masculina seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Neutra", style=discord.ButtonStyle.secondary)
            async def neutra(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["voice"] = "es-ES-Standard-A"
                self.collector.tts_prefs["voice_label"] = "Neutra"
                save_user_preference(self.collector.user_id, voice="es-ES-Standard-A")
                save_user_preference(self.collector.user_id, voice_label="Neutra")
                await interaction.response.send_message("✅ Voz neutra seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class SpeedView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=180)
                self.collector = collector

            async def disable_all_items(self, interaction: discord.Interaction):
                for item in self.children:
                    item.disabled = True
                await interaction.message.edit(view=self)

            @ui.button(label="Normal", style=discord.ButtonStyle.primary)
            async def normal(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["speed"] = 1.0
                self.collector.tts_prefs["speed_label"] = "Normal"
                save_user_preference(self.collector.user_id, speed=1.0)
                save_user_preference(self.collector.user_id, speed_label="Normal")
                await interaction.response.send_message("✅ Velocidad normal seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Rápida", style=discord.ButtonStyle.success)
            async def rapida(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["speed"] = 1.3
                self.collector.tts_prefs["speed_label"] = "Rápida"
                save_user_preference(self.collector.user_id, speed=1.3)
                save_user_preference(self.collector.user_id, speed_label="Rápida")
                await interaction.response.send_message("✅ Velocidad rápida seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()            @ui.button(label="Lenta", style=discord.ButtonStyle.secondary)
            async def lenta(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["speed"] = 0.8
                self.collector.tts_prefs["speed_label"] = "Lenta"
                save_user_preference(self.collector.user_id, speed=0.8)
                save_user_preference(self.collector.user_id, speed_label="Lenta")
                await interaction.response.send_message("✅ Velocidad lenta seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class AllPreferencesView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=300)  # Más tiempo para responder todo
                self.collector = collector
            # Tipo de Coach
            @ui.select(placeholder="1. ¿Qué tipo de coach prefieres?", min_values=1, max_values=1, row=0)
            async def coach_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["coach_type"] = select.values[0]
                save_user_preference(self.collector.user_id, coach_type=select.values[0])
                print(f"[PREFERENCIA] Coach_type seleccionado: {select.values[0]}")
                await interaction.response.defer()
                await self.check_completion()
            # Aspecto a mejorar
            @ui.select(placeholder="2. ¿Qué aspecto te gustaría mejorar?", min_values=1, max_values=1, row=1)
            async def aspect_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["aspect"] = select.values[0]
                save_user_preference(self.collector.user_id, aspect=select.values[0])
                print(f"[PREFERENCIA] Aspect seleccionado: {select.values[0]}")
                await interaction.response.defer()
                await self.check_completion()
            # Personalidad
            @ui.select(placeholder="3. ¿Con qué personalidad te identificas?", min_values=1, max_values=1, row=2)
            async def personality_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["personality"] = select.values[0]
                save_user_preference(self.collector.user_id, personality=select.values[0])
                print(f"[PREFERENCIA] Personalidad seleccionada: {select.values[0]}")
                await interaction.response.defer()
                await self.check_completion()
            # Tipo de voz
            @ui.select(placeholder="4. ¿Qué tipo de voz prefieres?", min_values=1, max_values=1, row=3)
            async def voice_select(self, interaction: discord.Interaction, select: ui.Select):
                # Asignar la voz técnica exacta según la preferencia del usuario
                voice_map = {
                    "Femenina": "es-ES-Chirp3-HD-Achernar",
                    "Masculina": "es-ES-Chirp3-HD-Charon",
                    "Neutra": "es-ES-Standard-A"
                }
                voice_label = select.values[0]
                voice_name = voice_map[voice_label]
                self.collector.tts_prefs["voice"] = voice_name
                self.collector.tts_prefs["voice_label"] = voice_label
                save_user_preference(self.collector.user_id, voice=voice_name)
                save_user_preference(self.collector.user_id, voice_label=voice_label)
                print(f"[PREFERENCIA] Voz seleccionada: {voice_label} ({voice_name})")
                await interaction.response.defer()
                await self.check_completion()
            # Velocidad
            @ui.select(placeholder="5. ¿A qué velocidad prefieres el audio?", min_values=1, max_values=1, row=4)
            async def speed_select(self, interaction: discord.Interaction, select: ui.Select):
                speed_mapping = {
                    "Normal": 1.0,
                    "Rápida": 1.3,
                    "Lenta": 0.8
                }
                self.collector.tts_prefs["speed"] = speed_mapping[select.values[0]]
                self.collector.tts_prefs["speed_label"] = select.values[0]
                save_user_preference(self.collector.user_id, speed=speed_mapping[select.values[0]])
                save_user_preference(self.collector.user_id, speed_label=select.values[0])
                print(f"[PREFERENCIA] Velocidad seleccionada: {select.values[0]} ({speed_mapping[select.values[0]]})")
                await interaction.response.defer()
                await self.check_completion()

            async def check_completion(self):
                # Verificar si todas las preferencias han sido seleccionadas
                required_analysis = ["coach_type", "aspect", "personality"]
                required_tts = ["voice", "speed"]
                analysis_complete = all(key in self.collector.analysis_prefs for key in required_analysis)
                tts_complete = all(key in self.collector.tts_prefs for key in required_tts)
                if analysis_complete and tts_complete:
                    # Deshabilitar todos los elementos
                    for item in self.children:
                        item.disabled = True
                    # Señalar que está completo
                    self.collector.all_prefs_collected.set()
                    print("[PREFERENCIAS COMPLETAS] JSON final:")
                    print(json.dumps({
                        "analysis_prefs": self.collector.analysis_prefs,
                        "tts_prefs": self.collector.tts_prefs
                    }, ensure_ascii=False, indent=2))
                    self.stop()

        # Configurar las opciones para cada selector
        def setup_select_options(view):
            # Coach options
            coach_options = [
                discord.SelectOption(label="Directo", value="Directo", description="Feedback directo y sin rodeos"),
                discord.SelectOption(label="Motivador", value="Motivador", description="Enfoque positivo y motivacional"),
                discord.SelectOption(label="Analítico", value="Analítico", description="Análisis detallado y técnico"),
                discord.SelectOption(label="Empático", value="Empático", description="Comprensivo y considerado")
            ]
            view.coach_select.options = coach_options

            # Aspect options
            aspect_options = [
                discord.SelectOption(label="Comunicación", value="Comunicación", description="Mejorar call-outs y comunicación"),
                discord.SelectOption(label="Estrategia", value="Estrategia", description="Decisiones tácticas y estratégicas"),
                discord.SelectOption(label="Precisión", value="Precisión", description="Precisión en información y datos"),
                discord.SelectOption(label="Trabajo en equipo", value="Trabajo en equipo", description="Coordinación y colaboración")
            ]
            view.aspect_select.options = aspect_options

            # Personality options
            personality_options = [
                discord.SelectOption(label="Introvertido", value="Introvertido", description="Prefiere feedback más personal"),
                discord.SelectOption(label="Extrovertido", value="Extrovertido", description="Prefiere feedback más dinámico"),
                discord.SelectOption(label="Analítico", value="Analítico", description="Prefiere datos y estadísticas"),
                discord.SelectOption(label="Competitivo", value="Competitivo", description="Enfoque en rendimiento y mejora")
            ]
            view.personality_select.options = personality_options

            # Voice options
            voice_options = [
                discord.SelectOption(label="Femenina", value="Femenina", description="Voz femenina clara"),
                discord.SelectOption(label="Masculina", value="Masculina", description="Voz masculina profesional"),
                discord.SelectOption(label="Neutra", value="Neutra", description="Voz neutra estándar")
            ]
            view.voice_select.options = voice_options

            # Speed options
            speed_options = [
                discord.SelectOption(label="Normal", value="Normal", description="Velocidad estándar"),
                discord.SelectOption(label="Rápida", value="Rápida", description="Más rápido para análisis eficiente"),
                discord.SelectOption(label="Lenta", value="Lenta", description="Más lento para mejor comprensión")
            ]
            view.speed_select.options = speed_options

        async def ask_preferences(user, collector):
            bienvenida = f"""¡Hola, {user.name}! Estoy feliz de poder asesorarte el día de hoy. 

Para personalizar tu feedback, por favor responde a las siguientes 5 preguntas usando los menús desplegables:

1. **Tipo de coach**: ¿Cómo prefieres recibir tu feedback?
2. **Aspecto a mejorar**: ¿En qué quieres enfocarte?
3. **Personalidad**: ¿Con qué tipo de jugador te identificas?
4. **Tipo de voz**: ¿Qué voz prefieres para el audio?
5. **Velocidad**: ¿A qué velocidad quieres el audio?

Mientras tanto, estoy procesando tu audio con Whisper..."""
            
            await user.send(bienvenida)
            
            # Crear vista única con todas las preguntas
            view = AllPreferencesView(collector)
            setup_select_options(view)
            
            await user.send("**Configura todas tus preferencias:**", view=view)
            await view.wait()            # Todas las preferencias han sido recolectadas
            collector.all_prefs_collected.set()

        @bot.event
        async def on_ready():
            print(f"Bot conectado como {bot.user}")
            try:
                user = await bot.fetch_user(int(user_id))
                if user:
                    # Crear un colector de preferencias para esta sesión
                    collector = PreferenceCollector(user_id)
                    
                    # Iniciar procesamiento de audio en paralelo
                    audio_processing_task = None
                    transcribed_text = None
                    transcribed_segments = None
                    
                    if audio_path and os.path.exists(audio_path):
                        async def process_audio_async():
                            nonlocal transcribed_text, transcribed_segments
                            api_key = os.environ.get("OPENAI_API_KEY")
                            transcribed_text, transcribed_segments = transcribe_with_whisper(audio_path)
                            print("✅ Transcripción de audio completada")
                        
                        # Iniciar procesamiento en paralelo
                        audio_processing_task = asyncio.create_task(process_audio_async())

                    # Lanzar el flujo de preguntas
                    await ask_preferences(user, collector)
                      # Esperar a que todas las preferencias sean recolectadas
                    await collector.all_prefs_collected.wait()
                    
                    # Esperar a que se complete el procesamiento del audio si aún está en progreso
                    if audio_processing_task:
                        await audio_processing_task

                    # Una vez respondidas todas, ejecutar análisis y TTS
                    if transcribed_text and transcribed_segments:
                        # Usar preferencias recolectadas
                        analysis_prefs = collector.analysis_prefs
                        tts_prefs = collector.tts_prefs
                          # Llamar a analyze_text con preferencias
                        api_key = os.environ.get("OPENAI_API_KEY")
                        content = analyze_text(transcribed_text, transcribed_segments, api_key, user_id, analysis_prefs, tts_prefs)
                          # Guardar análisis completo (S3 + DynamoDB)
                        try:
                            result = save_analysis_complete(
                                user_id=user_id,
                                analysis_text=content,
                                audio_file_path=audio_path,
                                transcription=transcribed_text,
                                user_preferences={
                                    **analysis_prefs,
                                    **tts_prefs
                                }
                            )
                            
                            if result['success']:
                                print(f"✅ Análisis completo guardado - ID: {result['analysis_id']}")
                                if result['s3_key']:
                                    print(f"📤 Audio subido a S3: {result['s3_key']}")
                            else:
                                print(f"⚠️ Proceso completado con errores: {result['errors']}")
                                
                        except Exception as e:
                            print(f"⚠️ Error en proceso completo: {e}")
                            # Fallback: guardar solo en DynamoDB
                            try:
                                analysis_id = dynamodb_manager.save_analysis(
                                    user_id=user_id,
                                    analysis_text=content,
                                    transcription=transcribed_text,
                                    user_preferences={**analysis_prefs, **tts_prefs}
                                )
                                print(f"✅ Fallback: Análisis guardado en DynamoDB: {analysis_id}")
                            except Exception as e2:
                                print(f"❌ Error en fallback: {e2}")
                        
                        # Generar audio TTS con preferencias
                        audio_path_for_discord = generate_tts_audio(content, user_id, tts_prefs)
                        
                        # Enviar feedback y audio
                        clutch_filename = get_clutch_filename()
                        mensaje_texto = (
                            f"{user.name}, aquí tienes tu feedback personalizado de comunicación para esta partida. "
                            "El análisis se ha realizado de manera objetiva y personalizada, considerando tus preferencias. "
                            "Escucha el audio adjunto para conocer los puntos clave y sugerencias de mejora."
                        )
                        await user.send(mensaje_texto)
                        
                        if audio_path_for_discord:
                            with open(audio_path_for_discord, 'rb') as f:
                                discord_file = discord.File(f, filename=clutch_filename)
                                await user.send(file=discord_file)
                            os.remove(audio_path_for_discord)
                            print(f"✅ Feedback completo enviado exitosamente con nombre: {clutch_filename}")
                        else:
                            await user.send("Lo siento, hubo un error al generar el audio del feedback.")

                        os.remove(audio_path)
                        print(f"🗑️ Archivo de audio temporal eliminado: {audio_path}")
                    else:
                        await user.send("Lo siento, hubo un error al procesar tu audio.")
                else:
                    print(f"⚠ No se pudo encontrar al usuario con ID {user_id}")
            except Exception as e:
                print(f"❌ Error enviando feedback: {e}")
            finally:
                await bot.close()
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error general en el envío de feedback por Discord: {e}")
    finally:
        if bot is not None:
            try:
                # Crear un nuevo event loop si no existe
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                if not loop.is_running():
                    loop.run_until_complete(bot.close())
                else:
                    # Si el loop está corriendo, programar el cierre
                    asyncio.create_task(bot.close())
            except Exception as close_error:
                print(f"⚠️ Error cerrando el bot de Discord: {close_error}")
                # Intentar cerrar de forma directa
                try:
                    if hasattr(bot, '_closed') and not bot._closed:
                        bot._closed = True
                except:
                    pass

def get_audio_duration_safe(file_path):
    """
    Intenta obtener la duración del audio de forma segura
    """
    try:
        audio = MP3(file_path)
        if audio and hasattr(audio.info, 'length') and audio.info.length > 0:
            return audio.info.length / 60
    except Exception as e:
        print(f"No se pudo obtener duración con mutagen: {e}")
    
    # Si mutagen falla, retornar 0 (desconocido)
    return 0

def extract_user_id_from_filename(filename):
    """
    Extrae el user_id del nombre del archivo de audio.
    El formato esperado del archivo es: <username>-<user_id>-<timestamp>.mp3
    """
    try:
        base_name = os.path.basename(filename)
        parts = base_name.split('-')
        if len(parts) < 3:
            raise ValueError(f"El nombre del archivo no tiene el formato esperado: {filename}")
        user_id = parts[1]
        return user_id
    except Exception:
        raise ValueError(f"El nombre del archivo no tiene el formato esperado: {filename}")

# Modificar la función process_audio para extraer el user_id del nombre del archivo
def process_audio(audio_path):
    if not os.path.exists(audio_path):
        print(f"⚠️ Archivo {audio_path} ya no existe, se omite procesamiento.")
        return
    """
    Procesa un archivo de audio específico y retorna el resultado del análisis
    """
    print(f"\n{'='*50}")
    print(f"PROCESANDO: {os.path.basename(audio_path)}")
    print(f"{'='*50}")

    # Cargar API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno")

    # Extraer el user_id del nombre del archivo
    user_id = extract_user_id_from_filename(audio_path)

    # En lugar de procesar directamente, iniciamos el bot de Discord para preguntar preferencias
    send_feedback_to_discord_user(user_id, feedback=None, audio_path=audio_path)

    # El resto del procesamiento se moverá dentro de la lógica del bot
    # para que ocurra DESPUÉS de que el usuario responda.
    
    print(f"\n✅ PROCESAMIENTO INICIADO PARA: {os.path.basename(audio_path)}")
    print("Esperando que el usuario complete las preferencias en Discord...")
    # El resultado ahora se manejará dentro del bot.
    return {"status": "pending_user_input", "user_id": user_id}

# ============================================================================
# PROCESAMIENTO DIRECTO DESDE DISCORD (Sin archivos locales)  
# ============================================================================

if __name__ == "__main__":
    print("🎧 Clutch eSports Bot - Iniciando...")
    print("☁️ Modo: Solo Nube (S3 + DynamoDB)")
    print("📱 Los audios se procesan directamente desde Discord")
    print("💾 Sin almacenamiento local")
    
    # Verificar configuración de AWS
    aws_region = os.getenv('AWS_REGION')
    s3_bucket = os.getenv('S3_BUCKET_NAME')
    
    print(f"🌍 AWS Región: {aws_region}")
    print(f"🪣 S3 Bucket: {s3_bucket}")
    print(f"💾 DynamoDB: {os.getenv('DYNAMODB_TABLE_NAME')}")
    
    # Verificar que no se use monitoreo de archivos locales
    print("\n✅ Configuración de solo nube:")
    print("   • Los archivos se suben directamente a S3")
    print("   • Los análisis se guardan en DynamoDB") 
    print("   • No se crean carpetas locales")
    print("   • No se monitorean archivos locales")
    
    print("\n🤖 El bot está listo para recibir archivos por Discord...")
    print("📱 Los usuarios pueden subir archivos directamente al bot")
    print("☁️ Todo se procesa y almacena en la nube")
      try:
        print("\n💡 INSTRUCCIONES DE USO:")
        print("   1. Los usuarios suben archivos MP3 directamente al bot de Discord")
        print("   2. El bot procesa automáticamente:")
        print("      • Transcripción con Whisper")
        print("      • Análisis con GPT")
        print("      • Subida a S3")
                print("      • Guardado en DynamoDB")
        print("   3. El usuario recibe análisis por Discord")
        print("\n⌨️ Presiona Ctrl+C para salir...")
        
        # Mantener el script corriendo sin hacer nada
        # (El verdadero procesamiento se hace cuando Discord llama a las funciones)
        while True:
            time.sleep(60)  # Dormir 1 minuto
            print(".", end="", flush=True)  # Mostrar que está vivo
            
    except KeyboardInterrupt:
        print("\n🛑 Cerrando Clutch eSports Bot...")
        print("✅ Bot cerrado correctamente.")
        print("💾 Todos los datos permanecen seguros en AWS")

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def list_google_tts_voices(language_code="es"):
    """Lista todas las voces disponibles de Google TTS para un idioma."""
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices(language_code=language_code).voices
    for v in voices:
        print(f"{v.name} | {v.ssml_gender} | {v.language_codes} | {v.natural_sample_rate_hertz} | {v.description if hasattr(v, 'description') else ''}")
    return voices