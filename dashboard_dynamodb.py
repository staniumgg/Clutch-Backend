"""
Dashboard simple para visualizar datos de DynamoDB del proyecto Clutch.
Ejecutar este script para ver estadísticas y análisis guardados.
"""

from dynamodb_config import dynamodb_manager
import json
from datetime import datetime, timedelta

def show_user_dashboard(user_id):
    """
    Muestra un dashboard completo para un usuario específico.
    """
    print(f"\n🎮 Dashboard para Usuario: {user_id}")
    print("=" * 60)
    
    # Estadísticas generales
    stats = dynamodb_manager.get_user_stats(user_id)
    print(f"📊 ESTADÍSTICAS GENERALES:")
    print(f"   Total de análisis: {stats.get('total_analyses', 0)}")
    print(f"   Análisis esta semana: {stats.get('analyses_this_week', 0)}")
    print(f"   Análisis este mes: {stats.get('analyses_this_month', 0)}")
    
    if stats.get('first_analysis'):
        first_date = stats['first_analysis'][:10]  # Solo la fecha
        print(f"   Primer análisis: {first_date}")
    
    if stats.get('latest_analysis'):
        latest_date = stats['latest_analysis'][:10]  # Solo la fecha
        print(f"   Último análisis: {latest_date}")
    
    # Análisis recientes
    print(f"\n📝 ÚLTIMOS ANÁLISIS:")
    analyses = dynamodb_manager.get_user_analyses(user_id, limit=5)
    
    if not analyses:
        print("   No hay análisis disponibles.")
        return
    
    for i, analysis in enumerate(analyses, 1):
        date = analysis.get('timestamp', '')[:10]  # Solo la fecha
        text = analysis.get('analysis', '')[:80] + "..." if len(analysis.get('analysis', '')) > 80 else analysis.get('analysis', '')
        print(f"   {i}. [{date}] {text}")
    
    # Preferencias del usuario
    if analyses and 'user_preferences' in analyses[0]:
        prefs = analyses[0]['user_preferences']
        print(f"\n⚙️ PREFERENCIAS ACTUALES:")
        print(f"   Coach: {prefs.get('coach_type', 'No definido')}")
        print(f"   Aspecto a mejorar: {prefs.get('aspect', 'No definido')}")
        print(f"   Personalidad: {prefs.get('personality', 'No definido')}")
        print(f"   Voz TTS: {prefs.get('voice_label', 'No definido')}")
        print(f"   Velocidad: {prefs.get('speed_label', 'No definido')}")

def show_global_stats():
    """
    Muestra estadísticas globales de todos los usuarios.
    """
    print(f"\n🌍 ESTADÍSTICAS GLOBALES")
    print("=" * 40)
    
    # Obtener datos de algunos usuarios para estadísticas globales
    # (En una implementación real, tendrías una función específica para esto)
    try:
        # Esto es un ejemplo - en producción necesitarías una consulta scan optimizada
        print("📊 Datos disponibles por usuario:")
        
        # Simular algunos usuarios comunes
        sample_users = ["123456789", "987654321", "555666777"]
        total_analyses = 0
        active_users = 0
        
        for user_id in sample_users:
            user_analyses = dynamodb_manager.get_user_analyses(user_id, limit=1)
            if user_analyses:
                active_users += 1
                stats = dynamodb_manager.get_user_stats(user_id)
                user_total = stats.get('total_analyses', 0)
                total_analyses += user_total
                print(f"   Usuario {user_id}: {user_total} análisis")
        
        print(f"\n📈 RESUMEN:")
        print(f"   Usuarios activos: {active_users}")
        print(f"   Total análisis: {total_analyses}")
        
        if active_users > 0:
            avg_analyses = total_analyses / active_users
            print(f"   Promedio por usuario: {avg_analyses:.1f}")
            
    except Exception as e:
        print(f"⚠️ Error obteniendo estadísticas globales: {e}")

def show_recent_activity():
    """
    Muestra actividad reciente en el sistema.
    """
    print(f"\n⏰ ACTIVIDAD RECIENTE")
    print("=" * 30)
    
    # Obtener análisis recientes de varios usuarios
    sample_users = ["123456789", "987654321", "555666777"]
    all_recent = []
    
    for user_id in sample_users:
        user_analyses = dynamodb_manager.get_user_analyses(user_id, limit=3)
        for analysis in user_analyses:
            analysis['display_user'] = f"Usuario-{user_id[-3:]}"  # Solo últimos 3 dígitos
            all_recent.append(analysis)
    
    # Ordenar por timestamp
    all_recent.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    print("🕐 Últimos análisis del sistema:")
    for i, analysis in enumerate(all_recent[:10], 1):
        date = analysis.get('timestamp', '')[:16]  # Fecha y hora
        user = analysis.get('display_user', 'Usuario desconocido')
        text = analysis.get('analysis', '')[:50] + "..." if len(analysis.get('analysis', '')) > 50 else analysis.get('analysis', '')
        print(f"   {i}. [{date}] {user}: {text}")

def interactive_dashboard():
    """
    Dashboard interactivo que permite al usuario elegir qué ver.
    """
    while True:
        print(f"\n🎮 CLUTCH ANALYTICS DASHBOARD")
        print("=" * 35)
        print("1. Ver dashboard de usuario específico")
        print("2. Ver estadísticas globales")
        print("3. Ver actividad reciente")
        print("4. Probar conexión DynamoDB")
        print("5. Salir")
        
        choice = input("\nElige una opción (1-5): ").strip()
        
        if choice == "1":
            user_id = input("Ingresa el User ID: ").strip()
            if user_id:
                show_user_dashboard(user_id)
            else:
                print("❌ User ID no válido")
                
        elif choice == "2":
            show_global_stats()
            
        elif choice == "3":
            show_recent_activity()
            
        elif choice == "4":
            test_dynamodb_connection()
            
        elif choice == "5":
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción no válida")

def test_dynamodb_connection():
    """
    Prueba rápida de conexión a DynamoDB.
    """
    print(f"\n🧪 PRUEBA DE CONEXIÓN")
    print("=" * 25)
    
    try:
        # Intentar obtener stats de un usuario de prueba
        stats = dynamodb_manager.get_user_stats("test_user")
        print("✅ Conexión a DynamoDB exitosa")
        print(f"📊 Respuesta de prueba: {stats}")
        
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        print("🔧 Verifica:")
        print("   1. Variables de entorno en .env")
        print("   2. Credenciales de AWS")
        print("   3. Tabla DynamoDB creada")

if __name__ == "__main__":
    print("🎮 Clutch Analytics Dashboard")
    print("Visualiza datos de análisis de comunicación eSports")
    
    # Verificar si hay datos de ejemplo
    print("\n🔍 Verificando datos disponibles...")
    test_stats = dynamodb_manager.get_user_stats("123456789")
    
    if test_stats.get('total_analyses', 0) == 0:
        print("ℹ️ No hay datos de ejemplo. Ejecuta 'python test_dynamodb.py' primero.")
    
    # Iniciar dashboard interactivo
    interactive_dashboard()
