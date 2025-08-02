#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test completo del procesador con GPT-4o y ElevenLabs
"""

import subprocess
import sys
import os

def test_complete_pipeline():
    """Prueba el pipeline completo: audio -> GPT-4o transcription -> GPT analysis"""
    
    # Usar el archivo de audio de prueba
    audio_file = "test_elevenlabs.mp3"
    if not os.path.exists(audio_file):
        print(f"❌ Archivo de audio no encontrado: {audio_file}")
        return False
    
    # Leer el archivo de audio
    with open(audio_file, 'rb') as f:
        audio_data = f.read()
    
    print(f"📁 Probando con archivo: {audio_file} ({len(audio_data)} bytes)")
    
    # Parámetros de prueba
    user_id = "test_user_123"
    username = "TestUser"
    timestamp = "1751986704129"
    
    try:
        # Ejecutar el procesador
        print("🔄 Ejecutando procesador con GPT-4o...")
        process = subprocess.Popen(
            ['python', 'esports_processor_simple.py', user_id, username, timestamp],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Enviar datos de audio
        stdout, stderr = process.communicate(input=audio_data)
          # Mostrar salida
        if stderr:
            print("📝 STDERR:")
            try:
                print(stderr.decode('utf-8'))
            except UnicodeDecodeError:
                print(stderr.decode('utf-8', errors='replace'))
        
        if stdout:
            print("📄 STDOUT:")
            try:
                print(stdout.decode('utf-8'))
            except UnicodeDecodeError:
                print(stdout.decode('utf-8', errors='replace'))
        
        if process.returncode == 0:
            print("✅ Procesamiento completado exitosamente")
            return True
        else:
            print(f"❌ Procesamiento falló con código: {process.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Error ejecutando el procesador: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Probando pipeline completo con GPT-4o...")
    success = test_complete_pipeline()
    if success:
        print("🎉 ¡Pipeline completo funciona correctamente!")
    else:
        print("💥 Pipeline falló")
