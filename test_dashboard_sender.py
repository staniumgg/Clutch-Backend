import requests
import time

def enviar_a_dashboard(data, url):
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        print("¡Datos enviados correctamente al dashboard!")
    except Exception as e:
        print(f"Error enviando datos al dashboard: {e}")

if __name__ == "__main__":
    dashboard_url = "http://localhost:3001/data"
    ejemplo = {
        "transcripcion": "Esto es una transcripción de prueba para el dashboard.",
        "segmentos": [
            {"start": 0, "end": 2, "text": "Hola equipo, atentos al objetivo."},
            {"start": 2, "end": 5, "text": "Rotamos a dragón en 10 segundos."}
        ],
        "analisis": {
            "analisis_general": {
                "comunicaciones_duplicadas": False,
                "comunicaciones_parasitas": False,
                "claridad_callouts": "alta",
                "relevancia_estrategica": "alta",
                "impacto_emocional": "positivo",
                "urgencia_y_timing": "adecuado"
            },
            "segmentos": [
                {
                    "timestamp": "001-002",
                    "estado_emocional": "concentración",
                    "estilo_comunicacional": "constructivo",
                    "impacto_equipo": "beneficioso",
                    "resumen_emocional": "equipo enfocado",
                    "palabras_clave": ["objetivo", "dragón"],
                    "frecuencia_palabras": 2
                }
            ],
            "temperatura_voz": "media",
            "gritos": False,
            "nivel_estres": "bajo",
            "sugerencias": [
                "Mantener la comunicación clara y precisa"
            ],
            "palabras_clave": ["objetivo", "dragón"],
            "resumen_emocional": "El equipo muestra buena coordinación y enfoque en el objetivo."
        },
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    enviar_a_dashboard(ejemplo, dashboard_url)
