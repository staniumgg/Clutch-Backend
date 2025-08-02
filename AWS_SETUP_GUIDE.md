# Guía de Configuración AWS DynamoDB

## Opción 1: Configuración con AWS Real (Recomendado para producción)

### Paso 1: Crear cuenta AWS
1. Ve a [aws.amazon.com](https://aws.amazon.com)
2. Haz clic en "Create AWS Account"
3. Completa el registro (requiere tarjeta de crédito, pero DynamoDB tiene tier gratuito)

### Paso 2: Crear usuario IAM
1. Ve al servicio IAM en la consola AWS
2. Haz clic en "Users" → "Add user"
3. Nombre: `clutch-esports-user`
4. Selecciona "Programmatic access"
5. En permisos, adjunta la política: `AmazonDynamoDBFullAccess`

### Paso 3: Obtener credenciales
1. Después de crear el usuario, copia:
   - Access Key ID (formato: AKIA...)
   - Secret Access Key (40 caracteres)
2. Actualiza tu archivo `.env`:
   ```
   AWS_ACCESS_KEY_ID=AKIA1234567890123456
   AWS_SECRET_ACCESS_KEY=abcdefghij1234567890abcdefghij1234567890
   ```

## Opción 2: DynamoDB Local (Para desarrollo)

### Instalación
```bash
# Descargar DynamoDB Local
curl -O https://s3-us-west-2.amazonaws.com/dynamodb-local/dynamodb_local_latest.zip
unzip dynamodb_local_latest.zip

# Ejecutar
java -Djava.library.path=./DynamoDBLocal_lib -jar DynamoDBLocal.jar -sharedDb
```

### Configuración para desarrollo local
En tu `.env`, usar:
```
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=dummy
AWS_SECRET_ACCESS_KEY=dummy
DYNAMODB_ENDPOINT=http://localhost:8000
DYNAMODB_TABLE_NAME=ClutchAnalysis
```

## Costos AWS DynamoDB
- **Tier gratuito**: 25 GB de almacenamiento
- **Lectura**: 25 unidades por segundo
- **Escritura**: 25 unidades por segundo
- Para tu proyecto: prácticamente gratuito por varios meses

## Regiones recomendadas
- `us-east-1` (Virginia) - Más barata
- `us-west-2` (Oregon) - Buena latencia
- `eu-west-1` (Irlanda) - Para Europa
