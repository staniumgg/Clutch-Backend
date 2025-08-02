#!/usr/bin/env python3
"""
Script para instalar dependencias de voz y solucionar el error WebSocket 4006.
Uso: python install_voice_deps.py
"""

import subprocess
import sys
import os
import platform

def run_command(command, description):
    """Ejecuta un comando y maneja errores."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Exitoso")
            return True
        else:
            print(f"❌ {description} - Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Excepción: {e}")
        return False

def install_voice_dependencies():
    """Instala todas las dependencias necesarias para grabación de voz."""
    print("🎧 INSTALADOR DE DEPENDENCIAS DE VOZ")
    print("=" * 50)
    
    # Detectar sistema operativo
    system = platform.system()
    print(f"🖥️ Sistema detectado: {system}")
    
    # Lista de dependencias a instalar
    dependencies = [
        ("pip install --upgrade pip", "Actualizando pip"),
        ("pip install --upgrade discord.py[voice]>=2.3.0", "Instalando discord.py[voice]"),
        ("pip install PyNaCl>=1.5.0", "Instalando PyNaCl (codec de audio)"),
        ("pip install pydub>=0.25.1", "Instalando pydub (procesamiento de audio)"),
    ]
    
    # Instalar dependencias específicas del sistema
    if system == "Windows":
        dependencies.extend([
            ("pip install python-opus", "Instalando python-opus (Windows)"),
        ])
    elif system == "Linux":
        print("🐧 Para Linux, también necesitas instalar:")
        print("   sudo apt-get install libffi-dev libopus-dev")
        dependencies.extend([
            ("pip install python-opus", "Instalando python-opus (Linux)"),
        ])
    elif system == "Darwin":  # macOS
        print("🍎 Para macOS, también necesitas instalar:")
        print("   brew install opus libffi")
        dependencies.extend([
            ("pip install python-opus", "Instalando python-opus (macOS)"),
        ])
    
    # Ejecutar instalaciones
    success_count = 0
    for command, description in dependencies:
        if run_command(command, description):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 RESUMEN: {success_count}/{len(dependencies)} instalaciones exitosas")
      # Verificar instalación
    print("\n🔍 VERIFICANDO INSTALACIÓN...")
    verification_tests = [
        ('python -c "import discord; print(f\'discord.py: {discord.__version__}\')"', "discord.py"),
        ('python -c "import nacl; print(\'PyNaCl: OK\')"', "PyNaCl"),
        ('python -c "import pydub; print(\'pydub: OK\')"', "pydub"),
    ]
    
    # Verificaciones opcionales
    try:
        run_command('python -c "import discord.sinks; print(\'discord.sinks: OK\')"', "discord.sinks (opcional)")
    except:
        print("⚠️ discord.sinks no disponible (puede ser normal en algunas versiones)")
    
    try:
        run_command('python -c "import opus; print(\'opus: OK\')"', "opus (opcional)")
    except:
        print("⚠️ opus no disponible (puede usar PyNaCl como alternativa)")
    
    for command, description in verification_tests:
        run_command(command, f"Verificando {description}")
    
    print("\n✅ INSTALACIÓN COMPLETADA")
    print("🎮 Ahora puedes usar el bot con grabación de voz!")
    print("\n💡 Si persisten errores:")
    print("   1. Reinicia tu terminal/IDE")
    print("   2. Usa !diagnostico en Discord")
    print("   3. Revisa permisos con !permisos")

def show_troubleshooting():
    """Muestra guía de resolución de problemas."""
    print("\n🔧 GUÍA DE RESOLUCIÓN - ERROR WEBSOCKET 4006")
    print("=" * 50)
    print("El error WebSocket 4006 se debe a:")
    print("• Permisos insuficientes del bot")
    print("• Problemas de conexión de red")
    print("• Dependencias de voz faltantes")
    print("• Configuración incorrecta del servidor")
    
    print("\n📋 PASOS DE SOLUCIÓN:")
    print("1. ✅ Verificar dependencias con este script")
    print("2. 🎧 Usar !diagnostico en Discord")
    print("3. 🔍 Usar !permisos en un canal de voz")
    print("4. 🧪 Usar !test_conexion para probar")
    print("5. ⚙️ Usar !fijar_permisos (solo admins)")
    
    print("\n🔧 CONFIGURACIÓN MANUAL DEL SERVIDOR:")
    print("• Rol del bot debe tener: 'Conectar' y 'Hablar'")
    print("• Canal de voz debe permitir al bot conectarse")
    print("• Bot debe estar por encima de otros roles en jerarquía")
    print("• Intents del bot deben incluir: voice_states, guilds")
    
    print("\n🆘 SI NADA FUNCIONA:")
    print("• Usa el modo manual: !record → graba externamente → !stop → sube archivo")
    print("• El análisis funcionará igual de bien")

if __name__ == "__main__":
    print("🎮 CLUTCH ESPORTS - INSTALADOR DE DEPENDENCIAS DE VOZ")
    print("Resolviendo error Discord WebSocket 4006")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--help":
        show_troubleshooting()
    else:
        install_voice_dependencies()
        show_troubleshooting()
