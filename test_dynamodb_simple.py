"""
Script de prueba simple para verificar que DynamoDB funcione 
con el bot de Discord usando la estructura que propusiste.
"""

from dynamodb_config import save_analysis, dynamodb_manager

def test_simple_save():
    """Prueba la función simple save_analysis"""
    print("🧪 Probando función simple save_analysis...")
    
    # Simular un análisis del bot
    user_id = "123456789"  # ID de Discord del usuario
    s3_key = "audio/test_recording.mp3"  # Clave del archivo en S3
    analysis_text = """
    📊 **Análisis de Comunicación eSports**
    
    **Claridad**: 8/10 - Tu comunicación fue clara y directa
    **Velocidad**: 7/10 - Buena velocidad de comunicación
    **Términos técnicos**: 9/10 - Excelente uso del vocabulario eSports
    
    **Recomendaciones**:
    - Mantén la calma en situaciones de presión
    - Utiliza más callouts específicos de mapa
    
    ¡Excelente trabajo en el análisis de equipo! 🎮
    """
    
    # Guardar el análisis
    analysis_id = save_analysis(user_id, s3_key, analysis_text)
    print(f"✅ Análisis guardado con ID: {analysis_id}")
    
    return analysis_id

def test_manager_save():
    """Prueba el DynamoDBManager con información adicional"""
    print("\n🧪 Probando DynamoDBManager con información adicional...")
    
    analysis_id = dynamodb_manager.save_analysis(
        user_id="987654321",
        analysis_text="Análisis detallado de comunicación en ranked",
        transcription="Enemigo en A, enemigo en A, necesito backup",
        audio_s3_key="audio/ranked_game_001.mp3",
        user_preferences={
            "coach_style": "motivational",
            "voice": "es-ES-Neural2-B",
            "focus_areas": ["teamwork", "callouts"]
        }
    )
    
    print(f"✅ Análisis con información adicional guardado: {analysis_id}")
    return analysis_id

def test_get_user_data():
    """Prueba obtener datos del usuario"""
    print("\n🧪 Probando obtención de datos del usuario...")
    
    # Obtener análisis de un usuario
    user_analyses = dynamodb_manager.get_user_analyses("123456789", limit=5)
    print(f"📊 Análisis encontrados: {len(user_analyses)}")
    
    if user_analyses:
        latest = user_analyses[0]
        print(f"🕒 Último análisis: {latest.get('timestamp')}")
        print(f"📝 Texto (primeros 100 chars): {latest.get('analysis', '')[:100]}...")
    
    # Obtener estadísticas
    stats = dynamodb_manager.get_user_stats("123456789")
    print(f"📊 Estadísticas del usuario: {stats}")

def main():
    """Ejecutar todas las pruebas"""
    print("🚀 Iniciando pruebas de DynamoDB para Clutch eSports")
    print("=" * 60)
    
    try:
        # Probar función simple
        test_simple_save()
        
        # Probar manager completo
        test_manager_save()
        
        # Probar obtención de datos
        test_get_user_data()
        
        print("\n🎉 ¡Todas las pruebas completadas exitosamente!")
        print("✅ DynamoDB está listo para usar con el bot de Discord")
        
    except Exception as e:
        print(f"\n❌ Error durante las pruebas: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
