# -*- coding: utf-8 -*-
"""
Script to run the Flask application
"""
if __name__ == '__main__':
    from app import app
    import socket
    
    # Получаем локальный IP
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print("\n" + "="*60)
    print("Starting NeuroSpeech Flask Application")
    print("="*60)
    print(f"\n📱 Доступ с телефона:")
    print(f"   http://{local_ip}:5000")
    print(f"\n💻 Локальный доступ:")
    print(f"   http://localhost:5000")
    print(f"   http://127.0.0.1:5000")
    print("\n" + "="*60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
