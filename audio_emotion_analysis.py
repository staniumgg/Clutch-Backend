import os
import json
import random
import librosa
import soundfile as sf
import subprocess
import tempfile
import pandas as pd

def preprocess_audio(input_path, output_path, target_sr=16000):
    """
    Convierte el audio a mono, 16kHz WAV.
    """
    audio, sr = librosa.load(input_path, sr=target_sr, mono=True)
    sf.write(output_path, audio, target_sr)
    return output_path

def extract_opensmile_features(wav_path, output_csv, config='eGeMAPSv01a'):
    """
    Extrae características paralingüísticas usando OpenSMILE.
    """
    config_map = {
        'eGeMAPSv01a': r'C:\opensmile\opensmile-3.0.2-windows-x86_64\config\gemaps\eGeMAPSv01a.conf',
        'emobase': r'C:\opensmile\opensmile-3.0.2-windows-x86_64\config\emobase.conf',
        'IS13_ComParE': r'C:\opensmile\opensmile-3.0.2-windows-x86_64\config\IS13_ComParE.conf'
    }
    config_file = config_map[config]
    smilextract_path = r'C:\opensmile\opensmile-3.0.2-windows-x86_64\SMILExtract.exe'
    cmd = [
        smilextract_path,
        '-C', config_file,
        '-I', wav_path,
        '-csvoutput', output_csv
    ]
    subprocess.run(cmd, check=True)
    return output_csv

def analyze_audio_emotion(audio_path):
    """
    Pipeline: Preprocesa, extrae features con OpenSMILE y muestra el CSV.
    """
    print(f"[INFO] Preprocesando audio: {audio_path}")
    with tempfile.TemporaryDirectory() as tmpdir:
        wav_path = os.path.join(tmpdir, 'audio.wav')
        preprocess_audio(audio_path, wav_path)
        csv_path = os.path.join(tmpdir, 'features.csv')
        print(f"[INFO] Extrayendo características con OpenSMILE...")
        extract_opensmile_features(wav_path, csv_path)
        df = pd.read_csv(csv_path, sep=';')
        print(f"[INFO] Primeras columnas extraídas:")
        print(df.head())
        # Aquí podrías cargar un modelo y predecir emoción, pero mostramos el CSV para empezar
        return {'opensmile_features': df.head().to_dict()}

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Uso: python audio_emotion_analysis.py <ruta_audio>")
        sys.exit(1)
    audio_path = sys.argv[1]
    resultado = analyze_audio_emotion(audio_path)
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
