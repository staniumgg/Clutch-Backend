#!/usr/bin/env python3
"""
Script de prueba para verificar la función de estructuración de análisis.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from esports_processor_simple import structure_analysis

def test_structure_function():
    """Prueba la función de estructuración con un análisis de ejemplo."""
    
    # Análisis de ejemplo (simulando output de GPT-4o-mini)
    sample_analysis = """
    Tu comunicación durante esta partida mostró aspectos positivos y áreas de mejora importantes. 
    Notaste que tu velocidad de respuesta fue buena, pero a veces faltó especificidad en los callouts. 
    Tu coordinación con el equipo fue decente, aunque podrías ser más proactivo en las estrategias. 
    En cuanto a la claridad, se escuchó bien pero algunos términos técnicos no fueron utilizados correctamente. 
    Para mejorar, te sugiero practicar callouts más precisos de ubicaciones, trabajar en la comunicación 
    preventiva antes de que sucedan las jugadas, y estudiar el vocabulario específico del mapa que estás jugando.
    """
    
    print("🧪 Probando función de estructuración de análisis...")
    print(f"📝 Análisis original: {sample_analysis[:100]}...")
    
    try:
        structured = structure_analysis(sample_analysis)
        print("\n✅ Análisis estructurado generado:")
        print("=" * 50)
        print(structured)
        print("=" * 50)
        
        # Verificar que contiene las secciones esperadas
        if '"Aspectos a mejorar":' in structured and '"Cómo mejorarlos":' in structured:
            print("\n✅ Formato correcto detectado!")
            return True
        else:
            print("\n❌ Formato incorrecto - no se encontraron las secciones esperadas")
            return False
            
    except Exception as e:
        print(f"\n❌ Error durante la estructuración: {e}")
        return False

if __name__ == "__main__":
    success = test_structure_function()
    if success:
        print("\n🎉 Prueba exitosa! La función de estructuración está funcionando correctamente.")
    else:
        print("\n💥 Prueba falló. Revisa la implementación.")
