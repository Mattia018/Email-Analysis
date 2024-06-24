from base import app,db
import os

# Avvio app su pota 8080 e creazione DB
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))