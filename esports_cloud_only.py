import os
import json
import requests
import time
from dotenv import load_dotenv
import mutagen  
from mutagen.mp3 import MP3, HeaderNotFoundError
from dynamodb_config import save_analysis_complete
import sys
import random
import discord
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
    
    transcript_with_timestamps = "\\n".join([
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
# COMANDOS DEL BOT DISCORD
# ============================================================================

@bot.event
async def on_ready():
    print(f"🤖 {bot.user} está conectado y listo!")
    print("📁 Modo: Solo Nube (S3 + DynamoDB)")
    print("🎧 Esperando archivos de audio...")

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

async def process_audio_attachment(message, attachment):
    """Procesa un archivo de audio adjunto desde Discord."""
    user_id = str(message.author.id)
    
    try:
        # Descargar audio a memoria
        audio_data = await attachment.read()
        
        # Enviar mensaje de confirmación
        await message.reply("🎧 ¡Audio recibido! Procesando tu comunicación...")
        
        # Crear colector de preferencias
        collector = PreferenceCollector(user_id)
        
        # Verificar si el usuario ya tiene preferencias guardadas
        existing_prefs = get_user_preference(user_id)
        
        if not existing_prefs:
            # Usuario nuevo - solicitar preferencias
            bienvenida = f"""¡Hola, {message.author.name}! 🎮

Bienvenido a **Clutch eSports Coach**. Para personalizar tu análisis, necesito conocer tus preferencias.

Responde las 5 preguntas usando los menús desplegables:

1. **Tipo de coach**: ¿Cómo prefieres recibir feedback?
2. **Aspecto a mejorar**: ¿En qué quieres enfocarte?
3. **Personalidad**: ¿Con qué tipo de jugador te identificas?
4. **Tipo de voz**: ¿Qué voz prefieres para el audio?
5. **Velocidad**: ¿A qué velocidad quieres el audio?

Mientras tanto, estoy procesando tu audio... ⚡"""
            
            await message.author.send(bienvenida)
            
            # Mostrar formulario de preferencias
            view = AllPreferencesView(collector)
            await message.author.send("**Configura tus preferencias:**", view=view)
            
            # Procesar audio en paralelo
            async def process_audio_async():
                transcribed_text, transcribed_segments = transcribe_with_whisper_from_bytes(
                    audio_data, attachment.filename
                )
                return transcribed_text, transcribed_segments
            
            # Iniciar procesamiento
            audio_task = asyncio.create_task(process_audio_async())
            
            # Esperar preferencias
            await collector.all_prefs_collected.wait()
            
            # Esperar audio si aún no termina
            transcribed_text, transcribed_segments = await audio_task
            
            # Usar preferencias recolectadas
            analysis_prefs = collector.analysis_prefs
            tts_prefs = collector.tts_prefs
            
        else:
            # Usuario existente - usar preferencias guardadas
            await message.reply("⚡ Procesando con tus preferencias guardadas...")
            
            # Procesar audio directamente
            transcribed_text, transcribed_segments = transcribe_with_whisper_from_bytes(
                audio_data, attachment.filename
            )
            
            # Usar preferencias existentes
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
        
        # Crear archivo temporal para subir a S3
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_audio_path = temp_file.name
        
        try:
            # Guardar análisis completo (S3 + DynamoDB)
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
            # Limpiar archivo temporal
            os.unlink(temp_audio_path)
        
        # Generar audio TTS
        tts_audio_bytes = generate_tts_audio_to_bytes(analysis_content, user_id, tts_prefs)
        
        # Enviar feedback
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
            # Crear archivo Discord desde bytes
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
    info_text = """
🤖 **Clutch eSports Coach Bot**

📁 **Modo:** Solo Nube (S3 + DynamoDB)
🎧 **Función:** Análisis de comunicación en eSports
☁️ **Almacenamiento:** Todo en AWS

**Cómo usar:**
1. Sube un archivo MP3/WAV con tu comunicación
2. El bot transcribe con Whisper (OpenAI)
3. Analiza con GPT-4 según tus preferencias
4. Recibe feedback personalizado por audio

**Comandos:**
• `!preferencias` - Restablecer preferencias
• `!info` - Mostrar esta información

Desarrollado para mejorar tu comunicación en los eSports 🎮
"""
    await ctx.send(info_text)

# ============================================================================
# INICIO DEL BOT
# ============================================================================

if __name__ == "__main__":
    print("🎧 Clutch eSports Bot - Modo Cloud-Only")
    print("☁️ Sin almacenamiento local - Todo en AWS")
    print(f"🌍 Región AWS: {os.getenv('AWS_REGION')}")
    print(f"🪣 S3 Bucket: {os.getenv('S3_BUCKET_NAME')}")
    print(f"💾 DynamoDB: {os.getenv('DYNAMODB_TABLE_NAME')}")
    print("🚀 Iniciando bot...")
    
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
