// Test completo de la funcionalidad PDF del bot Discord
const { spawn } = require('child_process');

// Simular la función generateAnalysisPDF del bot
async function generateAnalysisPDF(analysis, structuredAnalysis, username, userId) {
    return new Promise((resolve) => {
        try {
            // Datos para enviar al script Python
            const pdfData = {
                analysis_text: analysis,
                structured_analysis: structuredAnalysis || '',
                username: username,
                user_id: userId
            };
            
            console.log(`📄 Generando PDF del análisis para ${username}...`);
            
            const pythonProcess = spawn('python', ['pdf_generator.py'], {
                stdio: ['pipe', 'pipe', 'pipe']
            });
            
            let pdfBuffer = Buffer.alloc(0);
            let errorOutput = '';
            
            // Enviar datos JSON al script Python
            pythonProcess.stdin.write(JSON.stringify(pdfData));
            pythonProcess.stdin.end();
            
            // Recopilar salida del PDF (bytes)
            pythonProcess.stdout.on('data', (data) => {
                pdfBuffer = Buffer.concat([pdfBuffer, data]);
            });
            
            // Recopilar errores
            pythonProcess.stderr.on('data', (data) => {
                errorOutput += data.toString();
            });
            
            pythonProcess.on('close', (code) => {
                if (code === 0 && pdfBuffer.length > 0) {
                    console.log(`✅ PDF generado exitosamente: ${pdfBuffer.length} bytes`);
                    console.log(`📋 Información del proceso:`, errorOutput.trim());
                    resolve(pdfBuffer);
                } else {
                    console.error(`❌ Error generando PDF (código ${code}):`, errorOutput);
                    resolve(null);
                }
            });
            
            pythonProcess.on('error', (error) => {
                console.error('❌ Error ejecutando Python para PDF:', error);
                resolve(null);
            });
            
        } catch (error) {
            console.error('❌ Error en generateAnalysisPDF:', error);
            resolve(null);
        }
    });
}

async function testPDFGeneration() {
    console.log('🧪 === PRUEBA DE GENERACIÓN DE PDF ===\n');
    
    // Datos de prueba que simulan un análisis real
    const testData = {
        analysis: `He observado tu comunicación en la partida. El "no, no, no" sugiere frustración o desacuerdo. Es importante que, en esos momentos, intentes comunicar lo que está sucediendo o qué necesitas. Un callout específico puede ayudar a tu equipo en lugar de solo expresar descontento. Recuerda que tu voz es clave para el éxito del equipo. Sigue trabajando en eso, y verás cómo mejora la coordinación.`,
        
        structuredAnalysis: `"Aspectos a mejorar":

- Evitar expresiones de frustración como "no, no, no".
- Proporcionar información clara sobre la situación del juego.
- Realizar callouts específicos en lugar de solo expresar descontento.

"Cómo mejorarlos":

- Practica formular frases que describan lo que está sucediendo, como "estoy siendo atacado por el flanco derecho".
- Utiliza un sistema de comunicación que incluya ubicaciones y acciones, como "necesito apoyo en la zona A".
- Mantén un tono positivo y enfocado en soluciones, por ejemplo, "vamos a reagruparnos y atacar juntos".`,
        
        username: 'TestGamer123',
        userId: '987654321'
    };
    
    // Generar PDF
    const pdfBuffer = await generateAnalysisPDF(
        testData.analysis,
        testData.structuredAnalysis,
        testData.username,
        testData.userId
    );
    
    if (pdfBuffer) {
        // Guardar PDF de prueba
        const fs = require('fs');
        const filename = `test_analysis_${testData.username}.pdf`;
        fs.writeFileSync(filename, pdfBuffer);
        
        console.log(`\n✅ Prueba exitosa!`);
        console.log(`📄 PDF guardado como: ${filename}`);
        console.log(`📊 Tamaño del archivo: ${pdfBuffer.length} bytes`);
        console.log(`🎯 El archivo está listo para ser enviado por Discord`);
        
        // Simular envío por Discord
        console.log(`\n📤 Simulando envío por Discord...`);
        console.log(`📁 Archivo adjunto: ${filename}`);
        console.log(`👤 Destinatario: ${testData.username} (${testData.userId})`);
        console.log(`✅ ¡PDF enviado exitosamente!`);
        
    } else {
        console.log(`\n❌ Falló la generación del PDF`);
        console.log(`🔄 En producción se usaría fallback a texto`);
    }
}

// Ejecutar la prueba
testPDFGeneration().catch(console.error);
