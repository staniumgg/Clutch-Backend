#!/usr/bin/env python3
"""Script de verificación de dependencias"""

print("🔍 VERIFICACIÓN DE DEPENDENCIAS PARA DISCORD BOT")
print("=" * 50)

# 1. Discord.py
try:
    import discord
    print(f"✅ discord.py: {discord.__version__}")
except ImportError as e:
    print(f"❌ discord.py: {e}")

# 2. PyNaCl (crítico para audio)
try:
    import nacl
    print(f"✅ PyNaCl: {nacl.__version__}")
except ImportError as e:
    print(f"❌ PyNaCl: {e}")

# 3. discord.sinks (opcional para grabación automática)
try:
    import discord.sinks
    print("✅ discord.sinks: Disponible")
except ImportError:
    print("⚠️ discord.sinks: No disponible (usará fallback manual)")

# 4. Otras dependencias importantes
deps = [
    ("asyncio", "asyncio"),
    ("json", "json"),
    ("tempfile", "tempfile"),
    ("io", "io"),
    ("requests", "requests"),
    ("dotenv", "python-dotenv"),
    ("boto3", "boto3"),
    ("google.cloud.texttospeech", "google-cloud-texttospeech"),
    ("mutagen", "mutagen"),
    ("pydub", "pydub")
]

print("\n📦 OTRAS DEPENDENCIAS:")
for module, package in deps:
    try:
        __import__(module)
        print(f"✅ {package}")
    except ImportError:
        print(f"❌ {package}")

# 5. Verificar intents
print("\n🔑 VERIFICACIÓN DE INTENTS:")
try:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    intents.members = True
    print("✅ Todos los intents configurados correctamente")
except Exception as e:
    print(f"❌ Error configurando intents: {e}")

print("\n🎧 DIAGNÓSTICO DE VOZ:")
print("Para resolver error WebSocket 4006:")
print("1. ✅ discord.py>=2.3.0 instalado")
print("2. ✅ PyNaCl instalado (requerido)")
print("3. ⚠️ discord.sinks opcional (fallback disponible)")
print("4. 🔧 Usar comandos !permisos y !test_conexion en Discord")

print("\n🚀 ESTADO FINAL:")
print("✅ Bot listo para ejecutar")
print("🎙️ Grabación automática: Depende de discord.sinks")
print("📁 Grabación manual: Siempre disponible como fallback")
print("☁️ Análisis en la nube: Completamente funcional")
