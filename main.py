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
    tts_preferences: str = Form(...),
    user_personality_test: str = Form(...),
    player_audio: UploadFile = File(None),
    coach_audio: UploadFile = File(None)
):
    print(">>>>> [MAIN] Request received in /guardar-analisis/")
    print(f"       user_id: {user_id}")
    print(f"       tts_preferences (raw): {tts_preferences}")
    print(f"       user_personality_test (raw): {user_personality_test}")

    # Parsear tts_preferences
    try:
        tts_prefs = json.loads(tts_preferences) if tts_preferences else {}
    except Exception as e:
        print(f"[ERROR] No se pudo parsear tts_preferences: {e}")
        tts_prefs = {}

    # Parsear user_personality_test
    try:
        personality_test = json.loads(user_personality_test) if user_personality_test else []
    except Exception as e:
        print(f"[ERROR] No se pudo parsear user_personality_test: {e}")
        personality_test = []

    player_audio_bytes = await player_audio.read() if player_audio else None
    coach_audio_bytes = await coach_audio.read() if coach_audio else None
    print(f">>>>> [MAIN] Player audio read: {len(player_audio_bytes) if player_audio_bytes else 'No'} bytes")
    print(f">>>>> [MAIN] Coach audio read: {len(coach_audio_bytes) if coach_audio_bytes else 'No'} bytes")

    # Guardar en DynamoDB
    result = await asyncio.to_thread(
        save_analysis_complete,
        user_id=user_id,
        analysis_text=analysis_text,
        player_audio_data=player_audio_bytes,
        coach_audio_data=coach_audio_bytes,
        base_filename=player_audio.filename if player_audio else f"analysis_{user_id}_{int(__import__('time').time())}.mp3",
        transcription=transcription,
        tts_preferences=tts_prefs,
        user_personality_test=personality_test
    )

    # Echo para debug
    result["echo_tts_preferences"] = tts_prefs
    result["echo_user_personality_test"] = personality_test

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
