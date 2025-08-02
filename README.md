# Clutch Backend

Discord bot backend para análisis de gaming con integración de ElevenLabs TTS.

## Configuración

1. Copia `.env.example` a `.env` y completa tus valores:
   ```bash
   cp .env.example .env
   ```

2. Agrega tus credenciales de Firebase/Google Cloud en archivos JSON:
   - `clutch-gg-[project-id].json` - Firebase service account
   - `clutchgg-[project]-firebase-adminsdk-[key].json` - Firebase admin SDK

3. Instala dependencias:
   ```bash
   npm install
   pip install -r requirements.txt
   ```

4. Ejecuta el bot:
   ```bash
   node index_elevenlabs.js
   ```

## Archivos de Configuración Requeridos

- `.env` - Variables de entorno (usa .env.example como plantilla)
- Archivos JSON de Firebase/Google Cloud para autenticación
- `user_preferences_elevenlabs.json` - Se genera automáticamente

## Funcionalidades

- Grabación de audio en Discord
- Transcripción con OpenAI
- Análisis de gaming con IA
- Síntesis de voz con ElevenLabs
- Almacenamiento en AWS DynamoDB

## Comandos del Bot

- `!record` - Iniciar grabación
- `!stop` - Detener grabación y procesar análisis
