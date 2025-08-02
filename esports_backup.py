import os
import json
import requests
import time
from dotenv import load_dotenv
import mutagen  # Add this library to read audio metadata
from mutagen.mp3 import MP3, HeaderNotFoundError
from firebase_config import upload_to_firebase, save_to_firestore
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import random
import discord
import asyncio
from discord.ext import commands
from discord import ui

# Cargar variables de entorno desde .env al inicio del script
load_dotenv()

# Configuración de voz TTS Google Cloud
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "es-ES-Chirp3-HD-Alnilam")  # Cambia aquí el nombre de la voz

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
{extra_instructions}
Analiza ÚNICAMENTE el CONTENIDO de la comunicación (qué dijo, no cómo lo dijo):
📊 CRITERIOS DE EVALUACIÓN:
• PRECISIÓN INFORMATIVA: ¿La información fue específica y útil? (ubicaciones, números, estados)
• EFICIENCIA COMUNICATIVA: ¿Transmitió datos clave sin palabras innecesarias?
• REDUNDANCIA: ¿Repitió información ya comunicada sin justificación táctica?
• VALOR ESTRATÉGICO: ¿Sus call-outs ayudaron realmente a la toma de decisiones del equipo?
🎯 INSTRUCCIONES:
- Analiza solo el CONTENIDO textual, no interpretes emociones o tono
- Evalúa la calidad informativa usando el contexto de terminología eSports
- Cita ejemplos específicos de la transcripción con timestamps
- Da feedback constructivo sobre QUÉ comunicar mejor
- Respuesta en español chileno, UN párrafo corrido
- Solo análisis del contenido, sin saludos
TRANSCRIPCIÓN COMPLETA:
{text}
DESGLOSE TEMPORAL:
{transcript_with_timestamps}"""
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Eres un analista experto en comunicación de eSports. Te especializas en evaluar el CONTENIDO informativo de los call-outs, no el tono emocional. Das feedback constructivo sobre la calidad y utilidad de la información comunicada."},
            {"role": "user", "content": prompt}
        ],        "temperature": 0.3,
        "max_tokens": 600,
        "response_format": { "type": "text" }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        
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
    voice_name = prefs.get("voice", GOOGLE_TTS_VOICE)
    speed = prefs.get("speed", 1.0)
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

def save_user_preference(user_id, coach_type=None, aspect=None, personality=None, voice=None, speed=None):
    """
    Guarda la preferencia del usuario en un archivo JSON local.
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
                self.collector.tts_prefs["voice"] = "es-ES-Chirp3-HD-Alnilam"
                save_user_preference(self.collector.user_id, voice="es-ES-Chirp3-HD-Alnilam")
                await interaction.response.send_message("✅ Voz femenina seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Masculina", style=discord.ButtonStyle.success)
            async def masculina(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["voice"] = "es-ES-Wavenet-B"
                save_user_preference(self.collector.user_id, voice="es-ES-Wavenet-B")
                await interaction.response.send_message("✅ Voz masculina seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Neutra", style=discord.ButtonStyle.secondary)
            async def neutra(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["voice"] = "es-ES-Standard-A"
                save_user_preference(self.collector.user_id, voice="es-ES-Standard-A")
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
                save_user_preference(self.collector.user_id, speed=1.0)
                await interaction.response.send_message("✅ Velocidad normal seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

            @ui.button(label="Rápida", style=discord.ButtonStyle.success)
            async def rapida(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["speed"] = 1.3
                save_user_preference(self.collector.user_id, speed=1.3)
                await interaction.response.send_message("✅ Velocidad rápida seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()            @ui.button(label="Lenta", style=discord.ButtonStyle.secondary)
            async def lenta(self, interaction: discord.Interaction, button: ui.Button):
                self.collector.tts_prefs["speed"] = 0.8
                save_user_preference(self.collector.user_id, speed=0.8)
                await interaction.response.send_message("✅ Velocidad lenta seleccionada", ephemeral=True)
                await self.disable_all_items(interaction)
                self.stop()

        class AllPreferencesView(ui.View):
            def __init__(self, collector):
                super().__init__(timeout=300)  # Más tiempo para responder todo
                self.collector = collector            # Tipo de Coach
            @ui.select(placeholder="1. ¿Qué tipo de coach prefieres?", min_values=1, max_values=1, row=0)
            async def coach_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["coach_type"] = select.values[0]
                save_user_preference(self.collector.user_id, coach_type=select.values[0])
                await interaction.response.defer()
                await self.check_completion()

            # Aspecto a mejorar
            @ui.select(placeholder="2. ¿Qué aspecto te gustaría mejorar?", min_values=1, max_values=1, row=1)
            async def aspect_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["aspect"] = select.values[0]
                save_user_preference(self.collector.user_id, aspect=select.values[0])
                await interaction.response.defer()
                await self.check_completion()

            # Personalidad
            @ui.select(placeholder="3. ¿Con qué personalidad te identificas?", min_values=1, max_values=1, row=2)
            async def personality_select(self, interaction: discord.Interaction, select: ui.Select):
                self.collector.analysis_prefs["personality"] = select.values[0]
                save_user_preference(self.collector.user_id, personality=select.values[0])
                await interaction.response.defer()
                await self.check_completion()

            # Tipo de voz
            @ui.select(placeholder="4. ¿Qué tipo de voz prefieres?", min_values=1, max_values=1, row=3)
            async def voice_select(self, interaction: discord.Interaction, select: ui.Select):
                voice_mapping = {
                    "Femenina": "es-ES-Chirp3-HD-Alnilam",
                    "Masculina": "es-ES-Wavenet-B",
                    "Neutra": "es-ES-Standard-A"
                }
                self.collector.tts_prefs["voice"] = voice_mapping[select.values[0]]
                save_user_preference(self.collector.user_id, voice=voice_mapping[select.values[0]])
                await interaction.response.defer()
                await self.check_completion()            # Velocidad
            @ui.select(placeholder="5. ¿A qué velocidad prefieres el audio?", min_values=1, max_values=1, row=4)
            async def speed_select(self, interaction: discord.Interaction, select: ui.Select):
                speed_mapping = {
                    "Normal": 1.0,
                    "Rápida": 1.3,
                    "Lenta": 0.8
                }
                self.collector.tts_prefs["speed"] = speed_mapping[select.values[0]]
                save_user_preference(self.collector.user_id, speed=speed_mapping[select.values[0]])
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
                        
                        # Generar audio TTS con preferencias
                        audio_path_for_discord = generate_tts_audio(content, user_id, tts_prefs)
                        
                        # Enviar feedback y audio
                        motivational_filename = get_motivational_filename()
                        mensaje_texto = (
                            f"{user.name}, aquí tienes tu feedback personalizado de comunicación para esta partida. "
                            "El análisis se ha realizado de manera objetiva y profesional, considerando tu desempeño en el equipo. "
                            "Escucha el audio adjunto para conocer los puntos clave y sugerencias de mejora."
                        )
                        await user.send(mensaje_texto)
                        
                        if audio_path_for_discord:
                            with open(audio_path_for_discord, 'rb') as f:
                                discord_file = discord.File(f, filename=motivational_filename)
                                await user.send(file=discord_file)
                            os.remove(audio_path_for_discord)
                            print(f"✅ Feedback completo enviado exitosamente con nombre: {motivational_filename}")
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
                await bot.close()        bot.run(DISCORD_TOKEN)
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
    # Por lo tanto, el código que estaba aquí (transcripción, análisis) ya no es necesario.
    
    print(f"\n✅ PROCESAMIENTO INICIADO PARA: {os.path.basename(audio_path)}")
    print("Esperando que el usuario complete las preferencias en Discord...")
    # El resultado ahora se manejará dentro del bot.
    return {"status": "pending_user_input", "user_id": user_id}

class RecordingHandler(FileSystemEventHandler):
    def __init__(self):
        self.processing_files = set()  # Track files being processed
    
    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.mp3'):
            file_path = event.src_path
            if file_path in self.processing_files:
                print(f"Archivo ya en procesamiento: {file_path}")
                return
                
            print(f"\n🎵 Nuevo archivo MP3 detectado: {os.path.basename(file_path)}")
            self.processing_files.add(file_path)
            
            try:
                process_audio(file_path)
            except Exception as e:
                print(f"❌ Error procesando {os.path.basename(file_path)}: {e}")
            finally:
                self.processing_files.discard(file_path)

if __name__ == "__main__":
    print("🎧 Audio Processor para eSports - Iniciando...")
    
    recordings_dir = os.path.join(os.getcwd(), 'recordings')
    if not os.path.exists(recordings_dir):
        print(f"📁 Creando directorio de grabaciones: {recordings_dir}")
        os.makedirs(recordings_dir)

    event_handler = RecordingHandler()
    observer = Observer()
    observer.schedule(event_handler, path=recordings_dir, recursive=False)
    observer.start()

    print(f"👀 Monitoreando archivos MP3 en: {recordings_dir}")
    print("Presiona Ctrl+C para detener...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo monitor...")
        observer.stop()
    observer.join()
    print("✅ Monitor detenido correctamente.")

def list_google_tts_voices(language_code="es"):
    from google.cloud import texttospeech
    client = texttospeech.TextToSpeechClient()
    voices = client.list_voices(language_code=language_code).voices
    for v in voices:
        print(f"{v.name} | {v.ssml_gender} | {v.language_codes} | {v.natural_sample_rate_hertz} | {v.description if hasattr(v, 'description') else ''}")
    return voices

# Llama a esta función manualmente para ver las voces disponibles
# list_google_tts_voices("es")