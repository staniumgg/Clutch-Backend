from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dynamodb_config import save_analysis_complete, get_analyses_by_user
from s3_config import s3_manager
import asyncio
import json

app = FastAPI()

# Configurar límites para archivos grandes
app.max_request_size = 50 * 1024 * 1024  # 50MB

# Permitir CORS para pruebas desde el origen del frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"],  # Solo el origen de tu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Clutch API online"}

@app.post("/guardar-analisis/")
async def guardar_analisis(
    user_id: str = Form(...),
    analysis_text: str = Form(...),
    transcription: str = Form(...),
    game: str = Form(...),
    coach_type: str = Form(...),
    personality: str = Form(...),
    elevenlabs_voice: str = Form(...),
    tts_speed: str = Form(...),
    personality_scales: str = Form(...),  # Recibir como JSON string
    player_audio: UploadFile = File(None),
    coach_audio: UploadFile = File(None)
):
    print(">>>>> [MAIN] Request received in /guardar-analisis/")
    print(f">>>>> [MAIN] Datos recibidos:")
    print(f"       user_id: {user_id}")
    print(f"       game: {game}")
    print(f"       coach_type: {coach_type}")
    print(f"       personality: {personality}")
    print(f"       elevenlabs_voice: {elevenlabs_voice}")
    print(f"       tts_speed: {tts_speed}")
    print(f"       personality_scales (raw): {personality_scales}")
    
    player_audio_bytes = await player_audio.read() if player_audio else None
    coach_audio_bytes = await coach_audio.read() if coach_audio else None
    print(f">>>>> [MAIN] Player audio read: {len(player_audio_bytes) if player_audio_bytes else 'No'} bytes")
    print(f">>>>> [MAIN] Coach audio read: {len(coach_audio_bytes) if coach_audio_bytes else 'No'} bytes")
    
    # Parsear personality_scales de forma segura como lista
    scales_list = []
    try:
        parsed = json.loads(personality_scales) if personality_scales else []
        if isinstance(parsed, list):
            scales_list = parsed
        else:
            print(f">>>>> [MAIN] personality_scales no es lista, tipo recibido: {type(parsed)}. Usando [].")
    except json.JSONDecodeError:
        print(f">>>>> [MAIN] Error parseando personality_scales, usando [].")

    # Mantener compatibilidad: campos planos + objeto meta opcional
    user_preferences = {
        "game": game,
        "coach_type": coach_type,
        "personality": personality,
        "elevenlabs_voice": elevenlabs_voice,
        "tts_speed": tts_speed,
        "personality_scales": scales_list,
        # Estructura opcional anidada para futuras consultas sin romper compatibilidad
        "personality_meta": {
            "type": personality,
            "scales": scales_list
        }
    }
    
    print(f">>>>> [MAIN] user_preferences completo: {user_preferences}")

    # Run the synchronous function in a separate thread
    result = await asyncio.to_thread(
        save_analysis_complete,
        user_id=user_id,
        analysis_text=analysis_text,
        player_audio_data=player_audio_bytes,
        coach_audio_data=coach_audio_bytes,
        base_filename=player_audio.filename if player_audio else f"analysis_{user_id}_{int(__import__('time').time())}.mp3",
        transcription=transcription,
        user_preferences=user_preferences
    )
    
    print(">>>>> [MAIN] Analysis saved, returning result.")
    return result

@app.get("/analisis/{user_id}")
async def obtener_analisis_por_usuario(user_id: str):
    """
    Obtiene todos los análisis para un user_id específico.
    """
    print(f">>>>> [MAIN] Request received in /analisis/{user_id}")
    
    # Ejecuta la función síncrona de DynamoDB en un hilo separado
    result = await asyncio.to_thread(get_analyses_by_user, user_id)
    
    if not result['success']:
        # Si hubo un error en la capa de datos, devuelve un error HTTP
        raise HTTPException(status_code=500, detail=result.get('error', 'Error interno del servidor.'))
        
    print(f">>>>> [MAIN] Found {len(result.get('data', []))} analyses for user {user_id}.")
    return result

@app.get("/get-audio-url/")
async def get_audio_url(user_id: str, filename: str):
    url = s3_manager.generate_presigned_url(user_id, filename)
    if not url:
        raise HTTPException(status_code=404, detail="Audio not found or error generating URL")
    return {"url": url}
