import requests
import json

# -----------------------------------------------------------------------------
# IMPORTANTE: Reemplaza esta URL con la URL de tu entorno de Elastic Beanstalk
# -----------------------------------------------------------------------------
url = "http://clutch-backend-env.eba-7z3q9wis.us-east-2.elasticbeanstalk.com/guardar-analisis/"
# -----------------------------------------------------------------------------

# Datos de prueba que simulan una solicitud completa
# Usamos un user_id único para identificar fácilmente esta prueba

test_data = {
    "user_id": "test_FINAL_999",
    "analysis_text": "PRUEBA FINAL - Después de actualizar ZIP con force_update.txt",
    "transcription": "Transcripción de la prueba final.",
    "tts_preferences": json.dumps({
        "elevenlabs_voice": "FINAL_TestVoiceId",
        "tts_speed": "FINAL_TestSpeed"
    }),
    "user_personality_test": json.dumps([1,2,3,4,5,6,7,8,9,10])
}

print(f"Enviando petición POST a: {url}")
print("Datos a enviar:")
print(json.dumps(test_data, indent=2))

try:
    # En este caso no enviamos archivos, solo los datos del formulario
    response = requests.post(url, data=test_data)

    print(f"\nCódigo de estado: {response.status_code}")

    if response.status_code == 200:
        print("Respuesta del servidor:")
        print(json.dumps(response.json(), indent=2))
        print("\n✅ ¡Prueba exitosa! Revisa los logs de Elastic Beanstalk y la tabla de DynamoDB.")
        print("   Busca el registro con user_id: 'test_FINAL_999'.")
        print("   Si todos los campos aparecen en user_preferences, el problema está resuelto.")
    else:
        print("❌ La prueba falló.")
        print("Respuesta del servidor (raw):")
        print(response.text)

except requests.exceptions.RequestException as e:
    print(f"\n❌ Error de conexión: No se pudo conectar a {url}")
    print(f"   Asegúrate de que la URL es correcta y el backend está online.")
    print(f"   Error: {e}")

