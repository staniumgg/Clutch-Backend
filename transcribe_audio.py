import os
import requests
import sys
from dotenv import load_dotenv
import json

def transcribe_with_whisper(audio_path):
    """
    Transcribe un archivo de audio utilizando el modelo Whisper de OpenAI.
    """
    # Cargar variables de entorno desde el archivo .env
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("No se encontró OPENAI_API_KEY en las variables de entorno. Asegúrate de tener un archivo .env válido.")

    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    
    files = {
        'file': (os.path.basename(audio_path), open(audio_path, 'rb'), 'audio/mpeg'),
        'model': (None, 'whisper-1'),
        'language': (None, 'es'),
        'response_format': (None, 'verbose_json'),
        'temperature': (None, '0.2'),
        'prompt': (None, 'Esta es una grabación de comunicación de voz de un equipo de esports en español, con llamadas estratégicas y coordinación.')
    }
    
    try:
        print(f"Transcribiendo el archivo: {os.path.basename(audio_path)}...")
        response = requests.post(url, headers=headers, files=files)
        response.raise_for_status()
        result = response.json()
        
        # Guardar el resultado completo en un archivo JSON
        output_filename = os.path.splitext(os.path.basename(audio_path))[0] + ".json"
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)
        print(f"\n✅ Resultado completo guardado en: {output_filename}")

        print("\n=== TRANSCRIPCIÓN COMPLETA ===")
        print(result['text'])
        
        # Imprimir los segmentos con timestamps
        print("\n=== SEGMENTOS DETALLADOS (JSON) ===")
        print(json.dumps(result.get('segments', []), indent=4, ensure_ascii=False))

        return result['text']
        
    except requests.exceptions.RequestException as e:
        print(f"Error durante la solicitud a la API de Whisper: {e}")
        if 'response' in locals() and response is not None:
            print(f"Código de estado de la respuesta: {response.status_code}")
            print(f"Contenido de la respuesta: {response.text}")
        return None
    finally:
        # Asegurarse de que el archivo se cierre después de la solicitud
        if 'file' in files:
            files['file'][1].close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python transcribe_audio.py <ruta_al_archivo_de_audio.mp3>")
        sys.exit(1)
    
    audio_file_path = sys.argv[1]
    
    if not os.path.exists(audio_file_path):
        print(f"Error: El archivo '{audio_file_path}' no fue encontrado.")
        sys.exit(1)
        
    transcribe_with_whisper(audio_file_path)
