"""
Ejemplo de uso de DynamoDB para el proyecto Clutch.
Este archivo muestra cómo usar las funciones principales del DynamoDB manager.
"""

from dynamodb_config import dynamodb_manager
import json

def test_dynamodb_connection():
    """
    Prueba la conexión y funcionalidades básicas de DynamoDB.
    """
    print("🧪 Probando funcionalidades de DynamoDB para Clutch...")
    
    # Datos de ejemplo
    test_user_id = "123456789"
    test_analysis = "Tienes que mejorar la comunicación sobre posiciones específicas. En el minuto 1:30 dijiste 'ahí hay uno' pero no especificaste dónde. Procura usar callouts más precisos como 'uno en A site' o 'enemigo en connector'. También evita repetir 'dale dale' sin información útil."
    test_transcription = "dale weón ahí hay uno dale dale muerto nice nice rotemos rotemos"
    test_preferences = {
        "coach_type": "Directo",
        "aspect": "Comunicación", 
        "personality": "Competitivo",
        "voice": "es-ES-Chirp3-HD-Charon",
        "voice_label": "Masculina",
        "speed": 1.0,
        "speed_label": "Normal"
    }
    
    try:
        # 1. Guardar un análisis
        print("\n📝 Guardando análisis de ejemplo...")
        analysis_id = dynamodb_manager.save_analysis(
            user_id=test_user_id,
            analysis_text=test_analysis,
            transcription=test_transcription,
            user_preferences=test_preferences
        )
        print(f"✅ Análisis guardado con ID: {analysis_id}")
        
        # 2. Obtener análisis del usuario
        print(f"\n📊 Obteniendo análisis del usuario {test_user_id}...")
        user_analyses = dynamodb_manager.get_user_analyses(test_user_id, limit=5)
        print(f"📈 Encontrados {len(user_analyses)} análisis:")
        for i, analysis in enumerate(user_analyses, 1):
            print(f"  {i}. {analysis.get('timestamp', 'Sin fecha')} - {analysis.get('analysis', '')[:50]}...")
        
        # 3. Obtener estadísticas del usuario
        print(f"\n📊 Estadísticas del usuario {test_user_id}...")
        stats = dynamodb_manager.get_user_stats(test_user_id)
        print("📈 Estadísticas:")
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        
        # 4. Guardar sesión de ejemplo
        print(f"\n🎮 Guardando sesión de ejemplo...")
        session_data = {
            "duration_minutes": 3.5,
            "words_spoken": 45,
            "key_terms_used": ["rotemos", "muerto", "nice"],
            "game_mode": "Search & Destroy",
            "map": "Dust2"
        }
        session_id = dynamodb_manager.save_user_session(test_user_id, session_data)
        print(f"✅ Sesión guardada con ID: {session_id}")
        
        print("\n🎉 ¡Todas las pruebas de DynamoDB pasaron exitosamente!")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        print("⚠️ Asegúrate de que:")
        print("   1. AWS credentials estén configuradas correctamente")
        print("   2. La tabla 'ClutchAnalysis' exista en DynamoDB")
        print("   3. Las variables de entorno estén configuradas en .env")

def example_integration_with_esports():
    """
    Ejemplo de cómo integrar las funciones de DynamoDB en el flujo principal.
    """
    print("\n📝 Ejemplo de integración en esports.py:")
    print("""
# En la función donde se procesa el análisis:
    
try:
    # Después de generar el análisis con GPT
    content = analyze_text(transcribed_text, transcribed_segments, api_key, user_id, analysis_prefs, tts_prefs)
    
    # Guardar en DynamoDB
    analysis_id = dynamodb_manager.save_analysis(
        user_id=user_id,
        analysis_text=content,
        transcription=transcribed_text,
        user_preferences={
            **analysis_prefs,
            **tts_prefs
        }
    )
    
    print(f"✅ Análisis guardado en DynamoDB: {analysis_id}")
    
except Exception as e:
    print(f"⚠️ Error guardando en DynamoDB: {e}")
    # El sistema continúa funcionando aunque falle DynamoDB
""")

if __name__ == "__main__":
    test_dynamodb_connection()
    example_integration_with_esports()
