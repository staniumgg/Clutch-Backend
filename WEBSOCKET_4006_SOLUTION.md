# CLUTCH ESPORTS - SOLUCIÓN COMPLETA ERROR WEBSOCKET 4006

## ❌ PROBLEMA
Error Discord WebSocket 4006 al usar comandos de grabación de voz (!record)

## ✅ SOLUCIÓN COMPLETA

### 1. INSTALAR DEPENDENCIAS
```bash
python install_voice_deps.py
```

### 2. COMANDOS DE DIAGNÓSTICO

#### 🔍 Diagnóstico Completo
```
!diagnostico
```
- Verifica conexión del bot
- Revisa intents de Discord  
- Comprueba dependencias de voz
- Estado de grabaciones activas
- Recomendaciones específicas

#### 🔧 Verificar Permisos
```
!permisos
```
- Permisos del servidor
- Permisos del canal específico
- Estado detallado con emojis
- Soluciones sugeridas

#### 🧪 Probar Conexión
```
!test_conexion
```
- Prueba conexión sin grabación
- Detecta errores específicos
- Timeout de 5 segundos
- Desconexión automática

#### ⚙️ Guía para Administradores
```
!fijar_permisos
```
- Solo para administradores
- Lista permisos faltantes
- Guía paso a paso
- Canales problemáticos

### 3. CONFIGURACIÓN DEL SERVIDOR DISCORD

#### Permisos Requeridos del Bot:
- ✅ **Conectar** (a canales de voz)
- ✅ **Hablar** (en canales de voz)  
- ✅ **Usar activación por voz**
- ✅ **Ver canal**
- ✅ **Enviar mensajes**
- ✅ **Leer historial de mensajes**

#### Configuración de Rol:
1. **Configuración del Servidor** → **Roles**
2. Encontrar rol del bot
3. Activar permisos mencionados arriba
4. **Posición del rol**: Debe estar arriba en la jerarquía

#### Configuración de Canal:
1. Click derecho en canal de voz → **Editar Canal**
2. **Permisos** → Agregar rol del bot
3. Activar: **Conectar** y **Hablar**
4. Guardar cambios

### 4. FLUJO DE TRABAJO

#### ✅ Flujo Automático (Recomendado)
```
1. Usuario: únete a canal de voz
2. Usuario: !record
3. Bot: se conecta y graba automáticamente
4. Usuario: habla durante partida
5. Usuario: !stop
6. Bot: procesa automáticamente y envía análisis
```

#### 🔄 Flujo Manual (Fallback)
```
1. Usuario: únete a canal de voz
2. Usuario: !record
3. Bot: se conecta (sin grabación automática)
4. Usuario: graba externamente (OBS, Audacity)
5. Usuario: !stop
6. Usuario: sube archivo de audio
7. Bot: procesa y envía análisis
```

### 5. DEPENDENCIAS TÉCNICAS

#### Principales:
- `discord.py[voice]>=2.3.0` - Bot de Discord con soporte de voz
- `PyNaCl>=1.5.0` - Codec de audio para Discord
- `pydub>=0.25.1` - Procesamiento de audio

#### Opcionales (pero recomendadas):
- `discord.sinks` - Grabación directa en Discord
- `python-opus` - Codec Opus para mejor calidad
- `nacl` - Librería de cifrado para audio

### 6. INTENTS DISCORD

El bot requiere estos intents en Discord Developer Portal:
```python
intents = discord.Intents.default()
intents.message_content = True  # Leer mensajes
intents.voice_states = True     # Estados de voz ⭐ CRÍTICO
intents.guilds = True          # Información de servidores
intents.members = True         # Información de miembros
```

### 7. RESOLUCIÓN POR PASOS

#### Error persiste después de configuración:
1. **Reiniciar Discord** (cliente y bot)
2. **Verificar región del servidor** (some regiones tienen problemas)
3. **Cambiar canal de voz** (probar otro canal)
4. **Modo manual como fallback** (siempre funciona)

#### Códigos de error comunes:
- **4006**: Permisos insuficientes → usar `!permisos`
- **4004**: Token inválido → verificar .env
- **1006**: Conexión perdida → usar `!test_conexion`

### 8. MODO FALLBACK GARANTIZADO

Si la grabación automática falla, el bot usa modo manual:
- ✅ **Siempre funciona** independiente de discord.sinks
- ✅ **Mismo análisis** con calidad idéntica
- ✅ **Proceso automático** una vez subido el archivo
- ✅ **Compatible** con cualquier grabadora externa

### 9. COMANDOS ADICIONALES

```
!info           # Información completa del bot
!preferencias   # Resetear preferencias del usuario
```

### 10. VERIFICACIÓN FINAL

Después de aplicar soluciones:
```bash
# 1. Verificar instalación
python install_voice_deps.py

# 2. En Discord
!diagnostico
!permisos  
!test_conexion

# 3. Probar flujo completo
!record → hablar → !stop
```

## 🎯 RESULTADO ESPERADO

✅ **Grabación automática funcionando** en Discord
✅ **Análisis personalizado** con IA
✅ **Audio TTS** con feedback 
✅ **Almacenamiento cloud** (S3 + DynamoDB)
✅ **Fallback manual** como respaldo

---

**📞 SOPORTE**: Si persisten problemas, usar modo manual que garantiza 100% funcionalidad.
