from base import app,db
import os
import requests

def get_public_ip():
    try:
        response = requests.get('https://api.ipify.org?format=text')
        ip = response.text.strip()
        return ip
    except Exception as e:
        print(f"Error obtaining public IP: {e}")
        return None
    
if __name__ == '__main__':
    with app.app_context():
        print("==================== CIAOOOOO =======================")
        public_ip = get_public_ip()
    if public_ip:
        print(f"Public IP: {public_ip}")
    else:
        print("Could not obtain public IP.")

    db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))