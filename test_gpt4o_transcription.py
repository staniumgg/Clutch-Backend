#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script para probar la transcripción con GPT-4o
"""

import os
import sys
import requests
import base64
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def test_gpt4o_transcription():
    """Prueba la transcripción con GPT-4o usando el archivo de test de ElevenLabs."""
    
    # Leer el archivo de audio de prueba
    audio_file = "test_elevenlabs.mp3"
    if not os.path.exists(audio_file):
        print(f"❌ Archivo de audio no encontrado: {audio_file}")
        return False
    
    with open(audio_file, 'rb') as f:
        audio_data = f.read()
    
    print(f"📁 Archivo leído: {len(audio_data)} bytes")
    
    # Configurar la API de GPT-4o
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Codificar audio en base64
    audio_b64 = base64.b64encode(audio_data).decode('utf-8')
    
    # Crear prompt contextual
    game_name = "Call of Duty"
    context_prompt = f"Estás transcribiendo audio de una partida de {game_name} en Chile. " \
                    f"El audio contiene comunicación de jugadores durante el juego. " \
                    f"Transcribe exactamente lo que escuchas, incluyendo jerga gamer, " \
                    f"términos específicos del juego, y expresiones chilenas. " \
                    f"Mantén la naturalidad del lenguaje hablado."
    
    payload = {
        "model": "gpt-4o-audio-preview",
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
        print("🔊 Enviando audio a GPT-4o para transcripción...")
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        transcribed_text = result['choices'][0]['message']['content']
        
        print("✅ Transcripción completada!")
        print(f"📝 Resultado: {transcribed_text}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Error en la transcripción con GPT-4o: {e}")
        if 'response' in locals():
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    print("🎤 Probando transcripción con GPT-4o...")
    success = test_gpt4o_transcription()
    if success:
        print("✅ Test completado exitosamente")
    else:
        print("❌ Test falló")
