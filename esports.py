import os
import json
import requests
import time
from dotenv import load_dotenv
import discord
from mutagen.mp3 import MP3, HeaderNotFoundError
from dynamodb_config import save_analysis_complete
import sys
import random
import asyncio
from discord.ext import commands
from discord import ui
import tempfile
import io
from datetime import datetime

# Cargar variables de entorno
load_dotenv()

# Configuración del bot Discord
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Configuración TTS
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "es-ES-Standard-A")

# Configuración Discord Bot
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True  # Necesario para grabación de voz
intents.guilds = True        # Necesario para información de servidores
intents.members = True       # Necesario para información de miembros
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================================
# FUNCIONES TTS Y ANÁLISIS (CLOUD-ONLY)
# ============================================================================

def get_google_tts_voices_by_gender(language_code="es-ES"):
    """Devuelve voces de Google TTS agrupadas por género."""
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
    """Selecciona voz de Google TTS según género preferido."""
    voices_by_gender = get_google_tts_voices_by_gender(language_code)
    voices = voices_by_gender.get(preferred_gender, [])
    if voices:
        return voices[0]["name"]
    return GOOGLE_TTS_VOICE

def get_clutch_filename():
    """Genera nombre de archivo motivador para Discord."""
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

def transcribe_with_whisper_from_bytes(audio_data, filename):
    """Transcribe audio desde bytes usando OpenAI Whisper."""
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    files = {
        'file': (filename, audio_data, 'audio/mpeg'),
        'model': (None, 'whisper-1'),
        'language': (None, 'es'),
        'response_format': (None, 'verbose_json'),
        'temperature': (None, '0.2')
    }
    
    try:
        print("🎧 Transcribiendo audio con Whisper...")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        
        print("✅ Transcripción completada")
        return result['text'], result.get('segments', [])
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en transcripción Whisper: {e}")
        if 'response' in locals() and response is not None:
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        raise

def analyze_text(text, segments, user_id, analysis_prefs, tts_prefs):
    """Analiza texto transcrito usando GPT."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    transcript_with_timestamps = "\n".join([
        f"{i:03d} - [{seg.get('start', 0):.3f}:{seg.get('end', 0):.3f}] {seg.get('text', '')}"
        for i, seg in enumerate(segments, 1)
    ])
    
    # Obtener preferencias del usuario
    coach_type = analysis_prefs.get("coach_type", "Directo")
    aspect = analysis_prefs.get("aspect", "Comunicación")
    personality = analysis_prefs.get("personality", "Introvertido")
    
    esports_context = """
CONTEXTO DE TERMINOLOGÍA ESPORTS/CALL OF DUTY:
• POSICIONES: "A", "B", "C" (sitios de bomba), "spawn", "mid", "largo", "corto", "heaven", "hell"
• DIRECCIONES: "arriba", "abajo", "derecha", "izquierda", "flanqueando", "rotando", "empujando"
• ENEMIGOS: "uno", "dos", "tres", "lit", "tocado", "one shot", "absolute", "cracked", "weak", "full"
• ACCIONES: "push", "hold", "peek", "trade", "bait", "flank", "wrap", "split", "rotar", "pushear"
• OBJETIVOS: "bomba", "objetivo", "punto de control", "hardpoint", "zona de captura", "defusa"
• CHILENOS: "weón", "dale", "cabros", "buena", "nice", "mierda", "ctm", "ql", "puta la wea"
• ESTRATEGIA: "flank", "push", "hold", "rotate", "trade", "bait", "split", "wrap", "crossfire"
"""
    
    prompt = f"""{esports_context}
Analiza la comunicación de la siguiente transcripción de eSports. Evalúa únicamente el contenido textual.

Criterios de evaluación:
- Precisión: ¿Se entregó información específica y útil?
- Eficiencia: ¿Se comunicaron datos clave sin palabras de relleno?
- Redundancia: ¿Se repitió información sin justificación táctica?
- Valor estratégico: ¿Los call-outs ayudaron a la toma de decisiones?

Instrucciones:
- Cita ejemplos específicos de la transcripción
- Proporciona feedback constructivo 
- Responde en un párrafo en español chileno
- Escribe en primera persona dirigiéndote al jugador

TRANSCRIPCIÓN: {text}
DESGLOSE TEMPORAL: {transcript_with_timestamps}"""

    system_prompt = (
        f"Eres un entrenador de esports {coach_type.lower()}. "
        f"El jugador quiere mejorar en {aspect} y tiene personalidad {personality}. "
        "Te especializas en evaluar comunicación de call-outs."
    )
    
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 500,
        "response_format": {"type": "text"}
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        print("✅ Análisis GPT completado")
        return content
    except Exception as e:
        print(f"❌ Error en análisis GPT: {e}")
        return "Hubo un error al analizar la comunicación. Por favor, intenta de nuevo."

def generate_tts_audio_to_bytes(text_to_speak, user_id, prefs):
    """Genera audio TTS y retorna como bytes (sin guardar archivos)."""
    from google.cloud import texttospeech
    
    # Obtener preferencias de voz
    voice_name = prefs.get("voice", GOOGLE_TTS_VOICE)
    speed = prefs.get("speed", 1.0)
    speed_label = prefs.get("speed_label", "Normal")
    
    # Ajuste de velocidad
    if speed_label == "Lenta":
        speed = 0.8
    elif speed_label == "Rápida":
        speed = 1.3
    elif speed_label == "Normal":
        speed = 1.0
    
    print(f"🎤 Generando TTS: voz={voice_name}, velocidad={speed}")
    
    try:
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
        
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        print("✅ Audio TTS generado exitosamente")
        return response.audio_content
        
    except Exception as e:
        print(f"❌ Error generando TTS: {e}")
        return None

# ============================================================================
# GESTIÓN DE PREFERENCIAS (CLOUD-ONLY)
# ============================================================================

def save_user_preference(user_id, **kwargs):
    """Guarda preferencias del usuario en archivo JSON."""
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
    
    # Actualizar con kwargs
    prefs[str(user_id)].update(kwargs)
    
    with open(pref_file, "w", encoding="utf-8") as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2)

def get_user_preference(user_id):
    """Obtiene preferencias del usuario."""
    pref_file = "user_preferences.json"
    if os.path.exists(pref_file):
        with open(pref_file, "r", encoding="utf-8") as f:
            try:
                prefs = json.load(f)
                return prefs.get(str(user_id), {})
            except Exception:
                return {}
    return {}

# ============================================================================
# CLASES DE INTERFAZ DISCORD
# ============================================================================

class PreferenceCollector:
    def __init__(self, user_id):
        self.user_id = user_id
        self.all_prefs_collected = asyncio.Event()
        self.analysis_prefs = {}
        self.tts_prefs = {}

class AllPreferencesView(ui.View):
    def __init__(self, collector):
        super().__init__(timeout=300)
        self.collector = collector
        self.setup_select_options()

    def setup_select_options(self):
        """Configura todas las opciones de los selectores."""
        # Coach options
        coach_options = [
            discord.SelectOption(label="Directo", value="Directo", description="Feedback directo y sin rodeos"),
            discord.SelectOption(label="Motivador", value="Motivador", description="Enfoque positivo y motivacional"),
            discord.SelectOption(label="Analítico", value="Analítico", description="Análisis detallado y técnico"),
            discord.SelectOption(label="Empático", value="Empático", description="Comprensivo y considerado")
        ]
        self.coach_select.options = coach_options

        # Aspect options
        aspect_options = [
            discord.SelectOption(label="Comunicación", value="Comunicación", description="Mejorar call-outs"),
            discord.SelectOption(label="Estrategia", value="Estrategia", description="Decisiones tácticas"),
            discord.SelectOption(label="Precisión", value="Precisión", description="Información precisa"),
            discord.SelectOption(label="Trabajo en equipo", value="Trabajo en equipo", description="Coordinación")
        ]
        self.aspect_select.options = aspect_options

        # Personality options
        personality_options = [
            discord.SelectOption(label="Introvertido", value="Introvertido", description="Feedback personal"),
            discord.SelectOption(label="Extrovertido", value="Extrovertido", description="Feedback dinámico"),
            discord.SelectOption(label="Analítico", value="Analítico", description="Datos y estadísticas"),
            discord.SelectOption(label="Competitivo", value="Competitivo", description="Enfoque en rendimiento")
        ]
        self.personality_select.options = personality_options

        # Voice options
        voice_options = [
            discord.SelectOption(label="Femenina", value="Femenina", description="Voz femenina clara"),
            discord.SelectOption(label="Masculina", value="Masculina", description="Voz masculina profesional"),
            discord.SelectOption(label="Neutra", value="Neutra", description="Voz neutra estándar")
        ]
        self.voice_select.options = voice_options

        # Speed options
        speed_options = [
            discord.SelectOption(label="Normal", value="Normal", description="Velocidad estándar"),
            discord.SelectOption(label="Rápida", value="Rápida", description="Más rápido"),
            discord.SelectOption(label="Lenta", value="Lenta", description="Más lento")
        ]
        self.speed_select.options = speed_options

    @ui.select(placeholder="1. ¿Qué tipo de coach prefieres?", min_values=1, max_values=1, row=0)
    async def coach_select(self, interaction: discord.Interaction, select: ui.Select):
        self.collector.analysis_prefs["coach_type"] = select.values[0]
        save_user_preference(self.collector.user_id, coach_type=select.values[0])
        await interaction.response.defer()
        await self.check_completion()

    @ui.select(placeholder="2. ¿Qué aspecto te gustaría mejorar?", min_values=1, max_values=1, row=1)
    async def aspect_select(self, interaction: discord.Interaction, select: ui.Select):
        self.collector.analysis_prefs["aspect"] = select.values[0]
        save_user_preference(self.collector.user_id, aspect=select.values[0])
        await interaction.response.defer()
        await self.check_completion()

    @ui.select(placeholder="3. ¿Con qué personalidad te identificas?", min_values=1, max_values=1, row=2)
    async def personality_select(self, interaction: discord.Interaction, select: ui.Select):
        self.collector.analysis_prefs["personality"] = select.values[0]
        save_user_preference(self.collector.user_id, personality=select.values[0])
        await interaction.response.defer()
        await self.check_completion()

    @ui.select(placeholder="4. ¿Qué tipo de voz prefieres?", min_values=1, max_values=1, row=3)
    async def voice_select(self, interaction: discord.Interaction, select: ui.Select):
        voice_map = {
            "Femenina": "es-ES-Chirp3-HD-Achernar",
            "Masculina": "es-ES-Chirp3-HD-Charon",
            "Neutra": "es-ES-Standard-A"
        }
        voice_label = select.values[0]
        voice_name = voice_map[voice_label]
        self.collector.tts_prefs["voice"] = voice_name
        self.collector.tts_prefs["voice_label"] = voice_label
        save_user_preference(self.collector.user_id, voice=voice_name, voice_label=voice_label)
        await interaction.response.defer()
        await self.check_completion()

    @ui.select(placeholder="5. ¿A qué velocidad prefieres el audio?", min_values=1, max_values=1, row=4)
    async def speed_select(self, interaction: discord.Interaction, select: ui.Select):
        speed_mapping = {"Normal": 1.0, "Rápida": 1.3, "Lenta": 0.8}
        self.collector.tts_prefs["speed"] = speed_mapping[select.values[0]]
        self.collector.tts_prefs["speed_label"] = select.values[0]
        save_user_preference(self.collector.user_id, speed=speed_mapping[select.values[0]], speed_label=select.values[0])
        await interaction.response.defer()
        await self.check_completion()

    async def check_completion(self):
        """Verifica si todas las preferencias han sido seleccionadas."""
        required_analysis = ["coach_type", "aspect", "personality"]
        required_tts = ["voice", "speed"]
        
        analysis_complete = all(key in self.collector.analysis_prefs for key in required_analysis)
        tts_complete = all(key in self.collector.tts_prefs for key in required_tts)
        
        if analysis_complete and tts_complete:
            for item in self.children:
                item.disabled = True
            self.collector.all_prefs_collected.set()
            print("✅ Todas las preferencias recolectadas")
            self.stop()

# ============================================================================
# GRABACIÓN DE VOZ (CLOUD-ONLY CON FALLBACK)
# ============================================================================

active_recordings = {}

class VoiceRecorder:
    def __init__(self, user_id, guild_id, voice_client):
        self.user_id = user_id
        self.guild_id = guild_id
        self.voice_client = voice_client
        self.is_recording = False
        self.audio_data = b''
        self.start_time = time.time()
        
    def write_audio(self, data):
        """Escribe datos de audio al buffer."""
        if self.is_recording:
            self.audio_data += data
            
    def stop_recording(self):
        """Detiene la grabación y retorna datos de audio."""
        self.is_recording = False
        return self.audio_data
        
    def get_duration(self):
        """Retorna duración de la grabación en segundos."""
        return time.time() - self.start_time if self.is_recording else 0

# ============================================================================
# COMANDOS DEL BOT DISCORD
# ============================================================================

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} está conectado y listo!")
    print("📁 Modo: Solo Nube (S3 + DynamoDB)")
    print("🎧 Comandos: !record → grabar → !stop → análisis automático")
    print(f"🔗 Conectado a {len(bot.guilds)} servidor(es)")
    
    # Verificar permisos en todos los servidores
    for guild in bot.guilds:
        bot_member = guild.me
        if not bot_member.guild_permissions.connect or not bot_member.guild_permissions.speak:
            print(f"⚠️ Permisos faltantes en {guild.name}")

@bot.event
async def on_voice_state_update(member, before, after):
    """Maneja cambios en el estado de voz para detectar desconexiones."""
    if member == bot.user:
        if before.channel and not after.channel:
            # Bot fue desconectado
            print(f"🔌 Bot desconectado del canal de voz en {member.guild.name}")
            
            # NO INTENTAR RECONECTAR AUTOMÁTICAMENTE
            # Limpiar grabaciones activas de este servidor
            guild_id = str(member.guild.id)
            to_remove = []
            for key, recorder in active_recordings.items():
                if recorder.guild_id == guild_id:
                    to_remove.append(key)
            
            for key in to_remove:
                del active_recordings[key]
                print(f"🧹 Limpiada grabación activa: {key}")
                
            # Informar a los usuarios que tenían grabaciones activas
            try:
                guild = member.guild
                for key in to_remove:
                    user_id = key
                    user = guild.get_member(int(user_id))
                    if user:
                        try:
                            await user.send("🔌 **Sesión de grabación interrumpida**\n"
                                           "💡 **Para continuar**: Usa `!record` nuevamente\n"
                                           "🎯 **Alternativa**: Graba externamente y sube el archivo")
                        except:
                            pass  # Ignorar si no se puede enviar DM
            except Exception as e:
                print(f"⚠️ Error notificando usuarios: {e}")

@bot.event
async def on_error(event, *args, **kwargs):
    """Maneja errores generales del bot sin causar loops."""
    error_msg = f"❌ Error en evento {event}"
    print(error_msg)
    
    # Log detallado pero no imprimir args para evitar spam
    if len(args) > 0:
        print(f"📝 Tipo de error: {type(args[0]).__name__}")
    
    # NO hacer nada más para evitar loops de reconexión

@bot.event
async def on_command_error(ctx, error):
    """Maneja errores de comandos."""
    if isinstance(error, commands.CommandNotFound):
        return  # Ignorar comandos no encontrados
    
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para usar este comando.")
        return
    
    if isinstance(error, commands.BotMissingPermissions):
        missing_perms = ', '.join(error.missing_permissions)
        await ctx.send(f"❌ El bot necesita los siguientes permisos: {missing_perms}")
        return
    
    # Error de conexión de voz
    if "ConnectionClosed" in str(error) or "4006" in str(error):
        await ctx.send("❌ **Error de conexión de voz**\n"
                      "💡 **Posibles soluciones**:\n"
                      "• Usa `!permisos` para verificar permisos\n"
                      "• Verifica que el bot tenga rol con permisos de voz\n"
                      "• Intenta `!test_conexion` para diagnosticar")
        return
    
    print(f"❌ Error en comando {ctx.command}: {error}")
    await ctx.send(f"❌ Error inesperado: {str(error)[:100]}...")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    # Verificar si el mensaje tiene archivos adjuntos
    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.lower().endswith(('.mp3', '.wav', '.ogg', '.m4a')):
                await process_audio_attachment(message, attachment)
    
    await bot.process_commands(message)

@bot.command(name='record')
async def start_recording(ctx):
    """Inicia la grabación de audio en vivo desde Discord."""
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id)
    
    # Verificar permisos del bot
    if not ctx.guild.me.guild_permissions.connect:
        await ctx.send("❌ **Error de permisos**: El bot necesita permiso para **conectarse** a canales de voz.")
        return
    
    if not ctx.guild.me.guild_permissions.speak:
        await ctx.send("❌ **Error de permisos**: El bot necesita permiso para **hablar** en canales de voz.")
        return
    
    # Verificar si el usuario está en un canal de voz
    if not ctx.author.voice:
        await ctx.send("❌ Debes estar en un canal de voz para usar este comando.")
        return
    
    voice_channel = ctx.author.voice.channel
    
    # Verificar permisos en el canal específico
    bot_member = ctx.guild.me
    channel_permissions = voice_channel.permissions_for(bot_member)
    
    if not channel_permissions.connect:
        await ctx.send(f"❌ **Sin permisos**: No puedo conectarme a {voice_channel.name}. "
                      f"Verifica que el bot tenga permisos de **Conectar** en ese canal.")
        return
    
    if not channel_permissions.speak:
        await ctx.send(f"❌ **Sin permisos**: No puedo hablar en {voice_channel.name}. "
                      f"Verifica que el bot tenga permisos de **Hablar** en ese canal.")
        return
    
    # Verificar si ya hay una grabación activa para este usuario
    recording_key = f"{user_id}"
    if recording_key in active_recordings:
        await ctx.send("⚠️ Ya tienes una grabación activa. Usa `!stop` para terminarla.")
        return
      # Verificar si el bot ya está conectado a otro canal en este servidor
    if ctx.voice_client:
        if ctx.voice_client.channel.id != voice_channel.id:
            await ctx.send(f"⚠️ Ya estoy conectado a {ctx.voice_client.channel.name}. "
                          f"Usa `!stop` primero o únetelo a ese canal.")
            return
        else:
            # Ya estamos en el canal correcto
            voice_client = ctx.voice_client
    else:
        try:
            # Intentar conectar al canal de voz SIN RECONEXIÓN AUTOMÁTICA
            await ctx.send(f"🔄 Conectando a {voice_channel.name}...")
            voice_client = await voice_channel.connect(timeout=15.0, reconnect=False)
            await ctx.send(f"✅ Conectado exitosamente a {voice_channel.name}")
            
        except discord.errors.ClientException as e:
            await ctx.send(f"❌ **Error de cliente Discord**: {str(e)}\n"
                          f"💡 **Solución**: Usa `!permisos` para verificar configuración")
            return
        except discord.errors.ConnectionClosed as e:
            if e.code == 4006:
                await ctx.send(f"❌ **Error 4006 - Permisos insuficientes**\n"
                              f"🔧 **Soluciones**:\n"
                              f"• Usa `!permisos` para verificar permisos\n"
                              f"• Pide a un admin usar `!fijar_permisos`\n"
                              f"• Como alternativa: usa modo manual\n"
                              f"💡 **Modo manual**: `!record` → graba externamente → `!stop` → sube archivo")
            else:
                await ctx.send(f"❌ **Conexión cerrada por Discord**: Error {e.code}\n"
                              f"💡 **Solución**: Verifica permisos con `!diagnostico`")
            return
        except asyncio.TimeoutError:
            await ctx.send("❌ **Timeout**: No pude conectarme al canal en 15 segundos.\n"
                          f"💡 **Soluciones**:\n"
                          f"• Verifica tu conexión a internet\n"
                          f"• Usa `!test_conexion` para diagnosticar\n"
                          f"• Intenta de nuevo en unos momentos")
            return
        except Exception as e:
            await ctx.send(f"❌ **Error inesperado**: {str(e)}\n"
                          f"💡 Usa `!diagnostico` para más información")
            print(f"Error detallado conectando: {type(e).__name__}: {e}")
            return
    
    try:
        # Crear el recorder
        recorder = VoiceRecorder(user_id, guild_id, voice_client)
        recorder.is_recording = True
          # Configurar sesión de grabación manual (sin discord.sinks)
        try:
            # Activar el recorder para sesión manual
            active_recordings[recording_key] = recorder
            
            await ctx.send(f"🎙️ **¡Sesión de grabación iniciada!** en {voice_channel.name}\n"
                          f"📝 **Modo manual activo** (grabación externa requerida)\n"
                          f"🎯 **Instrucciones**:\n"
                          f"• Graba tu audio externamente (OBS, Audacity, etc.)\n"
                          f"• Usa `!stop` y luego **sube tu archivo de audio**\n"
                          f"• El análisis será completamente automático\n"
                          f"💡 **Formatos**: MP3, WAV, OGG, M4A")
            
            print(f"🎧 Sesión manual establecida para {user_id} en {voice_channel.name}")
            
        except Exception as e:
            await ctx.send(f"❌ Error configurando sesión: {e}")
            print(f"❌ Error configurando sesión: {e}")
            await voice_client.disconnect()
            return
        
    except Exception as e:
        print(f"❌ Error configurando grabación: {e}")
        await ctx.send(f"❌ Error configurando grabación: {str(e)}")
        
        # Limpiar si algo salió mal
        if recording_key in active_recordings:
            del active_recordings[recording_key]

@bot.command(name='stop')
async def stop_recording(ctx):
    """Detiene la grabación y procesa el audio."""
    user_id = str(ctx.author.id)
    recording_key = f"{user_id}"
    
    # Verificar si hay una grabación activa
    if recording_key not in active_recordings:
        await ctx.send("❌ No tienes ninguna sesión activa. Usa `!record` para iniciar.")
        return
    
    try:
        # Obtener el recorder
        recorder = active_recordings[recording_key]
        
        # Detener grabación
        audio_data = recorder.stop_recording()
        duration = recorder.get_duration()
        
        # Desconectar del canal de voz
        if recorder.voice_client:
            try:
                recorder.voice_client.stop_recording()
            except:
                pass  # Puede fallar si no se estaba grabando
            await recorder.voice_client.disconnect()
        
        # Limpiar
        del active_recordings[recording_key]
          # Procesar audio automáticamente si se capturó (modo manual)
        if audio_data and len(audio_data) > 1024:  # Más de 1KB indica audio real
            await ctx.send(f"🎧 **¡Audio capturado automáticamente!**\n"
                          f"⏱️ **Duración**: {duration:.1f} segundos\n"
                          f"📊 **Tamaño**: {len(audio_data)} bytes\n"
                          f"⚡ Procesando automáticamente...")
            # Procesar audio en memoria (sin guardar en recordings/)
            await process_captured_audio(ctx, audio_data, f"recording_{user_id}_{int(time.time())}.wav")
        else:
            # No hay audio capturado - modo manual
            await ctx.send(f"🎧 **Sesión terminada** - Modo manual\n\n"
                          f"📤 **SUBE TU ARCHIVO**: Arrastra tu grabación MP3/WAV aquí\n"
                          f"🎯 El bot procesará automáticamente tu comunicación\n"
                          f"💡 Graba tu micrófono durante las partidas para mejor análisis")
        
        print(f"✅ Sesión terminada para {user_id} - Audio: {len(audio_data) if audio_data else 0} bytes")
        
    except Exception as e:
        print(f"❌ Error terminando sesión: {e}")
        await ctx.send(f"❌ Error: {str(e)}")
        if recording_key in active_recordings:
            del active_recordings[recording_key]

async def process_captured_audio(ctx, audio_data, filename):
    """Procesa audio capturado automáticamente (en memoria, directo a Whisper y S3)."""
    user_id = str(ctx.author.id)
    
    # Crear un objeto tipo attachment simulado
    class MockAttachment:
        def __init__(self, data, name):
            self.data = data
            self.filename = name
        async def read(self):
            return self.data
    
    mock_attachment = MockAttachment(audio_data, filename)
    await process_audio_attachment(ctx, mock_attachment)

async def process_audio_attachment(message, attachment):
    """Procesa un archivo de audio adjunto desde Discord (en memoria, sin guardar local)."""
    user_id = str(message.author.id)
    try:
        # Descargar audio a memoria
        audio_data = await attachment.read()
        await message.reply("🎧 ¡Audio recibido! Procesando tu comunicación...")
        collector = PreferenceCollector(user_id)
        existing_prefs = get_user_preference(user_id)
        if not existing_prefs:
            bienvenida = f"""¡Hola, {message.author.name}! 🎮\n\nBienvenido a **Clutch eSports Coach**. Para personalizar tu análisis, necesito conocer tus preferencias.\n\nResponde las 5 preguntas usando los menús desplegables:\n\n1. **Tipo de coach**: ¿Cómo prefieres recibir feedback?\n2. **Aspecto a mejorar**: ¿En qué quieres enfocarte?\n3. **Personalidad**: ¿Con qué tipo de jugador te identificas?\n4. **Tipo de voz**: ¿Qué voz prefieres para el audio?\n5. **Velocidad**: ¿A qué velocidad quieres el audio?\n\nMientras tanto, estoy procesando tu audio... ⚡"""
            await message.author.send(bienvenida)
            view = AllPreferencesView(collector)
            await message.author.send("**Configura tus preferencias:**", view=view)
            async def process_audio_async():
                transcribed_text, transcribed_segments = transcribe_with_whisper_from_bytes(
                    audio_data, attachment.filename
                )
                return transcribed_text, transcribed_segments
            audio_task = asyncio.create_task(process_audio_async())
            await collector.all_prefs_collected.wait()
            transcribed_text, transcribed_segments = await audio_task
            analysis_prefs = collector.analysis_prefs
            tts_prefs = collector.tts_prefs
        else:
            await message.reply("⚡ Procesando con tus preferencias guardadas...")
            transcribed_text, transcribed_segments = transcribe_with_whisper_from_bytes(
                audio_data, attachment.filename
            )
            analysis_prefs = {
                "coach_type": existing_prefs.get("coach_type", "Directo"),
                "aspect": existing_prefs.get("aspect", "Comunicación"),
                "personality": existing_prefs.get("personality", "Introvertido")
            }
            tts_prefs = {
                "voice": existing_prefs.get("voice", GOOGLE_TTS_VOICE),
                "voice_label": existing_prefs.get("voice_label", "Neutra"),
                "speed": existing_prefs.get("speed", 1.0),
                "speed_label": existing_prefs.get("speed_label", "Normal")
            }
        # Realizar análisis
        analysis_content = analyze_text(
            transcribed_text, transcribed_segments, user_id, analysis_prefs, tts_prefs
        )
        # Guardar análisis completo (S3 + DynamoDB) usando audio en memoria
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_audio_path = temp_file.name
        try:
            result = save_analysis_complete(
                user_id=user_id,
                analysis_text=analysis_content,
                audio_file_path=temp_audio_path,
                transcription=transcribed_text,
                user_preferences={**analysis_prefs, **tts_prefs}
            )
            if result['success']:
                print(f"✅ Análisis guardado - ID: {result['analysis_id']}")
                if result['s3_key']:
                    print(f"📤 Audio subido a S3: {result['s3_key']}")
        except Exception as e:
            print(f"⚠️ Error guardando: {e}")
        finally:
            os.unlink(temp_audio_path)
        # Generar audio TTS
        tts_audio_bytes = generate_tts_audio_to_bytes(analysis_content, user_id, tts_prefs)
        feedback_filename = get_clutch_filename()
        mensaje_texto = (
            f"🎯 **{message.author.name}**, aquí tienes tu análisis personalizado.\n\n"
            f"📊 **Transcripción procesada:** {len(transcribed_text)} caracteres\n"
            f"🎤 **Coach:** {analysis_prefs.get('coach_type', 'Directo')}\n"
            f"🎯 **Enfoque:** {analysis_prefs.get('aspect', 'Comunicación')}\n\n"
            f"🔊 Escucha el audio adjunto para el análisis completo."
        )
        await message.author.send(mensaje_texto)
        if tts_audio_bytes:
            discord_file = discord.File(
                io.BytesIO(tts_audio_bytes), 
                filename=feedback_filename
            )
            await message.author.send(file=discord_file)
            print(f"✅ Feedback enviado: {feedback_filename}")
        else:
            await message.author.send("❌ Error generando audio del feedback.")
    except Exception as e:
        print(f"❌ Error procesando audio: {e}")
        await message.reply(f"❌ Hubo un error procesando tu audio: {str(e)}")

@bot.command(name='permisos')
async def check_permissions(ctx):
    """Verifica los permisos del bot para grabación de voz."""
    if not ctx.author.voice:
        await ctx.send("❌ Debes estar en un canal de voz para verificar permisos.")
        return
    
    voice_channel = ctx.author.voice.channel
    bot_member = ctx.guild.me
    
    # Permisos generales del servidor
    guild_perms = bot_member.guild_permissions
    
    # Permisos específicos del canal
    channel_perms = voice_channel.permissions_for(bot_member)
    
    # Verificar permisos requeridos
    required_guild_perms = [
        ("connect", "Conectar a canales de voz", guild_perms.connect),
        ("speak", "Hablar en canales de voz", guild_perms.speak),
        ("use_voice_activation", "Usar activación por voz", guild_perms.use_voice_activation),
    ]
    
    required_channel_perms = [
        ("connect", "Conectar a este canal", channel_perms.connect),
        ("speak", "Hablar en este canal", channel_perms.speak),
        ("view_channel", "Ver este canal", channel_perms.view_channel),
    ]
    
    embed = discord.Embed(
        title="🔍 Verificación de Permisos de Grabación",
        description=f"Verificando permisos para **{voice_channel.name}**",
        color=discord.Color.blue()
    )
    
    # Permisos del servidor
    guild_status = ""
    for perm, desc, has_perm in required_guild_perms:
        status = "✅" if has_perm else "❌"
        guild_status += f"{status} {desc}\n"
    
    embed.add_field(
        name="📋 Permisos del Servidor",
        value=guild_status,
        inline=False
    )
    
    # Permisos del canal
    channel_status = ""
    for perm, desc, has_perm in required_channel_perms:
        status = "✅" if has_perm else "❌"
        channel_status += f"{status} {desc}\n"
    
    embed.add_field(
        name=f"🎧 Permisos en #{voice_channel.name}",
        value=channel_status,
        inline=False
    )
    
    # Verificar si todos los permisos están disponibles
    all_good = all([has_perm for _, _, has_perm in required_guild_perms + required_channel_perms])
    
    if all_good:
        embed.add_field(
            name="✅ Estado",
            value="¡Todos los permisos están correctos! Puedes usar `!record` sin problemas.",
            inline=False
        )
        embed.color = discord.Color.green()
    else:
        embed.add_field(
            name="❌ Estado",
            value="Faltan algunos permisos. Contacta a un administrador para solucionarlo.",
            inline=False
        )
        embed.color = discord.Color.red()
    
    await ctx.send(embed=embed)

@bot.command(name='test_conexion')
async def test_voice_connection(ctx):
    """Prueba la conexión de voz sin iniciar grabación."""
    if not ctx.author.voice:
        await ctx.send("❌ Debes estar en un canal de voz para probar la conexión.")
        return
    
    voice_channel = ctx.author.voice.channel
    
    try:
        await ctx.send(f"🔄 Probando conexión a {voice_channel.name}...")
        
        # Intentar conectar SIN reconexión automática
        voice_client = await voice_channel.connect(timeout=8.0, reconnect=False)
        await ctx.send("✅ ¡Conexión exitosa!")
        
        # Desconectar inmediatamente
        await voice_client.disconnect()
        await ctx.send("🔌 Desconectado. La conexión funciona correctamente.")
        
    except discord.errors.ConnectionClosed as e:
        if e.code == 4006:
            await ctx.send(f"❌ **Error 4006 - Permisos insuficientes**\n"
                          f"🔧 **Soluciones**:\n"
                          f"• Usa `!permisos` para verificar permisos específicos\n"
                          f"• Pide a un administrador usar `!fijar_permisos`\n"
                          f"• Verifica que el bot tenga rol con permisos de voz\n"
                          f"💡 **Alternativa**: Usa modo manual (siempre funciona)")
        else:
            await ctx.send(f"❌ **Error de conexión Discord**: {e.code}\n"
                          f"💡 **Solución**: Usa `!diagnostico` para más información")
    except asyncio.TimeoutError:
        await ctx.send("❌ **Timeout**: No pude conectarme en 8 segundos\n"
                      f"💡 Posibles causas: conexión lenta o permisos")
    except Exception as e:
        await ctx.send(f"❌ **Error**: {str(e)}\n"
                      f"💡 Usa `!diagnostico` para análisis completo")

@bot.command(name='preferencias')
async def reset_preferences(ctx):
    """Comando para restablecer preferencias del usuario."""
    user_id = str(ctx.author.id)
    
    # Limpiar preferencias existentes
    save_user_preference(user_id, coach_type=None, aspect=None, personality=None, 
                        voice=None, speed=None, voice_label=None, speed_label=None)
    
    await ctx.send("✅ Tus preferencias han sido restablecidas. En tu próximo audio se te pedirán nuevamente.")

@bot.command(name='info')
async def bot_info(ctx):
    """Información sobre el bot."""
    embed = discord.Embed(
        title="🤖 Clutch eSports Coach Bot",
        description="Análisis de comunicación en eSports con IA",
        color=discord.Color.blue()
    )
    
    embed.add_field(
        name="🎧 Grabación de Voz",
        value="• `!record` - Iniciar grabación (automática o manual)\n"
              "• `!stop` - Terminar grabación y análisis automático",
        inline=False
    )
    
    embed.add_field(
        name="🔧 Herramientas",
        value="• `!permisos` - Verificar permisos de voz\n"
              "• `!test_conexion` - Probar conexión de voz\n"
              "• `!preferencias` - Restablecer preferencias",
        inline=False
    )
    
    embed.add_field(
        name="🚀 Flujo Automático",
        value="1. Únete a un canal de voz\n"
              "2. Usa `!record` - El bot graba automáticamente\n"
              "3. Comunícate durante tu partida\n"
              "4. Usa `!stop` - Análisis automático",
        inline=False
    )
    
    embed.add_field(
        name="📁 Flujo Manual (Fallback)",
        value="1. Usa `!record` - Bot se conecta\n"
              "2. Graba externamente (OBS, Audacity)\n"
              "3. Usa `!stop` y sube tu archivo\n"
              "4. Análisis automático",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Tecnología",
        value="• **Transcripción**: OpenAI Whisper\n"
              "• **Análisis**: GPT-4 personalizado\n"
              "• **TTS**: Google Text-to-Speech\n"
              "• **Almacenamiento**: AWS S3 + DynamoDB",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='diagnostico')
async def full_diagnostic(ctx):
    """Diagnóstico completo del bot para resolver errores de conexión."""
    embed = discord.Embed(
        title="🔧 Diagnóstico Completo del Bot",
        description="Verificando todo el sistema para resolver errores de conexión",
        color=discord.Color.orange()
    )
    
    # 1. Verificar conexión del bot
    bot_latency = round(bot.latency * 1000, 2)
    embed.add_field(
        name="📡 Conexión del Bot",
        value=f"• **Latencia**: {bot_latency}ms\n"
              f"• **Estado**: {'🟢 Conectado' if bot.is_ready() else '🔴 Desconectado'}\n"
              f"• **Servidores**: {len(bot.guilds)}",
        inline=True
    )
    
    # 2. Verificar intents
    intents_status = ""
    required_intents = [
        ("message_content", bot.intents.message_content),
        ("voice_states", bot.intents.voice_states),
        ("guilds", bot.intents.guilds),
        ("members", bot.intents.members)
    ]
    
    for intent_name, enabled in required_intents:
        status = "✅" if enabled else "❌"
        intents_status += f"{status} {intent_name}\n"
    
    embed.add_field(
        name="🔑 Intents Discord",
        value=intents_status,
        inline=True
    )
    
    # 3. Verificar usuario en canal de voz
    user_voice_status = "❌ No está en canal de voz"
    voice_channel_name = "N/A"
    
    if ctx.author.voice:
        user_voice_status = "✅ En canal de voz"
        voice_channel_name = ctx.author.voice.channel.name
    
    embed.add_field(
        name="🎧 Estado del Usuario",
        value=f"• **Estado**: {user_voice_status}\n"
              f"• **Canal**: {voice_channel_name}",
        inline=True
    )
    
    # 4. Verificar rol del bot
    bot_member = ctx.guild.me
    highest_role = bot_member.top_role
    role_position = highest_role.position
    
    embed.add_field(
        name="👤 Información del Bot",
        value=f"• **Rol más alto**: {highest_role.name}\n"
              f"• **Posición del rol**: {role_position}\n"
              f"• **Administrador**: {'✅' if bot_member.guild_permissions.administrator else '❌'}",
        inline=True
    )    # 5. Verificar dependencias de voz
    voice_deps_status = ""
    
    # Verificar discord.sinks sin importar directamente
    try:
        import sys
        sinks_available = 'discord.sinks' in sys.modules or False
        voice_deps_status += f"{'✅' if sinks_available else '❌'} discord.sinks {'disponible' if sinks_available else 'no disponible (modo manual activo)'}\n"
    except:
        voice_deps_status += "❌ discord.sinks no disponible (modo manual activo)\n"
    
    try:
        import nacl
        voice_deps_status += "✅ PyNaCl instalado\n"
    except ImportError:
        voice_deps_status += "❌ PyNaCl faltante\n"
    
    # Nota: Opus no es crítico para modo manual
    voice_deps_status += "✅ Modo manual - no requiere dependencias adicionales\n"
    
    embed.add_field(
        name="📦 Dependencias de Voz",
        value=voice_deps_status,
        inline=True
    )
    
    # 6. Estado de grabaciones activas
    active_count = len(active_recordings)
    embed.add_field(
        name="🎙️ Grabaciones Activas",
        value=f"• **Activas**: {active_count}\n"
              f"• **Usuario**: {'✅' if str(ctx.author.id) in active_recordings else '❌'}",
        inline=True
    )
    
    # 7. Recomendaciones específicas para error 4006
    if not ctx.author.voice:
        embed.add_field(
            name="💡 Solución Inmediata",
            value="1. **Únete a un canal de voz**\n"
                  "2. Usa `!permisos` para verificar\n"
                  "3. Prueba `!test_conexion`",
            inline=False
        )
    else:
        embed.add_field(
            name="🔧 Pasos de Resolución",
            value="1. Usa `!permisos` en tu canal\n"
                  "2. Verifica que el bot tenga rol adecuado\n"
                  "3. Prueba `!test_conexion` primero\n"
                  "4. Si persiste, reinicia Discord\n"
                  "5. Como último recurso: modo manual",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='fijar_permisos')
@commands.has_permissions(administrator=True)
async def fix_permissions(ctx):
    """Comando para administradores para verificar y sugerir cómo fijar permisos."""
    bot_member = ctx.guild.me
    
    embed = discord.Embed(
        title="🔧 Guía para Administradores - Fijar Permisos",
        description="Cómo configurar correctamente los permisos del bot",
        color=discord.Color.gold()
    )
      # Permisos requeridos
    required_perms = [
        "connect", "speak", "use_voice_activation", 
        "view_channel", "send_messages", "read_message_history"
    ]
    missing_perms = []
    for perm in required_perms:
        if not getattr(bot_member.guild_permissions, perm, False):
            missing_perms.append(perm)
    
    if missing_perms:
        embed.add_field(
            name="❌ Permisos Faltantes",
            value="\n".join([f"• `{perm}`" for perm in missing_perms]),
            inline=False
        )
        
        embed.add_field(
            name="🔧 Cómo Solucionarlo",
            value="1. Ve a **Configuración del Servidor**\n"
                  "2. Selecciona **Roles**\n"
                  f"3. Encuentra el rol **{bot_member.top_role.name}**\n"
                  "4. Activa los permisos faltantes\n"
                  "5. Guarda cambios",
            inline=False
        )
        
        embed.add_field(
            name="⚡ Solución Rápida",
            value="Dar al bot el permiso de **Administrador** "
                  "(no recomendado para producción)",
            inline=False
        )
    else:
        embed.add_field(
            name="✅ Estado",
            value="Todos los permisos están correctos a nivel servidor",
            inline=False
        )
    
    # Verificar permisos de canal
    voice_channels = [ch for ch in ctx.guild.voice_channels]
    problematic_channels = []
      for channel in voice_channels:
        channel_perms = channel.permissions_for(bot_member)
        if not (channel_perms.connect and channel_perms.speak):
            problematic_channels.append(channel.name)
    
    if problematic_channels:
        embed.add_field(
            name="⚠️ Canales con Problemas",
            value="\n".join([f"• #{ch}" for ch in problematic_channels[:5]]),
            inline=False
        )
          embed.add_field(
            name="🔧 Fijar Canales Específicos",
            value="1. Click derecho en el canal problemático\n"
                  "2. **Editar Canal** → **Permisos**\n"
                  f"3. Agregar rol **{bot_member.top_role.name}**\n"
                  "4. Activar: **Conectar** y **Hablar**\n"
                  "5. Guardar",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='status')
async def bot_status(ctx):
    """Muestra el estado actual del bot y grabaciones activas."""
    embed = discord.Embed(
        title="📊 Estado del Bot",
        description="Información actual del sistema",
        color=discord.Color.blue()
    )
    
    # Estado general
    embed.add_field(
        name="🤖 Bot",
        value=f"• **Latencia**: {round(bot.latency * 1000, 1)}ms\n"
              f"• **Servidores**: {len(bot.guilds)}\n"
              f"• **Usuarios activos**: {len(active_recordings)}",
        inline=True
    )
      # Estado de voz
    if ctx.voice_client:
        embed.add_field(
            name="🎧 Conexión de Voz",
            value=f"• **Canal**: {ctx.voice_client.channel.name}\n"
                  f"• **Latencia**: {round(ctx.voice_client.latency * 1000, 1)}ms\n"
                  f"• **Estado**: Conectado",
            inline=True
        )
    else:
        embed.add_field(
            name="🎧 Conexión de Voz",
            value="• **Estado**: Desconectado\n"
                  f"• **Último error**: {'4006' if hasattr(ctx.guild, '_last_voice_error') else 'Ninguno'}",
            inline=True
        )
      # Grabaciones activas
    if active_recordings:
        recordings_text = ""
        for user_id, recorder in active_recordings.items():
            duration = recorder.get_duration()
            recordings_text += f"• <@{user_id}>: {duration:.1f}s\n"
        
        embed.add_field(
            name="🎙️ Grabaciones Activas",
            value=recordings_text[:1000],  # Limitar longitud
            inline=False
        )
    else:
        embed.add_field(
            name="🎙️ Grabaciones Activas",
            value="• Ninguna grabación en curso",
            inline=False
        )
      # Consejos
    embed.add_field(
        name="💡 Comandos Útiles",
        value="• `!diagnostico` - Diagnóstico completo\n"
              "• `!permisos` - Verificar permisos\n"
              "• `!test_conexion` - Probar conexión",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='disconnect')
async def force_disconnect(ctx):
    """Desconecta el bot del canal de voz (solo para emergencias)."""
    if not ctx.voice_client:
        await ctx.send("❌ El bot no está conectado a ningún canal de voz.")
        return
    
    try:
        channel_name = ctx.voice_client.channel.name
        await ctx.voice_client.disconnect()
        
        # Limpiar grabaciones activas del servidor
        guild_id = str(ctx.guild.id)
        to_remove = []
        for key, recorder in active_recordings.items():
            if recorder.guild_id == guild_id:
                to_remove.append(key)
        
        for key in to_remove:
            del active_recordings[key]
        
        await ctx.send(f"🔌 Desconectado exitosamente de {channel_name}\n"
                      f"🧹 Grabaciones activas limpiadas: {len(to_remove)}")
        
    except Exception as e:
        await ctx.send(f"❌ Error desconectando: {str(e)}")

# ============================================================================
# INICIO DEL BOT
# ============================================================================

if __name__ == "__main__":
    print("🎧 Clutch eSports Bot - Modo Cloud-Only con Grabación Automática")
    print("☁️ Sin almacenamiento local - Todo en AWS")
    print(f"🌍 Región AWS: {os.getenv('AWS_REGION')}")
    print(f"🪣 S3 Bucket: {os.getenv('S3_BUCKET_NAME')}")
    print(f"💾 DynamoDB: {os.getenv('DYNAMODB_TABLE_NAME')}")
    print("🚀 Iniciando bot con capacidad de grabación automática...")
    
    print("\n🎮 COMANDOS PRINCIPALES:")
    print("   🎙️ !record → Iniciar grabación (automática o manual)")
    print("   ⏹️ !stop → Terminar grabación y análisis automático")  
    print("   ⚙️ !preferencias → Restablecer preferencias")
    print("   ℹ️ !info → Información completa del bot")
    
    print("\n🔧 COMANDOS DE DIAGNÓSTICO:")
    print("   🔍 !permisos → Verificar permisos de voz")
    print("   🧪 !test_conexion → Probar conexión de voz")
    
    print("\n💡 SOLUCIÓN PARA ERROR 4006:")
    print("   1. Verificar permisos con !permisos")
    print("   2. Probar conexión con !test_conexion")
    print("   3. Asegurar que el bot tenga rol con permisos de voz")
    print("   4. Verificar que el canal de voz permita al bot conectarse")
    
    if not DISCORD_TOKEN:
        print("❌ Error: DISCORD_TOKEN no encontrado en .env")
        sys.exit(1)
    
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY no encontrado en .env")
        sys.exit(1)
    
    try:
        bot.run(DISCORD_TOKEN)
    except Exception as e:
        print(f"❌ Error ejecutando bot: {e}")
