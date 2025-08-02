import firebase_admin
from firebase_admin import credentials, storage, firestore

# Initialize Firebase Admin SDK
cred = credentials.Certificate('clutchgg-b11bc-firebase-adminsdk-fbsvc-7f92773a86.json')
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred, {
        'storageBucket': 'clutchgg-b11bc.appspot.com'
    })

# Upload file to Firebase Storage
def upload_to_firebase(file_path, destination_path):
    try:
        bucket = storage.bucket()
        blob = bucket.blob(destination_path)
        blob.upload_from_filename(file_path)
        blob.make_public()
        print(f"File uploaded to {destination_path}, public URL: {blob.public_url}")
        return blob.public_url
    except Exception as e:
        print(f"Error uploading to Firebase: {e}")
        return None

# Save data to Firestore
def save_to_firestore(collection_name, document_id, data):
    try:
        db = firestore.client()
        db.collection(collection_name).document(document_id).set(data)
        print(f"Document {document_id} saved in collection {collection_name}.")
        return True
    except Exception as e:
        print(f"Error saving to Firestore: {e}")
        return False
