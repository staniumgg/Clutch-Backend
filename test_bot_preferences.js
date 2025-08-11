# filepath: c:\Users\paula\CLUTCH\test_bot_preferences.js
// Test rápido de las funciones de preferencias del bot Discord
const { spawn } = require('child_process');

// Función para obtener preferencias del usuario desde DynamoDB
async function getUserPreferencesFromDB(userId) {
    return new Promise((resolve) => {
        const pythonProcess = spawn('python', [
            '-c',
            `
import sys
sys.path.append('.')
from preferences_manager import get_user_preferences
result = get_user_preferences('${userId}')
print(result)
            `
        ], { stdio: ['pipe', 'pipe', 'pipe'] });

        let stdoutData = '';
        let stderrData = '';

        pythonProcess.stdout.on('data', (data) => {
            stdoutData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            stderrData += data.toString();
        });

        pythonProcess.on('close', (code) => {
            try {
                if (code === 0 && stdoutData.trim()) {
                    const result = JSON.parse(stdoutData.trim());
                    resolve(result);
                } else {
                    resolve({ success: false, error: 'No preferences found' });
                }
            } catch (e) {
                console.error('Error parsing preferences result:', e);
                resolve({ success: false, error: 'Parse error' });
            }
        });
    });
}

// Función para guardar preferencias del usuario en DynamoDB
async function saveUserPreferencesToDB(userId, tts_preferences, user_personality_test, profile_id) {
    return new Promise((resolve) => {
        const pythonProcess = spawn('python', [
            '-c',
            `
import sys
sys.path.append('.')
from preferences_manager import save_user_preferences
import json

tts_prefs = json.loads('${JSON.stringify(tts_preferences).replace(/'/g, "\\'")}')
personality_test = json.loads('${JSON.stringify(user_personality_test)}')
result = save_user_preferences('${userId}', tts_prefs, personality_test, '${profile_id || ''}')
print(result)
            `
        ], { stdio: ['pipe', 'pipe', 'pipe'] });

        let stdoutData = '';
        let stderrData = '';

        pythonProcess.stdout.on('data', (data) => {
            stdoutData += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            stderrData += data.toString();
        });

        pythonProcess.on('close', (code) => {
            try {
                if (code === 0 && stdoutData.trim()) {
                    const result = JSON.parse(stdoutData.trim());
                    resolve(result);
                } else {
                    resolve({ success: false, error: 'Save failed' });
                }
            } catch (e) {
                console.error('Error parsing save result:', e);
                resolve({ success: false, error: 'Parse error' });
            }
        });
    });
}

// Función para calcular profile_id desde user_personality_test
function calculateProfileId(answers) {
    // Preguntas invertidas: 2,4,6,8,10 (índices 1,3,5,7,9)
    const invert_indices = [1,3,5,7,9];
    const scores = [];
    
    for (let i = 0; i < answers.length; i++) {
        const val = answers[i];
        if (invert_indices.includes(i)) {
            scores.push(6 - val);
        } else {
            scores.push(val);
        }
    }
    
    // Rasgos: E(0,1), A(2,3), N(4,5), C(6,7), O(8,9)
    const traits = {
        'E': (scores[0] + scores[1]) / 2,
        'A': (scores[2] + scores[3]) / 2,
        'N': (scores[4] + scores[5]) / 2,
        'C': (scores[6] + scores[7]) / 2,
        'O': (scores[8] + scores[9]) / 2
    };
    
    function label(val) {
        if (val >= 4.0) return 'alto';
        else if (val <= 2.5) return 'bajo';
        else return 'medio';
    }
    
    const profile_id = Object.entries(traits)
        .map(([k, v]) => `${k}_${label(v)}`)
        .join('__');
    
    return profile_id;
}

async function testPreferences() {
    console.log('🧪 === PRUEBA DE FUNCIONES DEL BOT ===\n');
    
    const testUserId = 'bot_test_789';
    
    // 1. Verificar si hay preferencias existentes
    console.log('1️⃣ Verificando preferencias existentes...');
    const existingPrefs = await getUserPreferencesFromDB(testUserId);
    console.log('   Resultado:', existingPrefs);
    
    // 2. Crear nuevas preferencias
    console.log('\n2️⃣ Creando nuevas preferencias...');
    const tts_preferences = {
        elevenlabs_voice: 'pPdl9cQBQq4p6mRkZy2Z',
        tts_speed: 'Normal'
    };
    const user_personality_test = [4, 2, 5, 3, 1, 4, 5, 2, 3, 4];
    const profile_id = calculateProfileId(user_personality_test);
    
    console.log('   Profile ID calculado:', profile_id);
    
    // 3. Guardar preferencias
    console.log('\n3️⃣ Guardando preferencias...');
    const saveResult = await saveUserPreferencesToDB(testUserId, tts_preferences, user_personality_test, profile_id);
    console.log('   Resultado:', saveResult);
    
    // 4. Obtener preferencias guardadas
    console.log('\n4️⃣ Obteniendo preferencias guardadas...');
    const getResult = await getUserPreferencesFromDB(testUserId);
    console.log('   Resultado:', JSON.stringify(getResult, null, 2));
    
    console.log('\n✅ Prueba completada!');
}

// Ejecutar la prueba
testPreferences().catch(console.error);
