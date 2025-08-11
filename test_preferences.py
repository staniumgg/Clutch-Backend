import sys
sys.path.append('.')
from preferences_manager import save_user_preferences, get_user_preferences, update_user_preferences, delete_user_preferences
import json

def test_preferences():
    """
    Prueba las funciones de gestión de preferencias.
    """
    test_user_id = "test_user_123456789"
    
    print("🧪 === PRUEBA DE FUNCIONES DE PREFERENCIAS ===\n")
    
    # 1. Intentar obtener preferencias que no existen
    print("1️⃣ Buscando preferencias de usuario inexistente...")
    result = get_user_preferences(test_user_id)
    print(f"   Resultado: {result}\n")
    
    # 2. Guardar nuevas preferencias
    print("2️⃣ Guardando nuevas preferencias...")
    tts_prefs = {
        'elevenlabs_voice': 'pPdl9cQBQq4p6mRkZy2Z',
        'tts_speed': 'Normal'
    }
    personality_test = [4, 2, 5, 3, 1, 4, 5, 2, 3, 4]
    profile_id = "E_alto__A_medio__N_bajo__C_alto__O_medio"
    
    save_result = save_user_preferences(test_user_id, tts_prefs, personality_test, profile_id)
    print(f"   Resultado: {save_result}\n")
    
    # 3. Obtener las preferencias guardadas
    print("3️⃣ Obteniendo preferencias guardadas...")
    get_result = get_user_preferences(test_user_id)
    print(f"   Resultado: {json.dumps(get_result, indent=2)}\n")
    
    # 4. Actualizar preferencias
    print("4️⃣ Actualizando velocidad TTS...")
    new_tts_prefs = {
        'elevenlabs_voice': 'pPdl9cQBQq4p6mRkZy2Z',
        'tts_speed': 'Rapida'
    }
    
    update_result = update_user_preferences(test_user_id, tts_preferences=new_tts_prefs)
    print(f"   Resultado: {update_result}\n")
    
    # 5. Verificar actualización
    print("5️⃣ Verificando actualización...")
    get_result2 = get_user_preferences(test_user_id)
    print(f"   Resultado: {json.dumps(get_result2, indent=2)}\n")
    
    # 6. Limpiar - eliminar preferencias de prueba
    print("6️⃣ Eliminando preferencias de prueba...")
    delete_result = delete_user_preferences(test_user_id)
    print(f"   Resultado: {delete_result}\n")
    
    # 7. Verificar eliminación
    print("7️⃣ Verificando eliminación...")
    final_result = get_user_preferences(test_user_id)
    print(f"   Resultado: {final_result}\n")
    
    print("✅ Prueba de preferencias completada!")

if __name__ == "__main__":
    test_preferences()
