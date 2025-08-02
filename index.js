require('dotenv').config();
const { Client, GatewayIntentBits, ActionRowBuilder, StringSelectMenuBuilder, ComponentType } = require('discord.js');
const { joinVoiceChannel, getVoiceConnection, createAudioPlayer, createAudioResource, EndBehaviorType, VoiceConnectionStatus } = require('@discordjs/voice');
const { entersState } = require('@discordjs/voice');
const { pipeline } = require('node:stream');
const prism = require('prism-media');
const fs = require('fs');
const path = require('path');
const ffmpeg = require('fluent-ffmpeg');

// Set ffmpeg path
ffmpeg.setFfmpegPath("C:\\Users\\paula\\OneDrive\\Documentos\\StaniuM\\ffmpeg-2025-05-15-git-12b853530a-full_build\\bin\\ffmpeg.exe");

require('opusscript');

// Ensure recordings directory exists
if (!fs.existsSync('./recordings')) {
    fs.mkdirSync('./recordings');
}

if (!fs.existsSync('./temp')) {
    fs.mkdirSync('./temp');
}

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

// Add error handling for client login
client.on('error', error => {
    console.error('Discord client error:', error);
});

client.login(token).catch(error => {
    if (error.code === 'TokenInvalid') {
        console.error('Error: Invalid bot token! Please check your .env file.');
        console.log('Make sure:');
        console.log('1. Your .env file exists');
        console.log('2. It contains DISCORD_TOKEN=your_token_here');
        console.log('3. The token is copied correctly from Discord Developer Portal');
    } else {
        console.error('Failed to login:', error);
    }
});

client.on('ready', () => {
    console.log(`Logged in as ${client.user.tag}`);
});

client.on('messageCreate', async message => {
    if (message.content === '!test-analysis') {
        // Comando de prueba para verificar el análisis automático
        const testFiles = [
            'recordings/callmestanium-1106372321582784603-1753726167810.mp3',
            'recordings/callmestanium-1106372321582784603-1753727037228.mp3'
        ];
        
        let foundFile = null;
        for (const file of testFiles) {
            const fullPath = path.join(__dirname, file);
            if (fs.existsSync(fullPath)) {
                foundFile = fullPath;
                break;
            }
        }
        
        if (!foundFile) {
            return message.reply('❌ No se encontraron archivos de audio para probar');
        }
        
        await message.reply(`🧪 Probando análisis automático con: ${path.basename(foundFile)}`);
        
        try {
            const result = await analyzeAudio(foundFile);
            await message.reply(`✅ Prueba completada exitosamente!\n📊 User ID: ${result.user_id}\n🎯 Coach: ${result.coach_type}\n📝 Aspecto: ${result.aspect}`);
        } catch (error) {
            await message.reply(`❌ Error en la prueba: ${error.message}`);
        }
    }

    if (message.content === '!record') {
        // Check if user is in a voice channel
        if (!message.member.voice.channel) {
            return message.reply('¡Necesitas estar en un canal de voz!');
        }

        // Check if bot is already recording in this guild
        const existingConnection = getVoiceConnection(message.guild.id);
        if (existingConnection) {
            return message.reply('¡Ya estoy grabando! Usa !stop para detener la grabación.');
        }        const connection = joinVoiceChannel({
            channelId: message.member.voice.channel.id,
            guildId: message.guild.id,
            adapterCreator: message.guild.voiceAdapterCreator,
            selfDeaf: false,
            selfMute: true // Para que aparezca como muteado
        });

        handleConnectionStatus(connection);
        
        // Wait for connection to be ready before setting up audio streams
        connection.on(VoiceConnectionStatus.Ready, () => {
            console.log('Conexión de voz lista, configurando streams de audio...');
            const receiver = connection.receiver;

            // Small delay to ensure everything is ready
            setTimeout(() => {
                // Iniciar la grabación para todos los usuarios en el canal
                message.member.voice.channel.members.forEach(async (member) => {
                    if (!member.user.bot) {  // No grabar bots
                        const user = member.user;
                        try {
                            // Setup stream and store it
                            setupAudioStream(receiver, user, connection);
                            console.log(`🔴 Iniciando grabación para ${user.username}`);
                        } catch (error) {
                            console.error(`Error iniciando grabación para ${user.username}:`, error);
                        }
                    }
                });
            }, 1000); // 1 second delay
        });

        message.reply('¡Empezando a grabar! Usa !stop cuando quieras detener la grabación.');
    }

    if (message.content === '!stop') {
        const connection = getVoiceConnection(message.guild.id);
        if (connection) {
            try {
                if (activeRecordings.size === 0) {
                    connection.destroy();
                    return message.reply('No había grabaciones activas para procesar.');
                }

                await message.reply('Finalizando grabación, un momento por favor...');

                const processingPromises = [];
                  // Iterate over active recordings and trigger processing
                for (const [userId, recording] of activeRecordings.entries()) {
                    const { audioStream, decoder, user } = recording;

                    const processPromise = new Promise((resolve, reject) => {
                        let processCompleted = false;
                        
                        // Set up timeout to prevent hanging promises
                        const timeout = setTimeout(() => {
                            if (!processCompleted) {
                                processCompleted = true;
                                reject(new Error(`Timeout processing ${user.username}`));
                            }
                        }, 30000); // 30 second timeout

                        // This event listener will resolve the promise once the stream is fully processed
                        const handleEnd = async () => {
                            if (processCompleted) return;
                            processCompleted = true;
                            clearTimeout(timeout);
                            
                            try {
                                const pcmBuffer = Buffer.concat(recording.pcmChunks);
                                console.log(`✅ Stream finalizado para ${user.username}. PCM bytes: ${pcmBuffer.length}`);

                                if (pcmBuffer.length === 0) {
                                    console.log(`No se grabó audio para ${user.username}.`);
                                    resolve(); // Resolve without error if no audio
                                    return;
                                }

                                const mp3Buffer = await convertPcmToMp3(pcmBuffer);
                                if (!mp3Buffer || mp3Buffer.length === 0) {
                                    throw new Error('La conversión a MP3 falló.');
                                }

                                const [preferencesResult, analysisResult] = await Promise.allSettled([
                                    collectUserPreferences(userId, message),
                                    spawnPythonAndAnalyze(mp3Buffer, user)
                                ]);

                                let userPreferences;
                                if (preferencesResult.status === 'fulfilled') {
                                    userPreferences = preferencesResult.value;
                                } else {
                                    console.error(`⚠️ Error en preferencias para ${user.username}: ${preferencesResult.reason}. Usando defaults.`);
                                    userPreferences = getDefaultPreferences();
                                }

                                if (analysisResult.status === 'fulfilled') {
                                    const { analysis } = analysisResult.value;
                                    await sendFeedbackToUser(userId, analysis, userPreferences);
                                } else {
                                    throw new Error(`Análisis de Python falló: ${analysisResult.reason.message}`);
                                }
                                resolve();
                            } catch (error) {
                                console.error(`❌ Error procesando para ${user.username}:`, error);
                                reject(error);
                            }
                        };

                        // Attach the event listener first
                        decoder.once('end', handleEnd);
                        
                        // Add error handling for premature close
                        decoder.once('error', (err) => {
                            if (processCompleted) return;
                            processCompleted = true;
                            clearTimeout(timeout);
                            
                            if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                                console.log(`⚠️ Stream cerrado prematuramente para ${user.username}, procesando datos disponibles...`);
                                handleEnd(); // Try to process anyway
                            } else {
                                console.error(`❌ Error en stream para ${user.username}:`, err);
                                reject(err);
                            }
                        });

                        // Small delay before destroying to ensure event listeners are attached
                        setTimeout(() => {
                            try {
                                // Manually destroy the stream to trigger the 'end' event on the decoder
                                audioStream.destroy();
                            } catch (err) {
                                console.error(`Error destroying stream for ${user.username}:`, err);
                                if (!processCompleted) {
                                    processCompleted = true;
                                    clearTimeout(timeout);
                                    handleEnd(); // Try to process anyway
                                }
                            }
                        }, 10);
                    });
                    
                    processingPromises.push(processPromise);
                }

                // Wait for all processing to complete
                const results = await Promise.allSettled(processingPromises);
                
                results.forEach(result => {
                    if (result.status === 'rejected') {
                        console.error("Uno de los procesos de grabación falló:", result.reason);
                    }
                });

                // Clean up and disconnect
                activeRecordings.clear();
                connection.destroy();
                console.log("✅ Procesamiento completo. Conexión cerrada.");
                await message.channel.send("✅ ¡Análisis completo! Revisa tus mensajes directos para ver el feedback.");

            } catch (error) {
                console.error('Error en el comando !stop:', error);
                message.reply('Ocurrió un error al detener la grabación.');
                if (connection) connection.destroy();
                activeRecordings.clear();
            }
        } else {
            message.reply('No estoy grabando en este servidor.');
        }
    }
});

const { spawn } = require('child_process');

// Función para recopilar preferencias del usuario con menús desplegables
async function collectUserPreferences(userId, message) {
    console.log(`👤 Iniciando recopilación de preferencias para usuario: ${userId}`);
    const user = await client.users.fetch(userId);
    if (!user) {
        throw new Error(`No se pudo encontrar usuario con ID: ${userId}`);
    }

    try {
        const dmChannel = await user.createDM();
        const preferences = {};

        // Dividir los menús en dos grupos
        const preferenceMenus1 = [
            {
                customId: 'game',
                placeholder: '🎮 Elige el juego que analizaremos',
                options: [
                    { label: 'Call Of Duty: Black Ops 6', value: 'BlackOps6' },
                    { label: 'Call Of Duty: Warzone', value: 'Warzone' },
                    { label: 'Valorant', value: 'Valorant' },
                    { label: 'Fortnite', value: 'Fortnite' },
                ],
            },
            {
                customId: 'coach_type',
                placeholder: '🎯 Elige tu tipo de coach',
                options: [
                    { label: 'Directo', description: 'Feedback específico y directo al grano', value: 'Directo' },
                    { label: 'Motivacional', description: 'Enfoque positivo y motivador', value: 'Motivacional' },
                    { label: 'Detallado', description: 'Análisis profundo con ejemplos específicos', value: 'Detallado' },
                    { label: 'Analítico', description: 'Datos y estadísticas detalladas', value: 'Analítico' },
                    { label: 'Casual', description: 'Feedback relajado y amigable', value: 'Casual' },
                ],
            },
            {
                customId: 'aspect',
                placeholder: '📊 Elige el aspecto a mejorar',
                options: [
                    { label: 'Comunicación', description: 'Callouts, claridad y timing', value: 'Comunicacion' },
                    { label: 'Posicionamiento', description: 'Posiciones estratégicas y rotaciones', value: 'Posicionamiento' },
                    { label: 'Precisión', description: 'Información específica y útil', value: 'Precision' },
                    { label: 'Liderazgo', description: 'Coordinación y toma de decisiones', value: 'Liderazgo' },
                    { label: 'Estrategia', description: 'Planificación táctica avanzada', value: 'Estrategia' },
                ],
            },
            {
                customId: 'personality',
                placeholder: '🧠 Elige tu tipo de personalidad',
                options: [
                    { label: 'Introvertido', description: 'Feedback constructivo y no agresivo', value: 'Introvertido' },
                    { label: 'Extrovertido', description: 'Feedback directo y energético', value: 'Extrovertido' },
                    { label: 'Competitivo', description: 'Enfoque en performance competitiva', value: 'Competitivo' },
                    { label: 'Colaborativo', description: 'Enfoque en trabajo en equipo', value: 'Colaborativo' },
                    { label: 'Independiente', description: 'Mejoras para juego individual', value: 'Independiente' },
                ],
            },
        ];

        const preferenceMenus2 = [
            {
                customId: 'experience',
                placeholder: '📈 Elige tu nivel de experiencia',
                options: [
                    { label: 'Principiante', description: 'Conceptos básicos y fundamentos', value: 'Principiante' },
                    { label: 'Intermedio', description: 'Estrategias y tácticas intermedias', value: 'Intermedio' },
                    { label: 'Avanzado', description: 'Análisis detallado y optimización', value: 'Avanzado' },
                    { label: 'Competitivo', description: 'Enfoque en rendimiento de alto nivel', value: 'Competitivo' },
                    { label: 'Casual', description: 'Juego por diversión, sin presión', value: 'Casual' },
                ],
            },
            {
                customId: 'goal',
                placeholder: '🏆 Elige tu objetivo principal',
                options: [
                    { label: 'Mejorar K/D', description: 'Optimizar la relación de eliminaciones/muertes', value: 'Mejorar K/D' },
                    { label: 'Ganar más partidas', description: 'Enfoque en estrategias de victoria', value: 'Ganar más partidas' },
                    { label: 'Subir de rango', description: 'Tácticas para avanzar en el sistema de clasificación', value: 'Subir de rango' },
                    { label: 'Jugar en equipo', description: 'Mejorar la coordinación y sinergia', value: 'Jugar en equipo' },
                    { label: 'Divertirme', description: 'Feedback para maximizar la diversión', value: 'Divertirme' },
                ],
            },
            {
                customId: 'tts_voice',
                placeholder: '🗣️ Elige la voz del coach (TTS)',
                options: [
                    { label: 'Masculina (Estándar)', value: 'es-ES-Standard-B' },
                    { label: 'Femenina (Estándar)', value: 'es-ES-Standard-A' },
                    { label: 'Masculina (Wavenet)', value: 'es-ES-Wavenet-B' },
                    { label: 'Femenina (Wavenet)', value: 'es-ES-Wavenet-A' },
                ],
            },
            {
                customId: 'tts_speed',
                placeholder: '⏩ Elige la velocidad de la voz',
                options: [
                    { label: 'Lenta', value: 'Lenta' },
                    { label: 'Normal', value: 'Normal' },
                    { label: 'Rápida', value: 'Rapida' },
                ],
            },
        ];

        const createRow = (menu) => new ActionRowBuilder().addComponents(
            new StringSelectMenuBuilder()
                .setCustomId(menu.customId)
                .setPlaceholder(menu.placeholder)
                .addOptions(menu.options)
        );

        const rows1 = preferenceMenus1.map(createRow);
        const rows2 = preferenceMenus2.map(createRow);

        await dmChannel.send({
            content: 'He analizado tu partida. Para darte el mejor feedback, por favor, responde a estas preguntas (1/2):',
            components: rows1
        });

        const message2 = await dmChannel.send({
            content: 'Y ahora la segunda parte (2/2):',
            components: rows2
        });

        const collector = dmChannel.createMessageComponentCollector({
            componentType: ComponentType.StringSelect,
            time: 300000 // 5 minutos para responder
        });

        return new Promise((resolve, reject) => {
            collector.on('collect', i => {
                preferences[i.customId] = i.values[0];
                i.reply({ content: `✅ Opción guardada: ${i.values[0]}`, ephemeral: true });
                
                // Si se han recopilado las 8 preferencias
                if (Object.keys(preferences).length === 8) {
                    collector.stop('completed');
                }
            });

            collector.on('end', (collected, reason) => {
                if (reason === 'completed') {
                    console.log(`✅ Preferencias recopiladas para ${userId}:`, preferences);
                    saveUserPreferences(userId, preferences);
                    resolve(preferences);
                } else {
                    console.log(`⚠️ Recopilación de preferencias para ${userId} finalizada por: ${reason}`);
                    // Guardar lo que se tenga y resolver, o rechazar si no hay nada
                    if (Object.keys(preferences).length > 0) {
                        saveUserPreferences(userId, preferences);
                        resolve(preferences); // Resolver con lo que tenga
                    } else {
                        reject(new Error('El usuario no respondió a tiempo.'));
                    }
                }
            });
        });

    } catch (error) {
        console.error(`❌ Error al enviar DM a ${userId}:`, error);
        // Devolver un objeto de preferencias por defecto si el DM falla
        return Promise.resolve(getDefaultPreferences());
    }
}

function getDefaultPreferences() {
    const defaults = {
        game: 'Call of Duty',
        coach_type: 'Directo',
        aspect: 'Comunicacion',
        personality: 'Competitivo',
        experience: 'Intermedio',
        goal: 'Ganar más partidas',
        tts_voice: 'es-ES-Standard-B',
        tts_speed: 'Normal',
    };
    console.log("⚠️ Usando preferencias por defecto.");
    return defaults;
}

// Función para guardar preferencias del usuario
function saveUserPreferences(userId, preferences) {
    const fs = require('fs');
    const preferencesFile = './user_preferences.json';
    
    let allPreferences = {};
    
    // Leer preferencias existentes
    try {
        if (fs.existsSync(preferencesFile)) {
            const data = fs.readFileSync(preferencesFile, 'utf8');
            allPreferences = JSON.parse(data);
        }
    } catch (error) {
        console.error('Error leyendo preferencias existentes:', error);
    }
    
    // Guardar nuevas preferencias
    allPreferences[userId] = preferences;
    
    // Escribir archivo
    try {
        fs.writeFileSync(preferencesFile, JSON.stringify(allPreferences, null, 2));
        console.log(`Preferencias guardadas para usuario ${userId}`);
    } catch (error) {
        console.error('Error guardando preferencias:', error);
        throw error;
    }
}

// Función para obtener las preferencias del usuario
function getUserPreferences(userId) {
    const fs = require('fs');
    const preferencesFile = './user_preferences.json';
    
    if (fs.existsSync(preferencesFile)) {
        try {
            const data = fs.readFileSync(preferencesFile, 'utf8');
            const allPreferences = JSON.parse(data);
            return allPreferences[userId] || {};
        } catch (error) {
            console.error('Error leyendo preferencias:', error);
            return {};
        }
    }
    return {};
}

// Function to send a private message to a Discord user
async function sendFeedbackToUser(userId, feedback, ttsPrefs) {
    try {
        const user = await client.users.fetch(userId);
        const dmChannel = await user.createDM();

        // Generar audio TTS
        const ttsAudioBuffer = await generateTTS(
            feedback,
            ttsPrefs.tts_voice || 'es-ES-Standard-B',
            ttsPrefs.tts_speed || 'Normal'
        );

        // Enviar solo el archivo de audio
        await dmChannel.send({
            content: "Aquí tienes tu análisis de Clutch:",
            files: [{
                attachment: ttsAudioBuffer,
                name: 'Clutch Analysis.mp3'
            }]
        });

        console.log(`✅ Feedback enviado a ${user.username}`);

    } catch (error) {
        console.error(`❌ Error enviando feedback a ${userId}:`, error);
    }
}

// Función para generar TTS con Google
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
        console.error('Error en la API de Google TTS:', error);
        throw error;
    }
}

async function convertPcmToMp3(pcmBuffer) {
    return new Promise((resolve, reject) => {
        const ffmpegProcess = ffmpeg()
            .input('pipe:0')
            .inputFormat('s16le')
            .inputOptions(['-ar 48000', '-ac 2'])
            .toFormat('mp3')
            .outputOptions([
                '-acodec libmp3lame',
                '-q:a 2', // Buena calidad, buen balance
                '-ar 48000',
                '-ac 2',
            ])
            .on('error', (err) => {
                console.error('Error de FFMPEG:', err.message);
                reject(err);
            });

        const mp3Chunks = [];
        const mp3Stream = ffmpegProcess.pipe();

        mp3Stream.on('data', (chunk) => {
            mp3Chunks.push(chunk);
        });

        mp3Stream.on('end', () => {
            console.log("Conversión a MP3 finalizada.");
            resolve(Buffer.concat(mp3Chunks));
        });
        
        mp3Stream.on('error', (err) => {
            console.error("Error en el stream de salida de MP3.");
            reject(err);
        });

        ffmpegProcess.input(require('stream').Readable.from(pcmBuffer)).run();
    });
}

// Función para análisis con preferencias ya recopiladas
async function spawnPythonAndAnalyze(audioBuffer, user) {
    return new Promise((resolve, reject) => {
        const timestamp = Date.now();
        const pythonProcess = spawn('python', [
            './esports_processor_simple.py',
            user.id,
            user.username,
            timestamp
        ], { stdio: ['pipe', 'pipe', 'pipe'], encoding: 'utf-8' });

        let stdoutData = '';
        let stderrData = '';

        // Pipe the audio buffer to the Python script's stdin
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

function setupAudioStream(receiver, user, connection) {
    try {
        console.log(`Configurando stream de audio para ${user.username}...`);
        
        const audioStream = receiver.subscribe(user.id, {
            end: {
                behavior: EndBehaviorType.Manual, // Ensure manual control
            },
        });
        
        const decoder = new prism.opus.Decoder({ rate: 48000, channels: 2, frameSize: 960 });

        // Store stream, decoder, and chunks in the active recordings map
        activeRecordings.set(user.id, {
            audioStream,
            decoder,
            user,
            pcmChunks: [],
            isReady: false
        });

        // Set up pipeline with better error handling
        const pipelineStream = pipeline(audioStream, decoder, (err) => {
            if (err) {
                if (err.code === 'ERR_STREAM_DESTROYED') {
                    console.log(`Stream destruido correctamente para ${user.username}`);
                } else if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                    console.log(`⚠️ Stream cerrado prematuramente para ${user.username} en pipeline`);
                } else {
                    console.error(`Error en pipeline para ${user.username}:`, err);
                }
            }
        });

        // Wait a bit before marking as ready to allow Discord to start sending audio
        setTimeout(() => {
            if (activeRecordings.has(user.id)) {
                activeRecordings.get(user.id).isReady = true;
                console.log(`✅ Stream listo para ${user.username}`);
            }
        }, 2000);

        decoder.on('data', (chunk) => {
            const recording = activeRecordings.get(user.id);
            if (recording && recording.isReady) {
                recording.pcmChunks.push(chunk);
            }
        });

        decoder.on('error', (err) => {
            // Handle premature close gracefully - this is expected during manual stream destruction
            if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                console.log(`⚠️ Stream cerrado prematuramente para ${user.username} durante configuración inicial`);
            } else {
                console.error(`Error en decodificador para ${user.username}:`, err);
            }
        });
          // Add error handling to audio stream as well
        audioStream.on('error', (err) => {
            if (err.code === 'ERR_STREAM_PREMATURE_CLOSE') {
                console.log(`⚠️ AudioStream cerrado prematuramente para ${user.username}`);
            } else {
                console.error(`Error en audioStream para ${user.username}:`, err);
            }
        });

        // Log when audio stream actually starts receiving data (only once)
        let hasLoggedReceiving = false;
        audioStream.on('readable', () => {
            if (!hasLoggedReceiving) {
                console.log(`📡 Audio stream comenzó a recibir datos para ${user.username}`);
                hasLoggedReceiving = true;
            }
        });

        // Handle natural stream end (when user stops talking for a while)
        audioStream.on('end', () => {
            console.log(`ℹ️ Stream naturally ended for ${user.username} - this is normal`);
        });

        audioStream.on('close', () => {
            console.log(`ℹ️ Stream closed for ${user.username} - this is normal`);
        });

    } catch (error) {
        console.error(`Error configurando stream para ${user.username}:`, error);
    }
}

function handleConnectionStatus(connection) {
    connection.on(VoiceConnectionStatus.Ready, () => {
        console.log('Conexión de voz lista.');
    });

    connection.on(VoiceConnectionStatus.Disconnected, async (oldState, newState) => {
        try {
            await Promise.race([
                entersState(connection, VoiceConnectionStatus.Signalling, 5000),
                entersState(connection, VoiceConnectionStatus.Connecting, 5000),
            ]);
            // Parece que nos estamos reconectando
        } catch (error) {
            // Parece que la desconexión fue permanente
            console.log('Conexión de voz desconectada permanentemente.');
            if (connection.state.status !== VoiceConnectionStatus.Destroyed) {
                connection.destroy();
            }
        }
    });
}