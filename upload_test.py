from firebase_config import upload_to_firebase

def test_upload():
    audio_path = "recordings/callmestanium-1747586551758.mp3"
    print(f"Intentando subir archivo: {audio_path}")
    result = upload_to_firebase(audio_path, "recordings", delete_local=False)
    print(f"URL del archivo: {result}")

if __name__ == "__main__":
    test_upload()
