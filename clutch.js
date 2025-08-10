require('dotenv').config();
const { Client, GatewayIntentBits, ActionRowBuilder, StringSelectMenuBuilder, ComponentType, ButtonBuilder } = require('discord.js');
const { joinVoiceChannel, getVoiceConnection, EndBehaviorType, VoiceConnectionStatus } = require('@discordjs/voice');
const { entersState } = require('@discordjs/voice');
const { pipeline } = require('node:stream');
const prism = require('prism-media');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');
const { spawn } = require('child_process');
const { ElevenLabsClient } = require('@elevenlabs/elevenlabs-js');

// Set ffmpeg path
ffmpeg.setFfmpegPath("C:\\Users\\paula\\OneDrive\\Documentos\\StaniuM\\ffmpeg-2025-05-15-git-12b853530a-full_build\\bin\\ffmpeg.exe");

require('opusscript');

// Ensure directories exist
if (!fs.existsSync('./recordings')) fs.mkdirSync('./recordings');
if (!fs.existsSync('./temp')) fs.mkdirSync('./temp');

const client = new Client({
    intents: [
        GatewayIntentBits.Guilds,
        GatewayIntentBits.GuildVoiceStates,
        GatewayIntentBits.GuildMessages,
        GatewayIntentBits.MessageContent,
        GatewayIntentBits.GuildMembers
    ]
});

// Objeto para mantener el seguimiento de las grabaciones activas
const activeRecordings = new Map();
const token = process.env.DISCORD_TOKEN;

client.on('error', error => console.error('Discord client error:', error));

client.login(token).catch(error => {
    if (error.code === 'TokenInvalid') {
        console.error('Error: Invalid bot token! Please check your .env file.');
    } else {
        console.error('Failed to login:', error);
    }
});

client.on('ready', () => {
    console.log(`Logged in as ${client.user.tag} - Using ElevenLabs TTS`);
});

client.on('messageCreate', async message => {
    if (message.content === '!record') {
        if (!message.member.voice.channel) {
            return message.reply('¡Necesitas estar en un canal de voz!');
        }

        const existingConnection = getVoiceConnection(message.guild.id);
        if (existingConnection) {
            return message.reply('¡Ya estoy grabando! Usa !stop para detener la grabación.');
        }

        const connection = joinVoiceChannel({
            channelId: message.member.voice.channel.id,
            guildId: message.guild.id,
            adapterCreator: message.guild.voiceAdapterCreator,
            selfDeaf: false,
            selfMute: true
        });

        handleConnectionStatus(connection);
        const receiver = connection.receiver;

        // Iniciar la grabación para todos los usuarios en el canal
        message.member.voice.channel.members.forEach(async (member) => {
            if (!member.user.bot) {
                const user = member.user;
                const userId = user.id;
                const timestamp = Date.now();

                console.log(`🔴 Iniciando grabación para ${user.username}`);

                try {
                    const audioStream = await setupAudioStream(receiver, user, connection);
                    if (!audioStream) {
                        console.error(`❌ No se pudo configurar el stream de audio para ${user.username}`);
                        return;
                    }

                    // Almacenar chunks de PCM en memoria
                    const pcmChunks = [];
                    const decoder = new prism.opus.Decoder({
                        rate: 48000,
                        channels: 2,
                        frameSize: 960
                    });

                    activeRecordings.set(user.id, {
                        pcmChunks: pcmChunks,
                        audioStream: audioStream,
                        decoder: decoder,
                        username: user.username,
                        timestamp: timestamp,
                        stopped: false
                    });

                    // Conectar el pipeline: audioStream -> decoder -> chunks en memoria
                    audioStream.on('data', (chunk) => {
                        try {
                            decoder.write(chunk);
                        } catch (err) {
                            // Ignorar errores de escritura en decoder
                        }
                    });

                    decoder.on('data', (pcmData) => {
                        const recording = activeRecordings.get(user.id);
                        if (recording && !recording.stopped) {
                            recording.pcmChunks.push(pcmData);
                            console.log(`📊 Chunk PCM capturado para ${user.username}: ${pcmData.length} bytes (total: ${recording.pcmChunks.length} chunks)`);
                        }
                    });

                    audioStream.on('end', () => {
                        console.log(`🔇 Stream finalizado para ${user.username}`);
                        try {
                            decoder.end();
                        } catch (err) {
                            // Ignorar errores al cerrar decoder
                        }
                    });

                    audioStream.on('error', (err) => {
                        if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                            // Ignorar este error inicial
                            return;
                        }
                        console.error(`⚠️ Error en stream de audio para ${user.username}:`, err);
                    });

                    decoder.on('error', (err) => {
                        console.log(`⚠️ Error en decoder para ${user.username}:`, err.message);
                    });

                    console.log(`✅ Grabación configurada para ${user.username}`);
                } catch (error) {
                    console.error(`❌ Error general para ${user.username}:`, error);
                }
            }
        });

        message.reply('🎙️ ¡Empezando a grabar! Habla normalmente y usa `!stop` cuando quieras detener la grabación. (Usando ElevenLabs TTS)');
    }

    if (message.content === '!stop') {
        const connection = getVoiceConnection(message.guild.id);
        if (connection) {
            try {
                if (activeRecordings.size === 0) {
                    connection.destroy();
                    return message.reply('❌ No había grabaciones activas para procesar.');
                }

                console.log(`🛑 Comando !stop recibido. Grabaciones activas: ${activeRecordings.size}`);
                await message.reply('⏳ Finalizando grabación y procesando audio con ElevenLabs TTS, por favor espera...');

                // Detener todas las grabaciones
                for (const [userId, recording] of activeRecordings.entries()) {
                    recording.stopped = true;
                    console.log(`🛑 Deteniendo grabación para ${recording.username} - Chunks: ${recording.pcmChunks.length}`);
                    
                    if (recording.audioStream && !recording.audioStream.destroyed) {
                        recording.audioStream.destroy();
                    }
                    
                    try {
                        recording.decoder.end();
                    } catch (err) {
                        // Ignorar errores al cerrar decoder
                    }
                }

                // Destruir conexión
                connection.destroy();

                // Esperar un momento para que se complete la captura
                setTimeout(async () => {
                    console.log(`📊 Iniciando procesamiento de ${activeRecordings.size} grabaciones...`);
                    
                    const processingPromises = [];

                    for (const [userId, recording] of activeRecordings.entries()) {
                        console.log(`📋 Procesando ${recording.username} - ${recording.pcmChunks.length} chunks`);
                        const processPromise = processRecording(userId, recording, message);
                        processingPromises.push(processPromise);
                    }

                    const results = await Promise.allSettled(processingPromises);
                    
                    results.forEach((result, index) => {
                        const recording = Array.from(activeRecordings.values())[index];
                        if (result.status === 'rejected') {
                            console.error(`❌ Error procesando ${recording.username}:`, result.reason);
                        } else {
                            console.log(`✅ Procesamiento exitoso para ${recording.username}`);
                        }
                    });

                    activeRecordings.clear();
                    console.log("✅ Procesamiento completo.");
                    await message.channel.send("✅ ¡Análisis completo con ElevenLabs! Revisa tus mensajes directos para ver el feedback.");
                }, 2000);

            } catch (error) {
                console.error('❌ Error en el comando !stop:', error);
                message.reply('❌ Ocurrió un error al detener la grabación.');
                if (connection) connection.destroy();
                activeRecordings.clear();
            }
        } else {
            message.reply('❌ No estoy grabando en este servidor.');
        }
    }
});

async function processRecording(userId, recording, message) {
    try {
        const pcmBuffer = Buffer.concat(recording.pcmChunks);
        console.log(`✅ Procesando ${recording.username}. PCM bytes: ${pcmBuffer.length}`);

        if (pcmBuffer.length === 0) {
            console.log(`❌ No se grabó audio para ${recording.username}.`);
            return;
        }

        // Convertir PCM a MP3
        const mp3Buffer = await convertPcmToMp3(pcmBuffer);
        if (!mp3Buffer || mp3Buffer.length === 0) {
            throw new Error('La conversión a MP3 falló.');
        }

        console.log(`🎵 MP3 generado para ${recording.username}: ${mp3Buffer.length} bytes`);        
          // Procesar con preferencias del usuario
        const userPreferences = await collectUserPreferences(userId, message);
        console.log(`🐛 DEBUG: Preferencias obtenidas en processRecording:`, JSON.stringify(userPreferences, null, 2));
        
        const analysisResult = await spawnPythonAndAnalyze(mp3Buffer, recording.username, userId, recording.timestamp, userPreferences);
        if (analysisResult.analysis) {
            const { analysis, structured_analysis, transcription, wpm, wpm_by_segment } = analysisResult;
            await sendFeedbackToUser(
                userId, 
                analysis, 
                userPreferences, 
                transcription,
                structured_analysis,
                mp3Buffer, // Pasar el buffer del audio del jugador
                recording.username,
                recording.timestamp
            );
        } else {
            throw new Error('No se recibió análisis del script de Python');
        }

    } catch (error) {
        console.error(`❌ Error procesando ${recording.username}:`, error);
        throw error;
    }
}

async function convertPcmToMp3(pcmBuffer) {
    return new Promise((resolve, reject) => {
        const tempDir = path.join(__dirname, 'temp');
        const tempPcmFile = path.join(tempDir, `temp_${Date.now()}.pcm`);
        const tempMp3File = path.join(tempDir, `temp_${Date.now()}.mp3`);
        
        try {
            // Escribir PCM a archivo temporal
            fs.writeFileSync(tempPcmFile, pcmBuffer);
            console.log(`🔧 PCM temporal creado: ${tempPcmFile} (${pcmBuffer.length} bytes)`);
            
            ffmpeg(tempPcmFile)
                .inputFormat('s16le')
                .inputOptions(['-ar 48000', '-ac 2'])
                .audioCodec('libmp3lame')
                .audioBitrate('128k')
                .audioFrequency(48000)
                .audioChannels(2)
                .format('mp3')
                .on('start', (commandLine) => {
                    console.log('🎵 FFmpeg iniciado:', commandLine);
                })
                .on('error', (err) => {
                    console.error('❌ Error de FFMPEG:', err.message);
                    // Limpiar archivos temporales
                    try {
                        if (fs.existsSync(tempPcmFile)) fs.unlinkSync(tempPcmFile);
                        if (fs.existsSync(tempMp3File)) fs.unlinkSync(tempMp3File);
                    } catch (e) {}
                    reject(err);
                })
                .on('end', () => {
                    try {
                        console.log("✅ Conversión a MP3 finalizada.");
                        
                        // Leer el archivo MP3 resultante
                        if (fs.existsSync(tempMp3File)) {
                            const mp3Buffer = fs.readFileSync(tempMp3File);
                            console.log(`🎵 MP3 generado: ${mp3Buffer.length} bytes`);
                            
                            // Limpiar archivos temporales
                            fs.unlinkSync(tempPcmFile);
                            fs.unlinkSync(tempMp3File);
                            
                            resolve(mp3Buffer);
                        } else {
                            throw new Error('El archivo MP3 no fue creado');
                        }
                    } catch (error) {
                        console.error('❌ Error leyendo MP3 resultante:', error);
                        reject(error);
                    }
                })
                .save(tempMp3File);
                
        } catch (error) {
            console.error('❌ Error en conversión PCM->MP3:', error);
            // Limpiar archivos temporales
            try {
                if (fs.existsSync(tempPcmFile)) fs.unlinkSync(tempPcmFile);
                if (fs.existsSync(tempMp3File)) fs.unlinkSync(tempMp3File);
            } catch (e) {}
            reject(error);
        }
    });
}

async function spawnPythonAndAnalyze(audioBuffer, username, userId, timestamp, userPreferences) {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [
            './esports_processor_simple.py',
            userId,
            username,
            timestamp,
            JSON.stringify(userPreferences)
        ], { stdio: ['pipe', 'pipe', 'pipe'], encoding: 'utf-8' });

        let stdoutData = '';
        let stderrData = '';

        pythonProcess.stdin.write(audioBuffer);
        pythonProcess.stdin.end();

        pythonProcess.stdout.on('data', (data) => {
            stdoutData += data.toString('utf-8');
        });

        pythonProcess.stderr.on('data', (data) => {
            stderrData += data.toString('utf-8');
            console.error(`[PYTHON_STDERR] ${data.toString('utf-8')}`);
        });

        pythonProcess.on('close', (code) => {
            if (code === 0) {
                try {
                    const result = JSON.parse(stdoutData);
                    if (result.error) {
                        reject(new Error(`Error from Python script: ${result.error}`));
                    } else {
                        resolve(result);
                    }
                } catch (e) {
                    console.error("Raw stdout from Python:", stdoutData);
                    reject(new Error('Failed to parse JSON from Python script.'));
                }
            } else {
                console.error("Raw stderr from Python:", stderrData);
                reject(new Error(`Python script exited with code ${code}. Stderr: ${stderrData}`));
            }
        });

        pythonProcess.on('error', (err) => {
            reject(new Error(`Failed to start Python script: ${err.message}`));
        });
    });
}

async function collectUserPreferences(userId, message) {
    try {
        const user = await client.users.fetch(userId);
        const dmChannel = await user.createDM();

        // --- Personality/Scale Questions ---
        const personalityQuestions = [
            'Me resulta fácil iniciar conversaciones con personas que no conozco.',
            'Prefiero escuchar antes que hablar en la mayoría de las situaciones.',
            'Me esfuerzo por ser amable y considerado, incluso en desacuerdos.',
            'Cuando algo no sale como quiero, tiendo a reaccionar de forma brusca o directa.',
            'Me mantengo calmado y enfocado en situaciones de presión.',
            'Me pongo nervioso o frustrado con facilidad cuando hay tensión.',
            'Me gusta planificar y organizar antes de actuar.',
            'A menudo actúo de manera improvisada y sin plan previo.',
            'Disfruto probar ideas o formas nuevas de hacer las cosas.',
            'Prefiero seguir los métodos que ya conozco en lugar de cambiar.'
        ];

        // Solo recolectar TTS y personality test
        const tts_preferences = {};
        const user_personality_test = [];

        // Ask personality questions one by one with buttons
        for (let i = 0; i < personalityQuestions.length; i++) {
            let answered = false;
            let selectedNum = null;
            while (!answered) {
                const buttonRow = new ActionRowBuilder()
                    .addComponents(
                        [1,2,3,4,5].map(num =>
                            new ButtonBuilder()
                                .setCustomId(`personality_scale_${i}_${num}`)
                                .setLabel(`${num}`)
                                .setStyle(selectedNum === num ? 'Primary' : 'Secondary')
                                .setDisabled(answered)
                        )
                    );

                let sentMsg;
                if (!answered) {
                    sentMsg = await dmChannel.send({
                        content: `Pregunta ${i + 1}/10:\n${personalityQuestions[i]}`,
                        components: [buttonRow]
                    });
                } else {
                    await sentMsg.edit({
                        content: `Pregunta ${i + 1}/10:\n${personalityQuestions[i]}`,
                        components: [buttonRow]
                    });
                }

                const selection = await dmChannel.awaitMessageComponent({
                    componentType: ComponentType.Button,
                    time: 120000
                }).catch(() => null);

                if (selection && selection.customId) {
                    selectedNum = parseInt(selection.customId.split('_')[3]);
                    user_personality_test.push(selectedNum);
                    answered = true;
                    await selection.deferUpdate();
                    // Editar el mensaje para mostrar el botón seleccionado en morado (Primary) y los demás en gris
                    const buttonRowFinal = new ActionRowBuilder()
                        .addComponents(
                            [1,2,3,4,5].map(num =>
                                new ButtonBuilder()
                                    .setCustomId(`personality_scale_${i}_${num}`)
                                    .setLabel(`${num}`)
                                    .setStyle(num === selectedNum ? 'Primary' : 'Secondary')
                                    .setDisabled(true)
                            )
                        );
                    await sentMsg.edit({
                        content: `Pregunta ${i + 1}/10:\n${personalityQuestions[i]}`,
                        components: [buttonRowFinal]
                    });
                } else {
                    user_personality_test.push(null);
                    answered = true;
                }
            }
        }

        // Paso 1: Selección de voz ElevenLabs
        const voiceRow = new ActionRowBuilder()
            .addComponents(
                new StringSelectMenuBuilder()
                    .setCustomId('elevenlabs_voice_select')
                    .setPlaceholder('Selecciona la voz de ElevenLabs')
                    .addOptions([
                        { label: 'Coach Tierna', value: 'pPdl9cQBQq4p6mRkZy2Z', description: 'Voz femenina profesional y clara' },
                        { label: 'Historiador Antiguo', value: '5egO01tkUjEzu7xSSE8M', description: 'Voz masculina sabia y experimentada' },
                        { label: 'Coach Chileno', value: '0cheeVA5B3Cv6DGq65cT', description: 'Voz masculina latina y amigable' },
                        { label: 'Coach Villana', value: 'flHkNRp1BlvT73UL6gyz', description: 'Voz tranquila y relajante' },
                        { label: 'Sargento WWII', value: 'DGzg6RaUqxGRTHSBjfgF', description: 'Voz autoritaria y militar' }
                    ])
            );

        const preferencesEmbed = {
            color: 0x0099ff,
            title: '🎮 Configuración de Preferencias de Audio (ElevenLabs)',
            description: 'Solo necesito saber tu voz preferida y la velocidad del audio para personalizar tu análisis.',
            fields: [
                {
                    name: '¿Qué configuraremos?',
                    value: '• Voz de ElevenLabs\n• Velocidad del audio',
                    inline: false
                }
            ],
            footer: {
                text: 'Esto solo toma 1 minuto y mejorará tu feedback con ElevenLabs.'
            }
        };

        const preferencesMessage = await dmChannel.send({
            embeds: [preferencesEmbed],
            components: [voiceRow]
        });

        // Paso 2: Voz
        const voiceSelection = await dmChannel.awaitMessageComponent({
            componentType: ComponentType.StringSelect,
            time: 120000
        }).catch(() => null);

        if (voiceSelection && voiceSelection.customId === 'elevenlabs_voice_select') {
            const selectedVoice = voiceSelection.values[0];
            tts_preferences.elevenlabs_voice = selectedVoice;
            await voiceSelection.deferUpdate();
        } else {
            tts_preferences.elevenlabs_voice = 'gU0LNdkMOQCOrPrwtbee'; // Default
        }

        // Paso 3: Velocidad
        const speedRow = new ActionRowBuilder()
            .addComponents(
                new StringSelectMenuBuilder()
                    .setCustomId('tts_speed_select')
                    .setPlaceholder('Selecciona la velocidad del audio')
                    .addOptions([
                        { label: 'Lenta (0.85x)', value: 'Lenta', description: 'Velocidad más pausada para mejor comprensión' },
                        { label: 'Normal (1.0x)', value: 'Normal', description: 'Velocidad estándar de conversación' },
                        { label: 'Rápida (1.15x)', value: 'Rapida', description: 'Velocidad acelerada para análisis rápido' }
                    ])
            );

        await dmChannel.send({
            embeds: [{
                color: 0x0099ff,
                title: 'Selecciona la velocidad del audio',
                description: '¿Prefieres el análisis en audio lento, normal o rápido?'
            }],
            components: [speedRow]
        });

        const speedSelection = await dmChannel.awaitMessageComponent({
            componentType: ComponentType.StringSelect,
            time: 120000
        }).catch(() => null);

        if (speedSelection && speedSelection.customId === 'tts_speed_select') {
            const selectedSpeed = speedSelection.values[0];
            tts_preferences.tts_speed = selectedSpeed;
            await speedSelection.deferUpdate();
        } else {
            tts_preferences.tts_speed = 'Normal'; // Default
        }

        // Confirmación final
        await dmChannel.send({
            embeds: [{
                color: 0x00ff00,
                title: '✅ Preferencias Configuradas',
                description: '¡Tus preferencias han sido guardadas! Tu análisis será personalizado con ElevenLabs TTS.',
                fields: [
                    { name: 'Voz ElevenLabs', value: tts_preferences.elevenlabs_voice, inline: true },
                    { name: 'Velocidad TTS', value: tts_preferences.tts_speed, inline: true },
                    { name: 'Respuestas de personalidad', value: user_personality_test.join(', '), inline: false }
                ]
            }],
            components: []
        });

        // Guardar preferencias
        await saveUserPreferences(userId, { tts_preferences, user_personality_test });
        console.log(`🐛 DEBUG: Preferencias finales recolectadas:`, JSON.stringify({ tts_preferences, user_personality_test }, null, 2));
        return { tts_preferences, user_personality_test };
    } catch (error) {
        console.error(`❌ Error recolectando preferencias para ${userId}:`, error);
        return { tts_preferences: { elevenlabs_voice: 'gU0LNdkMOQCOrPrwtbee', tts_speed: 'Normal' }, user_personality_test: [3,3,3,3,3,3,3,3,3,3] };
    }
}

function getDefaultPreferencesElevenLabs() {
    return {
        tts_preferences: {
            elevenlabs_voice: 'gU0LNdkMOQCOrPrwtbee',
            tts_speed: 'Normal'
        },
        user_personality_test: [3,3,3,3,3,3,3,3,3,3]
    };
}

// Solo se envía el análisis una vez, después de recolectar todas las preferencias y generar el audio
async function sendFeedbackToUser(userId, analysis, userPreferences = null, transcription = null, structuredAnalysis = null, playerAudioBuffer = null, username = null, timestamp = null) {
    try {
        const user = await client.users.fetch(userId);
        const dmChannel = await user.createDM();

        // Usar preferencias de ElevenLabs o defaults
        const elevenLabsVoice = userPreferences?.elevenlabs_voice || 'gU0LNdkMOQCOrPrwtbee';
        const ttsSpeed = userPreferences?.tts_speed || 'Normal';

        console.log(`🔊 Generando TTS con ElevenLabs para ${user.username}`);
        console.log(`🎤 Voz: ${elevenLabsVoice}, Velocidad: ${ttsSpeed}`);

        // 1. Enviar análisis estructurado (si está disponible)
        if (structuredAnalysis && structuredAnalysis.trim()) {
            const structuredMessage = `**Resumen Estructurado de tu Análisis**\n\n${structuredAnalysis}`;
            await dmChannel.send(structuredMessage);
            console.log(`✅ Análisis estructurado enviado a ${user.username}`);
        }

        // 2. Enviar análisis completo como texto
        const textMessage = `🎮 **Tu Análisis Completo de Clutch**\n\n${analysis}\n\n🎧 **También tienes este análisis en audio:**`;
        await dmChannel.send(textMessage);

        // 3. Generar TTS del análisis completo con ElevenLabs
        let ttsAudioBuffer;
        if (process.env.TESTING === 'true') {
            // Generar un audio MP3 de 1 segundo de silencio para testing
            const silentBuffer = Buffer.alloc(44100 * 2, 0); // 1 segundo, 44100Hz, 16-bit mono
            ttsAudioBuffer = silentBuffer;
        } else {
            ttsAudioBuffer = await generateTTSElevenLabs(analysis, elevenLabsVoice, ttsSpeed);
        }

        // 4. Enviar el archivo de audio
        await dmChannel.send({
            files: [{
                attachment: ttsAudioBuffer,
                name: 'Clutch Analysis ElevenLabs.mp3'
            }]
        });

        // 5. Enviar a FastAPI SOLO aquí, con todas las preferencias
        console.log(`🐛 DEBUG: Preferencias que se van a enviar a FastAPI:`, JSON.stringify(userPreferences, null, 2));
        await sendToFastAPI(userId, analysis, transcription, userPreferences, playerAudioBuffer, ttsAudioBuffer, user.username, timestamp);

        console.log(`✅ Feedback completo con ElevenLabs enviado a ${user.username} (estructurado + texto + audio)`);

    } catch (error) {
        console.error(`❌ Error enviando feedback a ${userId}:`, error);
    }
}

async function sendToFastAPI(userId, analysis, transcription, userPreferences, playerAudioBuffer, coachAudioBuffer, username, timestamp) {    try {
        // userPreferences = { tts_preferences, user_personality_test }
        console.log(`📤 Enviando datos a FastAPI para ${username}`);
        console.log(`📋 Preferencias completas:`, JSON.stringify(userPreferences, null, 2));
        const FormData = require('form-data');
        const form = new FormData();
        // Datos principales
        form.append('user_id', userId);
        form.append('analysis_text', analysis);
        form.append('transcription', transcription);
        // Preferencias TTS
        form.append('tts_preferences', JSON.stringify(userPreferences.tts_preferences));
        // Test de personalidad
        form.append('user_personality_test', JSON.stringify(userPreferences.user_personality_test));
        // Archivos de audio
        if (playerAudioBuffer) {
            form.append('player_audio', playerAudioBuffer, {
                filename: `player_${username}_${timestamp}.mp3`,
                contentType: 'audio/mpeg'
            });
        }
        if (coachAudioBuffer) {
            form.append('coach_audio', coachAudioBuffer, {
                filename: `coach_${username}_${timestamp}.mp3`,
                contentType: 'audio/mpeg'
            });
        }
        // Enviar a tu API FastAPI
        const fetch = require('node-fetch');
        const response = await fetch('http://clutch-backend-env.eba-7z3q9wis.us-east-2.elasticbeanstalk.com/guardar-analisis/', {
            method: 'POST',
            body: form,
            headers: form.getHeaders()
        });
        const result = await response.json();
        if (result && result.echo_tts_preferences) {
            console.log('🧩 Echo tts_preferences desde backend:', JSON.stringify(result.echo_tts_preferences, null, 2));
        }
        if (result && result.echo_user_personality_test) {
            console.log('🧩 Echo user_personality_test desde backend:', JSON.stringify(result.echo_user_personality_test, null, 2));
        }
        if (result.success) {
            console.log(`✅ Datos enviados correctamente a FastAPI. Analysis ID: ${result.analysis_id}`);
            console.log(`🔗 Player audio URL: ${result.player_s3_url || 'No disponible'}`);
            console.log(`🔗 Coach audio URL: ${result.coach_s3_url || 'No disponible'}`);
        } else {
            console.error(`❌ Error en FastAPI: ${result.error}`);
        }
        return result;
    } catch (error) {
        console.error(`❌ Error enviando a FastAPI para ${username}:`, error);
        return { success: false, error: error.message };
    }
}

async function generateTTSElevenLabs(text, voiceId, speedLabel) {
    try {
        const elevenlabs = new ElevenLabsClient({
            apiKey: "sk_60199a73c7763bd71453a81136fce2bdc5fbe20f799b27b1"
        });

        console.log(`🔊 Iniciando generación TTS con ElevenLabs...`);
        console.log(`📝 Texto: ${text.substring(0, 100)}...`);
        console.log(`🎤 Voice ID: ${voiceId}`);
        
        // Mapear velocidad a valor numérico
        let stabilityValue = 0.5;
        let similarityBoostValue = 0.8;
        
        if (speedLabel === 'Lenta') {
            stabilityValue = 0.7;
            similarityBoostValue = 0.9;
        } else if (speedLabel === 'Rapida') {
            stabilityValue = 0.3;
            similarityBoostValue = 0.7;
        }

        const audioStream = await elevenlabs.textToSpeech.convert(
            voiceId,
            {
                text: text,
                model_id: "eleven_turbo_v2",
                output_format: "mp3_44100_128",
                voice_settings: {
                    stability: stabilityValue,
                    similarity_boost: similarityBoostValue,
                    style: 0.0,
                    use_speaker_boost: true
                }
            }
        );

        // Convertir stream a buffer
        const chunks = [];
        for await (const chunk of audioStream) {
            chunks.push(chunk);
        }
        
        const audioBuffer = Buffer.concat(chunks);
        console.log(`✅ TTS generado con ElevenLabs: ${audioBuffer.length} bytes`);
        
        return audioBuffer;
        
    } catch (error) {
        console.error('❌ Error en la API de ElevenLabs:', error);
        
        // Fallback: crear un archivo de texto si falla el TTS
        const fallbackText = `Error generando audio TTS: ${error.message}\n\nAnálisis original:\n${text}`;
        return Buffer.from(fallbackText, 'utf-8');
    }
}

function handleConnectionStatus(connection) {
    connection.on(VoiceConnectionStatus.Ready, () => {
        console.log('✅ Conexión de voz lista.');
    });

    connection.on(VoiceConnectionStatus.Disconnected, async (oldState, newState) => {
        try {
            await Promise.race([
                entersState(connection, VoiceConnectionStatus.Signalling, 5000),
                entersState(connection, VoiceConnectionStatus.Connecting, 5000),
            ]);
        } catch (error) {
            console.log('⚠️ Conexión de voz desconectada permanentemente.');
            if (connection.state.status !== VoiceConnectionStatus.Destroyed) {
                connection.destroy();
            }
        }
    });
}

async function setupAudioStream(receiver, user, connection, retryCount = 0) {
    if (retryCount >= 3) {
        console.error(`❌ Máximo número de reintentos alcanzado para ${user.username}`);
        return null;
    }

    try {
        // Verificar el estado de la conexión
        if (connection.state.status !== VoiceConnectionStatus.Ready) {
            console.log(`⏳ Esperando conexión lista para ${user.username}...`);
            await entersState(connection, VoiceConnectionStatus.Ready, 5_000);
        }

        const audioStream = receiver.subscribe(user.id, {
            end: {
                behavior: EndBehaviorType.Manual // Solo se detiene manualmente
            }
        });

        let hasData = false;
        let dataTimeout;

        const resetDataTimeout = () => {
            clearTimeout(dataTimeout);
            dataTimeout = setTimeout(() => {
                if (!hasData) {
                    console.log(`⏰ No se detectó audio para ${user.username} en 30 segundos, pero continuando...`);
                }
            }, 30000);
        };

        resetDataTimeout();

        audioStream.on('data', () => {
            hasData = true;
            resetDataTimeout();
            if (!audioStream.destroyed) {
                audioStream.resume();
            }
        });

        audioStream.on('end', () => {
            clearTimeout(dataTimeout);
            console.log(`🔚 Stream finalizado normalmente para ${user.username}`);
        });

        audioStream.on('close', () => {
            clearTimeout(dataTimeout);
            console.log(`🔒 Stream cerrado para ${user.username}`);
        });

        audioStream.on('error', async (err) => {
            clearTimeout(dataTimeout);
            
            if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                console.log(`🔄 Reintentando stream para ${user.username}...`);
                const newStream = await setupAudioStream(receiver, user, connection, retryCount + 1);
                if (newStream) {
                    return newStream;
                }
            } else {
                console.error(`⚠️ Error en stream de audio para ${user.username}:`, err);
            }
        });

        return audioStream;
    } catch (error) {
        console.error(`❌ Error configurando stream para ${user.username}:`, error);
        if (retryCount < 3) {
            console.log(`🔄 Reintentando configuración de stream para ${user.username}...`);
            await new Promise(resolve => setTimeout(resolve, 1000));
            return setupAudioStream(receiver, user, connection, retryCount + 1);
        }
        return null;
    }
}
