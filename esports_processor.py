#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de procesamiento de audio para Clutch eSports Coach.
Este archivo es llamado desde index.js para procesar archivos de audio.
NO ES UN BOT - Es solo un script de procesamiento.

Uso: python esports_processor.py <ruta_archivo_mp3>
"""

import os
import sys
import json
import requests
import time
import random
import tempfile
from pathlib import Path
from dotenv import load_dotenv
from mutagen.mp3 import MP3, HeaderNotFoundError
from dynamodb_config import save_analysis_complete

# Configurar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Cargar variables de entorno
load_dotenv()

# Función para imprimir sin problemas de encoding
def safe_print(message):
    """Imprime mensajes de forma segura sin problemas de encoding"""
    try:
        print(message)
    except UnicodeEncodeError:
        # Fallback: reemplazar caracteres problemáticos
        safe_message = message.encode('ascii', 'replace').decode('ascii')
        print(safe_message)

# Configuración de APIs
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_TTS_VOICE = os.getenv("GOOGLE_TTS_VOICE", "es-ES-Standard-A")

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
            safe_print("[WHISPER] Transcribiendo audio con Whisper...")
            response = requests.post(url, headers=headers, files=files)
            response.raise_for_status()
            result = response.json()
            
            safe_print("[OK] Transcripcion completada")
            return result['text'], result.get('segments', [])
            
        except requests.exceptions.RequestException as e:
            safe_print(f"[ERROR] Error en transcripcion Whisper: {e}")
            if response is not None:
                safe_print(f"Status: {response.status_code}")
                safe_print(f"Response: {response.text}")
            raise

def analyze_text(text, segments, user_id, analysis_prefs):
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

def extract_user_id_from_filename(filename):
    """Extrae el user_id del nombre del archivo: username-user_id-timestamp.mp3"""
    try:
        base_name = os.path.basename(filename)
        name_without_ext = os.path.splitext(base_name)[0]
        parts = name_without_ext.split('-')
        if len(parts) >= 2:
            # El user_id está en la segunda posición
            return parts[1]
        return None
    except Exception as e:
        safe_print(f"[ERROR] Error extrayendo user_id: {e}")
        return None

def process_audio_file(audio_file_path):
    """Procesa un archivo de audio completo."""
    safe_print(f"[PROCESO] Procesando archivo: {audio_file_path}")
    
    # Extraer user_id del nombre del archivo
    user_id = extract_user_id_from_filename(audio_file_path)
    if not user_id:
        safe_print("[ERROR] No se pudo extraer user_id del nombre del archivo")
        return {"error": "No se pudo extraer user_id del nombre del archivo"}
    
    safe_print(f"[USER] User ID extraido: {user_id}")
    
    # Verificar que el archivo existe
    if not os.path.exists(audio_file_path):
        safe_print(f"[ERROR] Archivo no encontrado: {audio_file_path}")
        return {"error": f"Archivo no encontrado: {audio_file_path}"}
    
    try:
        # Transcripción
        transcribed_text, transcribed_segments = transcribe_with_whisper(audio_file_path)
        
        if not transcribed_text or len(transcribed_text.strip()) < 10:
            safe_print("[WARNING] Transcripcion muy corta o vacia")
            return {"error": "Transcripción muy corta o vacía"}
        
        # Obtener preferencias del usuario
        user_prefs = get_user_preference(user_id)
        
        # Si no hay preferencias, usar valores por defecto
        if not user_prefs:
            safe_print("[INFO] Usando preferencias por defecto")
            analysis_prefs = {
                "coach_type": "Directo",
                "aspect": "Comunicación",
                "personality": "Introvertido"
            }
            # Guardar preferencias por defecto
            save_user_preference(user_id, **analysis_prefs)
        else:
            analysis_prefs = {
                "coach_type": user_prefs.get("coach_type", "Directo"),
                "aspect": user_prefs.get("aspect", "Comunicación"),
                "personality": user_prefs.get("personality", "Introvertido")
            }
        
        # Realizar análisis
        analysis_content = analyze_text(transcribed_text, transcribed_segments, user_id, analysis_prefs)
        
        # Guardar análisis completo (S3 + DynamoDB)
        try:
            result = save_analysis_complete(
                user_id=user_id,
                analysis_text=analysis_content,
                audio_file_path=audio_file_path,
                transcription=transcribed_text,
                user_preferences=analysis_prefs
            )
            
            if result['success']:
                print(f"✅ Análisis guardado - ID: {result['analysis_id']}")
                if result['s3_key']:
                    print(f"📤 Audio subido a S3: {result['s3_key']}")
        except Exception as e:
            print(f"⚠️ Error guardando en AWS: {e}")
        
        # Retornar resultado para index.js
        return {
            "success": True,
            "user_id": user_id,
            "transcription": transcribed_text,
            "analysis": analysis_content,
            "feedback_jugador": analysis_content,  # Para compatibilidad con index.js
            "segments_count": len(transcribed_segments),
            "coach_type": analysis_prefs.get("coach_type"),
            "aspect": analysis_prefs.get("aspect")
        }
        
    except Exception as e:
        print(f"❌ Error procesando archivo: {e}")
        return {"error": str(e)}

def main():
    """Función principal - llamada desde index.js"""
    if len(sys.argv) != 2:
        print("❌ Uso: python esports_processor.py <ruta_archivo_mp3>")
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    
    # Validar que OpenAI API key esté configurada
    if not OPENAI_API_KEY:
        print("❌ Error: OPENAI_API_KEY no encontrada en .env")
        result = {"error": "OPENAI_API_KEY no encontrada en .env"}
        print(json.dumps(result))
        sys.exit(1)
    
    # Procesar el archivo
    result = process_audio_file(audio_file_path)
    
    # Imprimir resultado como JSON para que index.js lo pueda leer
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    # Exit code según resultado
    if result.get("success"):
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
