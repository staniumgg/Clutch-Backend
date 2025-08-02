const admin = require('firebase-admin');
const fs = require('fs');
const serviceAccount = require('./clutchgg-b11bc-firebase-adminsdk-fbsvc-7f92773a86.json');

// Initialize Firebase Admin SDK with storage configuration
admin.initializeApp({
    credential: admin.credential.cert(serviceAccount),
    storageBucket: 'clutchgg-b11bc.appspot.com'
});

const bucket = admin.storage().bucket();
console.log('Firebase Storage bucket initialized:', bucket.name);

/**
 * Uploads a file to Firebase Storage.
 * @param {string} filePath - The local path to the file to upload.
 * @param {string} destination - The destination path in the bucket.
 * @returns {Promise<string>} - The public URL of the uploaded file.
 */
async function uploadToFirebase(filePath, destination) {
    try {
        console.log(`Intentando subir archivo: ${filePath} a ${destination}`);
        
        // Verificar que el archivo existe
        if (!fs.existsSync(filePath)) {
            throw new Error(`El archivo ${filePath} no existe`);
        }

        // Verificar que el bucket está configurado
        if (!bucket) {
            throw new Error('El bucket de Firebase no está configurado correctamente');
        }

        // Subir el archivo con metadata
        await bucket.upload(filePath, {
            destination,
            metadata: {
                contentType: 'audio/mpeg',
            },
            public: true
        });

        // Get the public URL
        const file = bucket.file(destination);
        console.log('Archivo subido, obteniendo URL...');
        const [url] = await file.getSignedUrl({
            action: 'read',
            expires: '03-01-2500' // Set a far future expiration date
        });

        return url;
    } catch (error) {
        console.error('Error uploading to Firebase:', error);
        throw error;
    }
}

/**
 * Saves metadata to Firestore.
 * @param {string} collection - The Firestore collection name.
 * @param {string} documentId - The document ID.
 * @param {Object} data - The data to save.
 * @returns {Promise<boolean>} - True if the operation is successful.
 */
async function saveToFirestore(collection, documentId, data) {
    try {
        const db = admin.firestore();
        await db.collection(collection).doc(documentId).set(data);
        return true;
    } catch (error) {
        console.error('Error saving to Firestore:', error);
        return false;
    }
}

// Export the functions
module.exports = {
    uploadToFirebase,
    saveToFirestore
};

// Log that the module is loaded
console.log('Firebase Admin module loaded successfully');
