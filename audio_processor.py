import os
import sys
import subprocess

def run_separation_pipeline(upload_path, output_dir):
    """Runs pure Demucs 6-stem separation."""
    env = os.environ.copy()
    env["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{env.get('PATH', '')}"
    env["PYTHONHTTPSVERIFY"] = "0"
    env["TO_DISABLE_SSL_VERIFICATION"] = "1"
    
    try:
        import certifi
        env["SSL_CERT_FILE"] = certifi.where()
        env["REQUESTS_CA_BUNDLE"] = certifi.where()
    except ImportError:
        pass

    # Run Demucs 6-Stem separation [1]
    result = subprocess.run([
        sys.executable, "-m", "demucs", 
        "-n", "htdemucs_6s", 
        "-o", "./separated", 
        upload_path
    ], env=env, capture_output=True, text=True)
    
    if result.returncode != 0:
        raise Exception(result.stderr)