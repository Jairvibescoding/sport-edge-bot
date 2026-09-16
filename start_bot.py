"""
SPORT EDGE BOT - Solo una instancia
"""
import subprocess
import sys
import os

# Verificar si ya hay un bot corriendo
def check_running():
    """Verifica si ya hay una instancia corriendo"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq python.exe', '/FO', 'CSV'],
            capture_output=True,
            text=True
        )
        count = result.stdout.count('python.exe')
        return count > 0
    except:
        return False

def main():
    print("=" * 50)
    print("SPORT EDGE BOT - Iniciando...")
    print("=" * 50)
    
    # Iniciar bot
    bot_path = os.path.join(os.path.dirname(__file__), "bot_interactivo.py")
    
    print(f"Iniciando bot: {bot_path}")
    print("Presiona Ctrl+C para detener")
    print("=" * 50)
    
    # Ejecutar bot
    subprocess.run([sys.executable, bot_path])

if __name__ == "__main__":
    main()
