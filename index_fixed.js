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
    // Comandos de ayuda y estado
    if (message.content === '!help' || message.content === '!ayuda') {
        const helpEmbed = {
            color: 0x0099ff,
            title: '🎮 Clutch Gaming Coach Bot',
            description: 'Bot de análisis de comunicación para gaming',
            fields: [
                {
                    name: '🎙️ !record',
                    value: 'Comenzar a grabar audio del canal de voz',
                    inline: true
                },
                {
                    name: '⏹️ !stop',
                    value: 'Detener grabación y procesar análisis',
                    inline: true
                },
                {
                    name: '📊 !status',
                    value: 'Ver estado actual de grabación',
                    inline: true
                }
            ],
            footer: {
                text: 'Para usar el bot, únete a un canal de voz y usa !record'
            }
        };
        return message.reply({ embeds: [helpEmbed] });
    }

    if (message.content === '!status') {
        const connection = getVoiceConnection(message.guild.id);
        if (connection && activeRecordings.size > 0) {
            let statusText = `🔴 **Grabando activamente**\n\n`;
            for (const [userId, recording] of activeRecordings.entries()) {
                const duration = Math.round((Date.now() - recording.startTime) / 1000);
                statusText += `👤 ${recording.user.username}: ${recording.pcmChunks.length} chunks, ${duration}s\n`;
            }
            return message.reply(statusText);
        } else {
            return message.reply('⚪ No hay grabaciones activas. Usa `!record` para comenzar.');
        }
    }

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
        
        connection.on(VoiceConnectionStatus.Ready, () => {
            console.log('✅ Conexión de voz lista, configurando streams de audio...');
            const receiver = connection.receiver;

            // Buscar usuarios en el canal de voz
            const usersInChannel = message.member.voice.channel.members.filter(member => !member.user.bot);
            console.log(`👥 Usuarios encontrados en el canal: ${usersInChannel.size}`);
            
            if (usersInChannel.size === 0) {
                console.log('⚠️ No hay usuarios para grabar en el canal');
                message.reply('No hay otros usuarios en el canal de voz para grabar.');
                return;
            }

            usersInChannel.forEach((member) => {
                const user = member.user;
                console.log(`🔴 Iniciando grabación para ${user.username} (ID: ${user.id})`);
                
                // Inicializar estructura de grabación
                activeRecordings.set(user.id, {
                    user,
                    pcmChunks: [],
                    isRecording: true,
                    startTime: Date.now()
                });

                // Configurar listener continuo para este usuario
                setupContinuousRecording(receiver, user);
            });
            
            console.log(`📊 Total de grabaciones activas: ${activeRecordings.size}`);
        });

        message.reply('🎙️ ¡Empezando a grabar! Habla normalmente y usa `!stop` cuando quieras detener la grabación y recibir tu análisis.');
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
                
                // Mostrar estadísticas de grabación
                for (const [userId, recording] of activeRecordings.entries()) {
                    const duration = Date.now() - recording.startTime;
                    console.log(`📊 ${recording.user.username}: ${recording.pcmChunks.length} chunks, ${Math.round(duration/1000)}s de grabación`);
                }

                // Marcar todas las grabaciones como detenidas
                for (const [userId, recording] of activeRecordings.entries()) {
                    recording.isRecording = false;
                    console.log(`🛑 Deteniendo grabación para ${recording.user.username}`);
                }

                // Esperar más tiempo para recoger audio restante
                setTimeout(async () => {
                    console.log(`📊 Iniciando procesamiento de ${activeRecordings.size} grabaciones...`);
                    
                    const processingPromises = [];

                    for (const [userId, recording] of activeRecordings.entries()) {
                        console.log(`📋 Preparando procesamiento para ${recording.user.username} - chunks: ${recording.pcmChunks.length}`);
                        const processPromise = processRecording(userId, recording, message);
                        processingPromises.push(processPromise);
                    }

                    const results = await Promise.allSettled(processingPromises);
                    
                    results.forEach((result, index) => {
                        const recording = Array.from(activeRecordings.values())[index];
                        if (result.status === 'rejected') {
                            console.error(`❌ Error procesando ${recording.user.username}:`, result.reason);
                        } else {
                            console.log(`✅ Procesamiento exitoso para ${recording.user.username}`);
                        }
                    });

                    activeRecordings.clear();
                    connection.destroy();
                    console.log("✅ Procesamiento completo. Conexión cerrada.");
                    await message.channel.send("✅ ¡Análisis completo! Revisa tus mensajes directos para ver el feedback.");
                }, 5000); // Aumentar a 5 segundos

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

function setupContinuousRecording(receiver, user) {
    console.log(`🎯 Configurando grabación continua para ${user.username}`);
    
    const createNewStream = () => {
        const recording = activeRecordings.get(user.id);
        if (!recording || !recording.isRecording) {
            console.log(`⏹️ Grabación detenida para ${user.username}, no creando nuevo stream`);
            return;
        }

        try {
            console.log(`🔄 Creando nuevo stream para ${user.username}`);
            
            const audioStream = receiver.subscribe(user.id, {
                end: {
                    behavior: EndBehaviorType.AfterSilence,
                    duration: 1000, // Terminar después de 1 segundo de silencio
                },
            });
            
            const decoder = new prism.opus.Decoder({ 
                rate: 48000, 
                channels: 2, 
                frameSize: 960 
            });

            let audioChunks = 0;
            let hasStarted = false;

            // NO usar pipeline - conectar manualmente
            audioStream.on('data', (chunk) => {
                try {
                    if (!hasStarted) {
                        console.log(`🎤 ${user.username} comenzó a hablar`);
                        hasStarted = true;
                    }
                    decoder.write(chunk);
                    audioChunks++;
                } catch (err) {
                    console.log(`⚠️ Error escribiendo chunk para ${user.username}: ${err.message}`);
                }
            });

            audioStream.on('end', () => {
                console.log(`🔇 ${user.username} dejó de hablar (chunks procesados: ${audioChunks})`);
                try {
                    decoder.end();
                } catch (err) {
                    console.log(`⚠️ Error cerrando decoder para ${user.username}: ${err.message}`);
                }
                
                // Configurar un nuevo stream después de un breve delay
                const currentRecording = activeRecordings.get(user.id);
                if (currentRecording && currentRecording.isRecording) {
                    setTimeout(() => {
                        console.log(`🔄 Preparando siguiente stream para ${user.username}...`);
                        createNewStream();
                    }, 500);
                }
            });

            decoder.on('data', (chunk) => {
                const currentRecording = activeRecordings.get(user.id);
                if (currentRecording && currentRecording.isRecording) {
                    currentRecording.pcmChunks.push(chunk);
                    console.log(`📊 Chunk PCM capturado para ${user.username}: ${chunk.length} bytes (total chunks: ${currentRecording.pcmChunks.length})`);
                }
            });

            // Manejar errores silenciosamente - son parte del comportamiento normal
            audioStream.on('error', (err) => {
                console.log(`⚠️ AudioStream error para ${user.username}: ${err.code || err.message}`);
            });
            
            decoder.on('error', (err) => {
                console.log(`⚠️ Decoder error para ${user.username}: ${err.code || err.message}`);
            });

        } catch (error) {
            console.log(`❌ Error creando stream para ${user.username}: ${error.message}`);
            // Error creando stream - reintentar después de un delay
            const recording = activeRecordings.get(user.id);
            if (recording && recording.isRecording) {
                setTimeout(() => {
                    console.log(`🔄 Reintentando crear stream para ${user.username}...`);
                    createNewStream();
                }, 1000);
            }
        }
    };

    // Iniciar el primer stream después de un pequeño delay
    setTimeout(() => {
        console.log(`✅ Iniciando captura de audio para ${user.username}`);
        createNewStream();
    }, 1000);
}

async function processRecording(userId, recording, message) {
    try {
        const pcmBuffer = Buffer.concat(recording.pcmChunks);
        console.log(`✅ Procesando grabación para ${recording.user.username}. PCM bytes: ${pcmBuffer.length}`);

        if (pcmBuffer.length === 0) {
            console.log(`⚠️ No se grabó audio para ${recording.user.username}.`);
            return;
        }

        // Verificar que tenemos suficiente audio (mínimo ~1 segundo)
        const minBytes = 48000 * 2 * 2; // 48kHz * 2 channels * 2 bytes * 1 second
        if (pcmBuffer.length < minBytes) {
            console.log(`⚠️ Audio muy corto para ${recording.user.username}: ${pcmBuffer.length} bytes`);
            return;
        }

        console.log(`🎵 Convirtiendo ${pcmBuffer.length} bytes PCM a MP3...`);
        const mp3Buffer = await convertPcmToMp3(pcmBuffer);
        
        if (!mp3Buffer || mp3Buffer.length === 0) {
            throw new Error('La conversión a MP3 produjo un buffer vacío.');
        }

        console.log(`✅ MP3 generado: ${mp3Buffer.length} bytes`);

        const [preferencesResult, analysisResult] = await Promise.allSettled([
            collectUserPreferences(userId, message),
            spawnPythonAndAnalyze(mp3Buffer, recording.user)
        ]);

        let userPreferences;
        if (preferencesResult.status === 'fulfilled') {
            userPreferences = preferencesResult.value;
        } else {
            console.error(`⚠️ Error en preferencias para ${recording.user.username}. Usando defaults.`);
            userPreferences = getDefaultPreferences();
        }

        if (analysisResult.status === 'fulfilled') {
            const { analysis } = analysisResult.value;
            await sendFeedbackToUser(userId, analysis, userPreferences);
        } else {
            throw new Error(`Análisis falló: ${analysisResult.reason.message}`);
        }

    } catch (error) {
        console.error(`❌ Error procesando para ${recording.user.username}:`, error);
        
        // Intentar enviar un mensaje de error al usuario
        try {
            const user = await client.users.fetch(userId);
            const dmChannel = await user.createDM();
            await dmChannel.send(`❌ Hubo un problema procesando tu audio. Por favor, intenta grabar de nuevo. Error: ${error.message}`);
        } catch (dmError) {
            console.error(`❌ No se pudo enviar mensaje de error a ${recording.user.username}:`, dmError);
        }
        
        throw error;
    }
}

// Resto de funciones auxiliares (collectUserPreferences, sendFeedbackToUser, etc.)
async function collectUserPreferences(userId, message) {
    // Implementación simplificada - devuelve defaults por ahora
    return getDefaultPreferences();
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
        tts_speed: 'Normal',
    };
}

async function sendFeedbackToUser(userId, feedback, ttsPrefs) {
    try {
        const user = await client.users.fetch(userId);
        const dmChannel = await user.createDM();

        const ttsAudioBuffer = await generateTTS(
            feedback,
            ttsPrefs.tts_voice || 'es-ES-Standard-B',
            ttsPrefs.tts_speed || 'Normal'
        );

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
        console.log(`🔄 Iniciando conversión PCM a MP3: ${pcmBuffer.length} bytes`);
        
        // Crear un stream readable desde el buffer
        const { Readable } = require('stream');
        const inputStream = new Readable({
            read() {
                this.push(pcmBuffer);
                this.push(null); // End stream
            }
        });

        const mp3Chunks = [];
        
        const ffmpegProcess = ffmpeg(inputStream)
            .inputFormat('s16le')
            .inputOptions(['-ar', '48000', '-ac', '2'])
            .audioCodec('libmp3lame')
            .audioBitrate('128k')
            .format('mp3')
            .on('start', (commandLine) => {
                console.log('🎵 FFmpeg iniciado:', commandLine);
            })
            .on('progress', (progress) => {
                if (progress.percent) {
                    console.log(`🔄 Progreso conversión: ${Math.round(progress.percent)}%`);
                }
            })
            .on('end', () => {
                console.log("✅ Conversión a MP3 completada exitosamente");
                resolve(Buffer.concat(mp3Chunks));
            })
            .on('error', (err) => {
                console.error('❌ Error de FFmpeg:', err.message);
                reject(new Error(`FFmpeg error: ${err.message}`));
            });

        // Capturar output stream
        const outputStream = ffmpegProcess.pipe();
        
        outputStream.on('data', (chunk) => {
            mp3Chunks.push(chunk);
        });
        
        outputStream.on('error', (err) => {
            console.error('❌ Error en output stream:', err.message);
            reject(err);
        });

        // Iniciar el proceso
        ffmpegProcess.run();
    });
}

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
        } catch (error) {
            console.log('Conexión de voz desconectada permanentemente.');
            if (connection.state.status !== VoiceConnectionStatus.Destroyed) {
                connection.destroy();
            }
        }
    });
}
