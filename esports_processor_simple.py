#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de procesamiento de audio para Clutch eSports Coach - Versión Simple
Este archivo es llamado desde index.js para procesar archivos de audio.
Recibe el audio crudo desde stdin y el user_id como argumento.

Uso: node | python esports_processor_simple.py <user_id> <username> <timestamp>
"""

import os
import sys
import json
import requests
import time
import random
from pathlib import Path
from dotenv import load_dotenv

# Importar módulos de AWS
try:
    from dynamodb_config import save_analysis_complete
    AWS_AVAILABLE = True
except ImportError:
    AWS_AVAILABLE = False

# Cargar variables de entorno
load_dotenv()

# Configuración de APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

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
        sys.stderr.write("[WHISPER] Transcribiendo audio desde bytes con Whisper...\n")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        
        result = response.json()
        sys.stderr.write(f"[WHISPER] Transcripción completada. Texto: {result['text'][:100]}...\n")
        
        segments = result.get('segments', [])
        return result['text'], segments
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error en la transcripción con Whisper: {e}\n")
        return None, None

def transcribe_with_gpt4o_mini_from_bytes(audio_data, filename, game_name="Call of Duty"):
    """Transcribe audio desde bytes usando GPT-4o-mini Audio (más económico)."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Codificar audio en base64
    import base64
    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
    
    # Crear prompt contextual basado en el juego
    context_prompt = f"Estás transcribiendo audio de una partida de {game_name} en Chile. " \
                    f"El audio contiene comunicación de jugadores durante el juego. " \
                    f"Transcribe exactamente lo que escuchas, incluyendo jerga gamer, " \
                    f"términos específicos del juego, y expresiones chilenas. " \
                    f"Mantén la naturalidad del lenguaje hablado."
    
    payload = {
        "model": "gpt-4o-mini-transcribe",
        "modalities": ["text"],
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": context_prompt
                    },
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": audio_b64,
                            "format": "mp3"
                        }
                    }
                ]
            }
        ],
        "temperature": 0,
        "response_format": {"type": "text"}
    }
    
    try:
        sys.stderr.write("[GPT-4O-MINI] Transcribiendo audio con GPT-4o-mini (económico)...\n")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        transcribed_text = result['choices'][0]['message']['content']
        sys.stderr.write(f"[GPT-4O-MINI] Transcripción completada. Texto: {transcribed_text[:100]}...\n")
        
        # GPT-4o-mini no proporciona segmentos como Whisper, crear uno simple
        segments = [{
            "start": 0.0,
            "end": 30.0,  # Estimación básica
            "text": transcribed_text
        }]
        
        return transcribed_text, segments
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error en la transcripción con GPT-4o-mini: {e}\n")
        # Fallback a Whisper si falla GPT-4o-mini
        sys.stderr.write("[FALLBACK] Intentando con Whisper como respaldo...\n")
        return transcribe_with_whisper_from_bytes(audio_data, filename)
        result = response.json()
        
        sys.stderr.write("[OK] Transcripcion completada\n")
        return result['text'], result.get('segments', [])
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error en transcripcion Whisper: {e}\n")
        if 'response' in locals() and response is not None:
            sys.stderr.write(f"Status: {response.status_code}\n")
            sys.stderr.write(f"Response: {response.text}\n")
        raise

def transcribe_with_gpt4o_transcribe_from_bytes(audio_data, filename, game_name="Call of Duty"):
    """Transcribe audio desde bytes usando gpt-4o-transcribe (modelo específico para transcripción)."""
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Crear prompt contextual basado en el juego y país
    context_prompt = f"Estás transcribiendo audio de una partida de {game_name} en Chile. " \
                    f"El audio contiene comunicación de jugadores durante el juego. " \
                    f"Incluye jerga gamer, términos específicos del juego, y expresiones chilenas."
    
    files = {
        'file': (filename, audio_data, 'audio/mpeg'),
        'model': (None, 'gpt-4o-mini-transcribe'),
        'language': (None, 'es'),  # español
        'prompt': (None, context_prompt),
        'response_format': (None, 'json'),
        'temperature': (None, '0')
    }
    
    try:
        sys.stderr.write("[GPT-4O-TRANSCRIBE] Transcribiendo audio con gpt-4o-transcribe...\n")
        sys.stderr.write(f"[CONTEXTO] Juego: {game_name}, País: Chile\n")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        
        result = response.json()
        transcribed_text = result.get('text', '')
        # Con formato 'json', gpt-4o-transcribe no devuelve segmentos detallados
        segments = [{
            "start": 0.0,
            "end": 30.0,  # Estimación básica
            "text": transcribed_text
        }]
        
        sys.stderr.write(f"[GPT-4O-TRANSCRIBE] Transcripción completada. Texto: {transcribed_text[:100]}...\n")
        
        return transcribed_text, segments
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error en la transcripción con gpt-4o-transcribe: {e}\n")
        # Fallback a Whisper si falla gpt-4o-transcribe
        sys.stderr.write("[FALLBACK] Intentando con Whisper como respaldo...\n")
        return transcribe_with_whisper_from_bytes(audio_data, filename)

def analyze_text(text, segments, user_id, analysis_prefs):
    """Analiza texto transcrito usando GPT."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    # Obtener todas las preferencias del usuario con valores por defecto
    game = analysis_prefs.get("game", "un juego específico")
    coach_type = analysis_prefs.get("coach_type", "un coach directo")
    aspect = analysis_prefs.get("aspect", "la comunicación")
    personality = analysis_prefs.get("personality", "un jugador introvertido")
    experience = analysis_prefs.get("experience", "un jugador casual")
    goal = analysis_prefs.get("goal", "mejorar en general")

    # Construcción del prompt dinámico
    system_prompt = f"""
Eres un coach de eSports profesional para el juego {game}. Tu especialidad es analizar la comunicación de los jugadores.
Tu estilo de coaching es {coach_type}. Te enfocas principalmente en el aspecto de {aspect}.
El jugador al que te diriges tiene una personalidad de tipo {personality}, un nivel de experiencia {experience} y su objetivo principal es {goal}.
Tu feedback debe ser altamente personalizado, adaptándose a todas estas características para que sea lo más útil y relevante posible para el jugador.
"""

    user_prompt = f"""
Analiza la siguiente transcripción de la comunicación de un jugador durante una partida.

TRANSCRIPCIÓN:
{text}

INSTRUCCIONES CRÍTICAS PARA TU RESPUESTA:
1.  **Formato de Salida**: Tu respuesta DEBE ser un texto plano, conversacional y fluido.
2.  **SIN MARKDOWN**: No uses NUNCA formato markdown. No incluyas asteriscos (`*`), negritas (`**`), guiones (`-`), ni ningún tipo de lista. La salida tiene que ser limpia para ser convertida a audio (TTS).
3.  **Tono**: Habla directamente al jugador de forma natural y constructiva.
4.  **Extensión**: Sé conciso. Limita tu respuesta a un máximo de 100 tokens.
5.  **Enfoque**: Céntrate en el aspecto principal a mejorar que es la {aspect}, considerando el resto de preferencias del jugador.

EJEMPLO DE RESPUESTA IDEAL (recuerda, es solo un ejemplo de formato):
"Hola, he revisado tu partida. En general, tu comunicación es buena, pero intenta ser más rápido con los callouts de enemigos en el punto B. Un aviso a tiempo puede cambiar el resultado de la ronda. Sigue así, vas por buen camino."

Ahora, analiza la transcripción y genera tu feedback personalizado.
"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": system_prompt.strip()},
            {"role": "user", "content": user_prompt.strip()}
        ],
        "max_tokens": 100,
        "temperature": 0.7,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    
    try:
        sys.stderr.write("[GPT] Analizando con GPT-4o-mini...\n")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        analysis_content = result['choices'][0]['message']['content'].strip()
        # Limpieza final para remover cualquier formato no deseado
        analysis_content = analysis_content.replace('*', '').replace('**', '').replace('\n', ' ')
        sys.stderr.write("[OK] Analisis GPT completado\n")
        return analysis_content
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error en analisis GPT: {e}\n")
        if 'response' in locals() and response is not None:
            sys.stderr.write(f"Status: {response.status_code}\n")
            sys.stderr.write(f"Response: {response.text}\n")
        raise

def structure_analysis(raw_analysis):
    """Estructura el análisis usando GPT-4o-mini para darle formato organizado."""
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    prompt = f"""Eres un asistente especializado en estructurar análisis de gaming. 

Toma el siguiente análisis de comunicación en gaming y estructúralo exactamente en este formato:

"Aspectos a mejorar":

- [punto específico 1]
- [punto específico 2] 
- [punto específico 3]

"Cómo mejorarlos":

- [consejo práctico y específico 1]
- [consejo práctico y específico 2]
- [consejo práctico y específico 3]

IMPORTANTE:
- Usa exactamente este formato con comillas
- Máximo 3 puntos en cada sección
- Sé específico y práctico
- Enfócate en comunicación para gaming
- Mantén el tono del análisis original

Análisis original:
{raw_analysis}"""

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "system",
                "content": "Eres un experto en estructurar feedback de gaming de manera clara y organizada. Tu trabajo es tomar análisis largos y convertirlos en formato estructurado fácil de leer."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 500,
        "temperature": 0.3,
        "top_p": 1,
        "frequency_penalty": 0,
        "presence_penalty": 0
    }
    
    try:
        sys.stderr.write("[STRUCTURE] Estructurando análisis con GPT-4o-mini...\n")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        structured_content = result['choices'][0]['message']['content'].strip()
        sys.stderr.write("[OK] Análisis estructurado completado\n")
        return structured_content
        
    except requests.exceptions.RequestException as e:
        sys.stderr.write(f"[ERROR] Error estructurando análisis: {e}\n")
        if 'response' in locals() and response is not None:
            sys.stderr.write(f"Status: {response.status_code}\n")
            sys.stderr.write(f"Response: {response.text}\n")
        # En caso de error, devolver el análisis original
        return raw_analysis

def get_user_preference(user_id):
    """Obtiene preferencias del usuario desde archivos JSON."""
    # Primero intentar con preferencias de ElevenLabs
    pref_file_elevenlabs = "user_preferences_elevenlabs.json"
    if os.path.exists(pref_file_elevenlabs):
        with open(pref_file_elevenlabs, "r", encoding="utf-8") as f:
            try:
                prefs = json.load(f)
                user_prefs = prefs.get(str(user_id), {})
                if user_prefs:
                    sys.stderr.write("[PREFS] Usando preferencias de ElevenLabs\n")
                    return user_prefs
            except Exception:
                pass
    
    # Fallback a preferencias normales
    pref_file = "user_preferences.json"
    if os.path.exists(pref_file):
        with open(pref_file, "r", encoding="utf-8") as f:
            try:
                prefs = json.load(f)
                user_prefs = prefs.get(str(user_id), {})
                if user_prefs:
                    sys.stderr.write("[PREFS] Usando preferencias estándar\n")
                    return user_prefs
            except Exception:
                pass
    
    sys.stderr.write("[PREFS] No se encontraron preferencias, usando defaults\n")
    return {}

def process_audio_stream(user_id, username, timestamp):
    """Procesa un stream de audio desde stdin."""
    sys.stderr.write(f"[PROCESO] Procesando audio para {username} ({user_id})\n")
    
    # Leer audio desde stdin
    audio_data = sys.stdin.buffer.read()
    if not audio_data:
        sys.stderr.write("[ERROR] No se recibieron datos de audio desde stdin.\n")
        return {"error": "No se recibieron datos de audio desde stdin."}
    
    sys.stderr.write(f"[OK] Leídos {len(audio_data)} bytes de audio desde stdin.\n")
    
    # Generar nombre de archivo base
    base_filename = f"{username}-{user_id}-{timestamp}.mp3"

    try:
        # Obtener preferencias del usuario ANTES de la transcripción para obtener el juego
        user_prefs = get_user_preference(user_id)
        
        if not user_prefs:
            sys.stderr.write("[INFO] Usando preferencias por defecto\n")
            analysis_prefs = {
                "game": "Call of Duty", "coach_type": "Directo", "aspect": "Comunicacion",
                "personality": "Introvertido", "experience": "Casual", "goal": "Mejorar"
            }
        else:
            analysis_prefs = user_prefs
        
        # Obtener nombre del juego para la transcripción contextual
        game_name = analysis_prefs.get("game", "Call of Duty")
        sys.stderr.write(f"[CONTEXTO] Usando contexto de juego: {game_name}\n")        # Transcripción con gpt-4o-transcribe (modelo específico para transcripción)
        transcribed_text, transcribed_segments = transcribe_with_gpt4o_transcribe_from_bytes(audio_data, base_filename, game_name)
        
        if not transcribed_text or len(transcribed_text.strip()) < 10:
            sys.stderr.write("[WARNING] Transcripcion muy corta o vacia\n")
            return {"error": "Transcripción muy corta o vacía"}
          # Análisis con GPT (ya tenemos analysis_prefs de antes)
        analysis_content = analyze_text(transcribed_text, transcribed_segments, user_id, analysis_prefs)
        
        # Estructurar análisis para mejor presentación
        structured_analysis = structure_analysis(analysis_content)
        
        # Guardar en AWS (si está disponible) - guardar el análisis original completo
        if AWS_AVAILABLE:
            sys.stderr.write("[AWS] Guardando análisis y subiendo audio a S3...\n")
            save_analysis_complete(
                user_id=user_id,
                analysis_text=analysis_content,  # Guardar análisis original en AWS
                audio_data=audio_data,
                base_filename=base_filename,
                transcription=transcribed_text,
                user_preferences=analysis_prefs
            )
        else:
            sys.stderr.write("[INFO] Módulos de AWS no disponibles. Omitiendo guardado en la nube.\n")
        
        # Retornar resultado para index.js - incluir ambos análisis
        return {
            "success": True,
            "analysis": analysis_content,          # Análisis original completo
            "structured_analysis": structured_analysis,  # Análisis estructurado
            "transcription": transcribed_text
        }
        
    except Exception as e:
        sys.stderr.write(f"[ERROR] Error fatal en el procesamiento de audio: {e}\n")
        return {"error": str(e)}

if __name__ == "__main__":
    try:
        if len(sys.argv) != 4:
            sys.stderr.write(f"[ERROR] Argumentos incorrectos. Recibidos: {len(sys.argv)-1}, esperados: 3\n")
            sys.stderr.write(f"[ERROR] Argumentos recibidos: {sys.argv[1:] if len(sys.argv) > 1 else 'ninguno'}\n")
            sys.stderr.write("Uso: <stdin> | python esports_processor_simple.py <user_id> <username> <timestamp>\n")
            sys.exit(1)
        
        user_id_arg = sys.argv[1]
        username_arg = sys.argv[2]
        timestamp_arg = sys.argv[3]
        
        sys.stderr.write(f"[ARGS] Procesando: user_id={user_id_arg}, username={username_arg}, timestamp={timestamp_arg}\n")
        
        result = process_audio_stream(user_id_arg, username_arg, timestamp_arg)
        
        # Imprimir resultado como JSON a stdout para que Node.js lo capture con UTF-8 correcto
        output_json = json.dumps(result, ensure_ascii=False, indent=None)
        sys.stdout.buffer.write(output_json.encode('utf-8'))
        sys.stdout.buffer.flush()
        
    except Exception as e:
        sys.stderr.write(f"[ERROR] Error fatal en main: {e}\n")
        error_result = {"error": f"Error fatal en main: {str(e)}"}
        error_json = json.dumps(error_result, ensure_ascii=False, indent=None)
        sys.stdout.buffer.write(error_json.encode('utf-8'))
        sys.stdout.buffer.flush()
        sys.exit(1)
