"""
Script de prueba para verificar la integración completa:
Audio local → S3 → DynamoDB
"""

from dynamodb_config import save_analysis_with_audio
import os

def test_complete_integration():
    """Prueba la integración completa con un archivo real."""
    
    print("🧪 Probando integración completa: Local → S3 → DynamoDB")
    print("=" * 60)
    
    # Buscar un archivo de audio existente
    recordings_dir = "recordings"
    audio_files = [f for f in os.listdir(recordings_dir) if f.endswith('.mp3')]
    
    if not audio_files:
        print("❌ No se encontraron archivos de audio en recordings/")
        return
    
    # Usar el primer archivo encontrado
    audio_file = audio_files[0]
    audio_path = os.path.join(recordings_dir, audio_file)
    
    print(f"📁 Archivo seleccionado: {audio_file}")
    print(f"📏 Tamaño: {os.path.getsize(audio_path) / 1024:.1f} KB")
    
    # Extraer user_id del nombre del archivo
    try:
        user_id = audio_file.split('-')[1]
        print(f"👤 Usuario extraído: {user_id}")
    except:
        user_id = "test_user_123"
        print(f"👤 Usuario por defecto: {user_id}")
    
    # Simular un análisis
    analysis_text = f"""
📊 **Análisis de Comunicación eSports - Prueba de Integración**

**Archivo procesado**: {audio_file}
**Timestamp**: {audio_file.split('-')[-1].replace('.mp3', '')}

**Evaluación técnica**:
• Claridad: 8/10 - Comunicación clara durante el gameplay
• Términos técnicos: 9/10 - Buen uso de callouts específicos 
• Timing: 7/10 - Información oportuna en momentos clave

**Recomendaciones**:
• Mantener la consistencia en callouts de posición
• Reducir ruido de fondo para mejor claridad
• Excellent trabajo en comunicación de equipo

🎯 **Resultado**: Nivel de comunicación competitivo alcanzado
"""
    
    print(f"\n🤖 Simulando análisis de GPT...")
    print(f"📝 Longitud del análisis: {len(analysis_text)} caracteres")
    
    # Ejecutar integración completa
    print(f"\n🚀 Iniciando proceso completo...")
    result = save_analysis_with_audio(user_id, audio_path, analysis_text)
    
    # Mostrar resultados
    print(f"\n📊 RESULTADOS:")
    print(f"   • Audio subido a S3: {'✅' if result['audio_uploaded'] else '❌'}")
    print(f"   • Análisis guardado en DynamoDB: {'✅' if result['analysis_saved'] else '❌'}")
    print(f"   • S3 Key: {result['s3_key']}")
    print(f"   • Analysis ID: {result['analysis_id']}")
    
    if result['audio_uploaded'] and result['analysis_saved']:
        print(f"\n🎉 ¡Integración completa exitosa!")
        print(f"✅ El archivo está ahora disponible en la nube de AWS")
        
        # Mostrar cómo consultar los datos después
        print(f"\n📖 Para consultar este análisis después:")
        print(f"   from dynamodb_config import dynamodb_manager")
        print(f"   analyses = dynamodb_manager.get_user_analyses('{user_id}')")
        print(f"   print(analyses[0])  # Último análisis")
        
    else:
        print(f"\n⚠️ Integración parcial - revisar configuración")

def test_with_existing_files():
    """Muestra los archivos disponibles para prueba."""
    
    print("📁 Archivos de audio disponibles para prueba:")
    print("=" * 50)
    
    recordings_dir = "recordings"
    if not os.path.exists(recordings_dir):
        print("❌ Carpeta recordings/ no encontrada")
        return
    
    audio_files = [f for f in os.listdir(recordings_dir) if f.endswith('.mp3')]
    
    if not audio_files:
        print("❌ No hay archivos .mp3 en recordings/")
        return
    
    for i, file in enumerate(audio_files, 1):
        file_path = os.path.join(recordings_dir, file)
        size_kb = os.path.getsize(file_path) / 1024
        try:
            user_id = file.split('-')[1]
            timestamp = file.split('-')[-1].replace('.mp3', '')
        except:
            user_id = "unknown"
            timestamp = "unknown"
        
        print(f"{i}. {file}")
        print(f"   👤 Usuario: {user_id}")
        print(f"   📅 Timestamp: {timestamp}")
        print(f"   📏 Tamaño: {size_kb:.1f} KB")
        print()

if __name__ == "__main__":
    print("🎮 Clutch eSports - Prueba de Integración S3 + DynamoDB")
    print()
    
    # Mostrar archivos disponibles
    test_with_existing_files()
    
    # Preguntar si continuar
    proceed = input("¿Ejecutar prueba de integración completa? (y/n): ").lower().strip()
    
    if proceed == 'y':
        test_complete_integration()
    else:
        print("❌ Prueba cancelada")
        print("💡 Ejecuta 'python setup_s3.py' primero para configurar S3")
