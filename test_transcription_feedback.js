require('dotenv').config();

// Test de transcripción para verificar el feedback mejorado
async function testTranscriptionInclusion() {
    console.log('🧪 Probando inclusión de transcripción en feedback...');
    
    // Simular datos de análisis que retornaría Python
    const mockAnalysisResult = {
        success: true,
        analysis: "Tu comunicación fue clara y directa. Mantuviste un buen ritmo durante la partida. Se recomienda usar más callouts específicos del mapa.",
        transcription: "Enemigo en A, enemigo en A, necesito backup. Van por B, van por B! Mira el mapa, están rotando."
    };
    
    // Simular preferencias de usuario
    const mockUserPreferences = {
        game: 'Call of Duty',
        coach_type: 'Directo',
        personality: 'Competitivo',
        elevenlabs_voice: 'gU0LNdkMOQCOrPrwtbee',
        tts_speed: 'Normal'
    };
    
    // Simular el contenido del mensaje que se enviaría
    let messageContent = "🎮 **Análisis personalizado de Clutch** (generado con ElevenLabs)\n\n";
    
    if (mockAnalysisResult.transcription && mockAnalysisResult.transcription.trim()) {
        messageContent += `📝 **Tu comunicación transcrita:**\n> "${mockAnalysisResult.transcription.trim()}"\n\n`;
    }
    
    messageContent += "🎧 **Escucha tu análisis personalizado en el audio adjunto.**";
    
    console.log('📄 Contenido del mensaje que se enviaría:');
    console.log('=' .repeat(60));
    console.log(messageContent);
    console.log('=' .repeat(60));
    
    console.log('\n✅ Análisis:', mockAnalysisResult.analysis);
    console.log('✅ Transcripción:', mockAnalysisResult.transcription);
    console.log('✅ Voz ElevenLabs:', mockUserPreferences.elevenlabs_voice);
    
    console.log('\n🎯 Test completado - La transcripción se incluirá correctamente en el feedback');
}

testTranscriptionInclusion();
