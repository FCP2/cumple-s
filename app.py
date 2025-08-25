import os, importlib, subprocess
from flask import Flask, jsonify, send_file, Response, request
from threading import Thread

# Crea credenciales.json desde secreto (no subas el archivo al repo)
CREDS = os.getenv("GOOGLE_CREDENTIALS_JSON")
if CREDS:
    with open("credenciales.json", "w", encoding="utf-8") as f:
        f.write(CREDS)

PERSIST_DIR = os.getenv("PERSIST_DIR", "/data")
QR_PATH = os.path.join(PERSIST_DIR, "qr.png")

RUN_TOKEN = os.getenv("RUN_TOKEN")  # opcional para proteger /run

app = Flask(__name__)
RUNNING = False

def call_cumple():
    global RUNNING
    if RUNNING:
        return False, "Ya hay una ejecución en curso"
    RUNNING = True
    try:
        mod = importlib.import_module("cumple")  # tu archivo: cumple.py
        if hasattr(mod, "run_job"):
            mod.run_job()
        elif hasattr(mod, "main"):
            mod.main()
        else:
            subprocess.run(["python", "cumple.py"], check=True)
        RUNNING = False
        return True, "OK"
    except Exception as e:
        RUNNING = False
        return False, str(e)

@app.get("/")
def health():
    return "✅ Servicio activo. Usa /run para disparar, /warmup para generar QR, y /qr para verlo."

@app.get("/run")
def run():
    if RUN_TOKEN and request.args.get("key") != RUN_TOKEN:
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    ok, msg = call_cumple()
    return jsonify({"ok": ok, "msg": msg}), (200 if ok else 409)

# --- genera el QR sin correr todo el job ---
def _generate_qr():
    try:
        from cumple import construir_driver, asegurar_sesion_whatsapp
        d = construir_driver()
        asegurar_sesion_whatsapp(d)  # aquí se guarda /data/qr.png
        d.quit()
    except Exception as e:
        print("Warmup error:", e)

@app.get("/warmup")
def warmup():
    Thread(target=_generate_qr).start()
    return "OK: generando QR en background. Abre /qr en ~10-15s.", 202

@app.get("/qr")
def qr():
    if os.path.exists(QR_PATH):
        return send_file(QR_PATH, mimetype="image/png")
    return Response("No hay QR aún. Genera abriendo WhatsApp en tu script y guardando /data/qr.png.", 404)

# util sencillo para verificar que /data existe y listar archivos
@app.get("/ls")
def ls():
    try:
        files = os.listdir(PERSIST_DIR)
        return jsonify({"dir": PERSIST_DIR, "files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
