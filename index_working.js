require('dotenv').config();
const { Client, GatewayIntentBits, ActionRowBuilder, StringSelectMenuBuilder, ComponentType } = require('discord.js');
const { joinVoiceChannel, getVoiceConnection, EndBehaviorType, VoiceConnectionStatus } = require('@discordjs/voice');
const { entersState } = require('@discordjs/voice');
const { pipeline } = require('node:stream');
const prism = require('prism-media');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');
const { spawn } = require('child_process');

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
    console.log(`Logged in as ${client.user.tag}`);
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

        message.reply('🎙️ ¡Empezando a grabar! Habla normalmente y usa `!stop` cuando quieras detener la grabación.');
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
                await message.reply('⏳ Finalizando grabación y procesando audio, por favor espera...');

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
                    await message.channel.send("✅ ¡Análisis completo! Revisa tus mensajes directos para ver el feedback.");
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

        console.log(`🎵 MP3 generado para ${recording.username}: ${mp3Buffer.length} bytes`);        // Procesar con preferencias del usuario
        const userPreferences = await collectUserPreferences(userId, message);
        const analysisResult = await spawnPythonAndAnalyze(mp3Buffer, recording.username, userId, recording.timestamp);
        
        if (analysisResult.analysis) {
            await sendFeedbackToUser(userId, analysisResult.analysis, userPreferences);
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

async function spawnPythonAndAnalyze(audioBuffer, username, userId, timestamp) {
    return new Promise((resolve, reject) => {
        const pythonProcess = spawn('python', [
            './esports_processor_simple.py',
            userId,
            username,
            timestamp
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
        const dmChannel = await user.createDM();        // Crear menú de selección
        const gameRow = new ActionRowBuilder()
            .addComponents(
                new StringSelectMenuBuilder()
                    .setCustomId('game_select')
                    .setPlaceholder('Selecciona tu juego principal')
                    .addOptions([
                        { label: 'Call of Duty', value: 'Call of Duty', emoji: '🔫' },
                        { label: 'Valorant', value: 'Valorant', emoji: '⚡' },
                        { label: 'Counter-Strike 2', value: 'Counter-Strike 2', emoji: '💥' },
                        { label: 'Apex Legends', value: 'Apex Legends', emoji: '🏆' },
                        { label: 'Overwatch 2', value: 'Overwatch 2', emoji: '🎯' }
                    ])
            );const preferencesEmbed = {
            color: 0x0099ff,
            title: '🎮 Configuración de Preferencias de Coaching',
            description: 'Para darte el mejor análisis personalizado, necesito conocer tus preferencias:',
            fields: [
                {
                    name: '🎯 ¿Qué configuraremos?',
                    value: '• Juego principal\n• Estilo de coaching\n• Aspecto a mejorar\n• Personalidad de juego\n• Nivel de experiencia\n• Objetivo principal\n• Voz del audio\n• Velocidad del audio',
                    inline: false
                }
            ],
            footer: {
                text: 'Esto solo toma 3 minutos y mejorará mucho tu feedback'
            }
        };

        const preferencesMessage = await dmChannel.send({
            embeds: [preferencesEmbed],
            components: [gameRow]
        });

        const preferences = { userId: userId };        // Recolectar preferencias paso a paso
        const steps = [
            {
                id: 'game_select',
                options: [
                    { label: 'Call of Duty', value: 'Call of Duty' },
                    { label: 'Valorant', value: 'Valorant' },
                    { label: 'Counter-Strike 2', value: 'Counter-Strike 2' },
                    { label: 'Apex Legends', value: 'Apex Legends' },
                    { label: 'Overwatch 2', value: 'Overwatch 2' }
                ],
                key: 'game',
                nextStep: 'coach_type_select'
            },
            {
                id: 'coach_type_select',
                options: [
                    { label: 'Directo y específico', value: 'Directo' },
                    { label: 'Motivacional y positivo', value: 'Motivacional' },
                    { label: 'Analítico y detallado', value: 'Analitico' },
                    { label: 'Amigable y constructivo', value: 'Amigable' }
                ],
                key: 'coach_type',
                nextStep: 'aspect_select'
            },
            {
                id: 'aspect_select',
                options: [
                    { label: 'Comunicación en equipo', value: 'Comunicacion' },
                    { label: 'Estrategia y táctica', value: 'Estrategia' },
                    { label: 'Mecánicas de juego', value: 'Mecanicas' },
                    { label: 'Liderazgo', value: 'Liderazgo' },
                    { label: 'Coordinación', value: 'Coordinacion' }
                ],
                key: 'aspect',
                nextStep: 'personality_select'
            },
            {
                id: 'personality_select',
                options: [
                    { label: 'Competitivo e intenso', value: 'Competitivo' },
                    { label: 'Relajado y casual', value: 'Relajado' },
                    { label: 'Estratégico y analítico', value: 'Estrategico' },
                    { label: 'Social y comunicativo', value: 'Social' }
                ],
                key: 'personality',
                nextStep: 'experience_select'
            },
            {
                id: 'experience_select',
                options: [
                    { label: 'Principiante', value: 'Principiante' },
                    { label: 'Intermedio', value: 'Intermedio' },
                    { label: 'Avanzado', value: 'Avanzado' },
                    { label: 'Profesional/Semi-pro', value: 'Profesional' }
                ],
                key: 'experience',
                nextStep: 'goal_select'
            },
            {
                id: 'goal_select',
                options: [
                    { label: 'Ganar más partidas', value: 'Ganar más partidas' },
                    { label: 'Mejorar comunicación', value: 'Mejorar comunicación' },
                    { label: 'Subir de rango', value: 'Subir de rango' },
                    { label: 'Jugar profesionalmente', value: 'Jugar profesionalmente' },
                    { label: 'Divertirme más', value: 'Divertirme más' }
                ],
                key: 'goal',
                nextStep: 'tts_voice_select'
            },
            {
                id: 'tts_voice_select',
                options: [
                    { label: 'Voz Masculina Estándar', value: 'es-ES-Standard-B' },
                    { label: 'Voz Femenina Estándar', value: 'es-ES-Standard-A' },
                    { label: 'Voz Masculina Neural', value: 'es-ES-Neural2-B' },
                    { label: 'Voz Femenina Neural', value: 'es-ES-Neural2-A' },
                    { label: 'Voz Masculina Wavenet', value: 'es-ES-Wavenet-B' },
                    { label: 'Voz Femenina Wavenet', value: 'es-ES-Wavenet-A' }
                ],
                key: 'tts_voice',
                nextStep: 'tts_speed_select'
            },
            {
                id: 'tts_speed_select',
                options: [
                    { label: 'Lenta (0.85x)', value: 'Lenta' },
                    { label: 'Normal (1.0x)', value: 'Normal' },
                    { label: 'Rápida (1.15x)', value: 'Rapida' }
                ],
                key: 'tts_speed',
                nextStep: null
            }
        ];

        let currentStepIndex = 0;

        return new Promise((resolve) => {
            const collector = dmChannel.createMessageComponentCollector({
                componentType: ComponentType.StringSelect,
                time: 300000 // 5 minutos
            });            collector.on('collect', async (interaction) => {
                const currentStep = steps[currentStepIndex];
                
                if (interaction.customId === currentStep.id) {
                    const selectedValue = interaction.values[0];
                    const selectedOption = currentStep.options.find(opt => opt.value === selectedValue);
                    
                    if (!selectedOption) {
                        console.error(`❌ Opción no encontrada: ${selectedValue}`);
                        return;
                    }
                    
                    preferences[currentStep.key] = selectedOption.value;
                    
                    await interaction.deferUpdate();
                    
                    currentStepIndex++;
                    
                    if (currentStepIndex < steps.length) {
                        // Mostrar siguiente paso
                        const nextStep = steps[currentStepIndex];
                        const nextRow = new ActionRowBuilder()
                            .addComponents(
                                new StringSelectMenuBuilder()
                                    .setCustomId(nextStep.id)
                                    .setPlaceholder(`Selecciona tu ${getStepLabel(nextStep.key)}`)
                                    .addOptions(nextStep.options.map(opt => ({
                                        label: opt.label,
                                        value: opt.value
                                    })))
                            );

                        await interaction.editReply({
                            embeds: [{
                                ...preferencesEmbed,
                                description: `✅ ${selectedOption.label} seleccionado\n\nPaso ${currentStepIndex + 1}/${steps.length}:`
                            }],
                            components: [nextRow]
                        });
                    } else {
                        // Completado
                        await interaction.editReply({
                            embeds: [{
                                color: 0x00ff00,
                                title: '✅ Preferencias Configuradas',
                                description: 'Perfecto! Tus preferencias han sido guardadas. Tu análisis será personalizado según estos ajustes.',
                                fields: [
                                    { name: 'Juego', value: preferences.game, inline: true },
                                    { name: 'Estilo de Coach', value: preferences.coach_type, inline: true },
                                    { name: 'Aspecto Principal', value: preferences.aspect, inline: true },
                                    { name: 'Personalidad', value: preferences.personality, inline: true },
                                    { name: 'Experiencia', value: preferences.experience, inline: true },
                                    { name: 'Objetivo', value: preferences.goal, inline: true },
                                    { name: 'Voz TTS', value: preferences.tts_voice, inline: true },
                                    { name: 'Velocidad TTS', value: preferences.tts_speed, inline: true }
                                ]
                            }],
                            components: []
                        });

                        // Guardar preferencias
                        await saveUserPreferences(userId, preferences);
                        collector.stop();
                        resolve(preferences);
                    }
                }
            });

            collector.on('end', () => {
                if (currentStepIndex < steps.length) {
                    // Si no completó, usar defaults
                    resolve(getDefaultPreferences());
                }
            });
        });

    } catch (error) {
        console.error(`❌ Error recolectando preferencias para ${userId}:`, error);
        return getDefaultPreferences();
    }
}

function getStepLabel(key) {
    const labels = {
        game: 'juego',
        coach_type: 'estilo de coaching',
        aspect: 'aspecto a mejorar',
        personality: 'personalidad de juego',
        experience: 'nivel de experiencia',
        goal: 'objetivo principal',
        tts_voice: 'voz para el audio',
        tts_speed: 'velocidad del audio'
    };
    return labels[key] || key;
}

async function saveUserPreferences(userId, preferences) {
    try {
        const fs = require('fs');
        let existingPrefs = {};
        
        if (fs.existsSync('user_preferences.json')) {
            const data = fs.readFileSync('user_preferences.json', 'utf8');
            existingPrefs = JSON.parse(data);
        }
        
        existingPrefs[userId] = preferences;
        
        fs.writeFileSync('user_preferences.json', JSON.stringify(existingPrefs, null, 2));
        console.log(`✅ Preferencias guardadas para usuario ${userId}`);
    } catch (error) {
        console.error(`❌ Error guardando preferencias:`, error);
    }
}

function getDefaultPreferences() {
    return {
        game: 'Call of Duty',
        coach_type: 'Directo',
        aspect: 'Comunicacion',
        personality: 'Competitivo',
        experience: 'Intermedio',
        goal: 'Ganar más partidas',
        tts_voice: 'es-ES-Standard-B',
        tts_speed: 'Normal'
    };
}

async function sendFeedbackToUser(userId, analysis, userPreferences = null) {
    try {
        const user = await client.users.fetch(userId);
        const dmChannel = await user.createDM();

        // Usar preferencias de TTS o defaults
        const ttsVoice = userPreferences?.tts_voice || 'es-ES-Standard-B';
        const ttsSpeed = userPreferences?.tts_speed || 'Normal';

        // Generar TTS del análisis
        const ttsAudioBuffer = await generateTTS(analysis, ttsVoice, ttsSpeed);

        await dmChannel.send({
            content: "🎮 Aquí tienes tu análisis personalizado de Clutch:",
            files: [{
                attachment: ttsAudioBuffer,
                name: 'Clutch_Analysis.mp3'
            }]
        });

        console.log(`✅ Feedback enviado a ${user.username}`);

    } catch (error) {
        console.error(`❌ Error enviando feedback a ${userId}:`, error);
    }
}

async function generateTTS(text, voiceName, speedLabel) {
    const { TextToSpeechClient } = require('@google-cloud/text-to-speech');
    const ttsClient = new TextToSpeechClient();

    let speed = 1.0;
    if (speedLabel === 'Lenta') speed = 0.85;
    if (speedLabel === 'Rapida') speed = 1.15;

    const request = {
        input: { text: text },
        voice: { languageCode: 'es-ES', name: voiceName },
        audioConfig: { audioEncoding: 'MP3', speakingRate: speed },
    };

    try {
        const [response] = await ttsClient.synthesizeSpeech(request);
        return response.audioContent;
    } catch (error) {
        console.error('❌ Error en la API de Google TTS:', error);
        throw error;
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
