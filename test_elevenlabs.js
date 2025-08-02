const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');
const fs = require('fs');

// Test ElevenLabs TTS
async function testElevenLabs() {
    try {
        const elevenlabs = new ElevenLabsClient({
            apiKey: "sk_60199a73c7763bd71453a81136fce2bdc5fbe20f799b27b1"
        });

        console.log('🔊 Probando ElevenLabs TTS...');
          const audioStream = await Promise.race([
            elevenlabs.textToSpeech.convert(
                "gU0LNdkMOQCOrPrwtbee", // voice_id
                {
                    text: "Hola, este es un test de ElevenLabs desde Clutch.",
                    model_id: "eleven_multilingual_v2",
                    output_format: "mp3_44100_128"
                }
            ),
            new Promise((_, reject) => 
                setTimeout(() => reject(new Error('Timeout after 30 seconds')), 30000)
            )
        ]);

        // Convertir stream a buffer
        const chunks = [];
        for await (const chunk of audioStream) {
            chunks.push(chunk);
        }
        
        const audioBuffer = Buffer.concat(chunks);
        
        // Guardar archivo de prueba
        fs.writeFileSync('./test_elevenlabs.mp3', audioBuffer);
        
        console.log(`✅ TTS generado exitosamente: ${audioBuffer.length} bytes`);
        console.log('📁 Archivo guardado como: test_elevenlabs.mp3');
        
    } catch (error) {
        console.error('❌ Error probando ElevenLabs:', error.message);
    }
}

testElevenLabs().then(() => {
    console.log('🔚 Test completado');
    process.exit(0);
}).catch(err => {
    console.error('💥 Error en test:', err);
    process.exit(1);
});
