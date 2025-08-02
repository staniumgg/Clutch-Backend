#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de procesamiento de audio para Clutch eSports Coach - Versión Limpia
Este archivo es llamado desde index.js para procesar archivos de audio.
NO ES UN BOT - Es solo un script de procesamiento.

Uso: python esports_processor_clean.py <ruta_archivo_mp3>
"""

import os
import sys
import json
import requests
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def log(message):
    """Envía logs a stderr para no contaminar el JSON de stdout"""
    sys.stderr.write(f"{message}\n")
    sys.stderr.flush()

def transcribe_with_whisper(audio_file_path):
    """Transcribe audio usando OpenAI Whisper."""
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    
    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'file': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg'),
            'model': (None, 'whisper-1'),
            'language': (None, 'es'),
            'response_format': (None, 'verbose_json'),
            'temperature': (None, '0.2')
        }
        
        try:
            log("[WHISPER] Iniciando transcripcion...")
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            
            log("[WHISPER] Transcripcion completada")
            return result['text'], result.get('segments', [])
            
        except requests.exceptions.RequestException as e:
            log(f"[ERROR] Error en transcripcion: {e}")
            raise

def analyze_with_gpt(text, segments, analysis_prefs):
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
    
    coach_type = analysis_prefs.get("coach_type", "Directo")
    aspect = analysis_prefs.get("aspect", "Comunicacion")
    personality = analysis_prefs.get("personality", "Introvertido")
    
    prompt = f"""
Eres un coach profesional de eSports especializado en Call of Duty y juegos tácticos FPS.

CONTEXTO DEL JUGADOR:
- Estilo de coaching: {coach_type}
- Aspecto a mejorar: {aspect}
- Personalidad: {personality}

TRANSCRIPCIÓN:
{text}

Analiza la comunicación del jugador y proporciona feedback específico sobre:

1. **Calidad de Callouts**: ¿Qué tan claros y útiles fueron?
2. **Timing**: ¿La información se dio en el momento correcto?
3. **Especificidad**: ¿Se dieron detalles útiles (posiciones, números de enemigos, etc.)?
4. **Mejoras Específicas**: 2-3 consejos concretos para mejorar

Responde en español, máximo 200 palabras, tono {coach_type.lower()}.
"""

    data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "Eres un coach profesional de eSports especializado en comunicación táctica."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 300,
        "temperature": 0.7
    }
    
    try:
        log("[GPT] Iniciando analisis...")
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()
        
        analysis_content = result['choices'][0]['message']['content'].strip()
        log("[GPT] Analisis completado")
        return analysis_content
        
    except requests.exceptions.RequestException as e:
        log(f"[ERROR] Error en analisis GPT: {e}")
        raise

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

def extract_user_id_from_filename(filename):
    """Extrae el user_id del nombre del archivo: username-user_id-timestamp.mp3"""
    try:
        base_name = os.path.basename(filename)
        name_without_ext = os.path.splitext(base_name)[0]
        parts = name_without_ext.split('-')
        if len(parts) >= 2:
            return parts[1]
        return None
    except Exception as e:
        log(f"[ERROR] Error extrayendo user_id: {e}")
        return None

def process_audio_file(audio_file_path):
    """Procesa un archivo de audio completo."""
    log(f"[PROCESO] Iniciando procesamiento")
    
    # Extraer user_id del nombre del archivo
    user_id = extract_user_id_from_filename(audio_file_path)
    if not user_id:
        log("[ERROR] No se pudo extraer user_id")
        return {"error": "No se pudo extraer user_id del nombre del archivo"}
    
    log(f"[USER] User ID: {user_id}")
    
    # Verificar que el archivo existe
    if not os.path.exists(audio_file_path):
        log(f"[ERROR] Archivo no encontrado")
        return {"error": f"Archivo no encontrado: {audio_file_path}"}
    
    try:
        # Transcripción
        transcribed_text, transcribed_segments = transcribe_with_whisper(audio_file_path)
        
        if not transcribed_text or len(transcribed_text.strip()) < 10:
            log("[WARNING] Transcripcion muy corta")
            return {"error": "Transcripción muy corta o vacía"}
        
        # Obtener preferencias del usuario
        user_prefs = get_user_preference(user_id)
        
        # Si no hay preferencias, usar valores por defecto
        if not user_prefs:
            log("[INFO] Usando preferencias por defecto")
            analysis_prefs = {
                "coach_type": "Directo",
                "aspect": "Comunicacion",
                "personality": "Introvertido"
            }
        else:
            analysis_prefs = user_prefs
            log(f"[PREFS] Coach: {analysis_prefs.get('coach_type', 'Directo')}")
        
        # Análisis con GPT
        analysis_content = analyze_with_gpt(transcribed_text, transcribed_segments, analysis_prefs)
        
        log("[SUCCESS] Procesamiento completado")
        
        # Retornar resultado para index.js
        return {
            "success": True,
            "user_id": user_id,
            "transcription": transcribed_text,
            "analysis": analysis_content,
            "feedback_jugador": analysis_content,
            "segments_count": len(transcribed_segments),
            "coach_type": analysis_prefs.get("coach_type"),
            "aspect": analysis_prefs.get("aspect")
        }
        
    except Exception as e:
        log(f"[ERROR] Error procesando: {e}")
        return {"error": str(e)}

def main():
    """Función principal - llamada desde index.js"""
    if len(sys.argv) != 2:
        log("[ERROR] Uso: python esports_processor_clean.py <ruta_archivo_mp3>")
        result = {"error": "Uso incorrecto"}
        print(json.dumps(result))
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    
    # Validar que OpenAI API key esté configurada
    if not OPENAI_API_KEY:
        log("[ERROR] OPENAI_API_KEY no encontrada en .env")
        result = {"error": "OPENAI_API_KEY no encontrada en .env"}
        print(json.dumps(result))
        sys.exit(1)
    
    log(f"[INICIO] Procesando archivo: {audio_file_path}")
    
    # Procesar el archivo
    result = process_audio_file(audio_file_path)
    
    # Solo el JSON va a stdout
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # Exit code según resultado
    if result.get("success"):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
