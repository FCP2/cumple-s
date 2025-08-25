import os, importlib, subprocess, shutil
from flask import Flask, jsonify, send_file, Response, request
from threading import Thread

# ========================
# Configuración de rutas
# ========================
PERSIST_DIR = os.getenv("PERSIST_DIR", "/data")
QR_PATH = os.path.join(PERSIST_DIR, "qr.png")
PROFILE_DIR = os.path.join(PERSIST_DIR, "chrome-profile")
RUN_TOKEN = os.getenv("RUN_TOKEN")  # opcional, para proteger endpoints

# ========================
# Manejo de credenciales
# ========================
CREDS = os.getenv("GOOGLE_CREDENTIALS_JSON")
if CREDS:
    with open("credenciales.json", "w", encoding="utf-8") as f:
        f.write(CREDS)

# ========================
# Inicializar Flask
# ========================
app = Flask(__name__)
RUNNING = False

# ========================
# Utilidad de auth
# ========================
def _auth_ok(req):
    return (RUN_TOKEN is None) or (req.args.get("key") == RUN_TOKEN)

# ========================
# Ejecución del script
# ========================
def call_cumple():
    global RUNNING
    if RUNNING:
        return False, "Ya hay una ejecución en curso"
    RUNNING = True
    try:
        mod = importlib.import_module("cumple")
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

# ========================
# Endpoints principales
# ========================
@app.get("/")
def health():
    return "✅ Servicio activo. Usa /run para disparar, /warmup para generar QR, y /qr para verlo."

@app.get("/run")
def run():
    if not _auth_ok(request):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    ok, msg = call_cumple()
    return jsonify({"ok": ok, "msg": msg}), (200 if ok else 409)

# --- Warmup para generar QR en background ---
def _generate_qr():
    try:
        from cumple import construir_driver, asegurar_sesion_whatsapp
        d = construir_driver()
        asegurar_sesion_whatsapp(d)
        d.quit()
    except Exception as e:
        print("Warmup error:", e)

@app.get("/warmup")
def warmup():
    if not _auth_ok(request):
        return "Unauthorized", 401
    global RUNNING
    if RUNNING:
        return "Ya hay un Chrome abierto, espera a que termine", 409
    Thread(target=_generate_qr).start()
    return "OK: generando QR en background. Abre /qr en ~15-25s.", 202

@app.get("/qr")
def qr():
    if os.path.exists(QR_PATH):
        return send_file(QR_PATH, mimetype="image/png")
    return Response("No hay QR aún. Genera abriendo WhatsApp en tu script y guardando /data/qr.png.", 404)

# ========================
# Endpoints de utilidades
# ========================
@app.get("/env")
def env_info():
    if not _auth_ok(request):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    return jsonify({
        "PERSIST_DIR": PERSIST_DIR,
        "PROFILE_DIR": PROFILE_DIR,
        "QR_PATH": QR_PATH,
        "exists": {
            "persist_dir": os.path.isdir(PERSIST_DIR),
            "profile_dir": os.path.isdir(PROFILE_DIR),
            "qr_png": os.path.exists(QR_PATH),
        }
    })

@app.get("/ls")
def ls():
    if not _auth_ok(request):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    try:
        return jsonify({"dir": PERSIST_DIR, "files": os.listdir(PERSIST_DIR)})
    except Exception as e:
        return jsonify({"ok": False, "error": repr(e)}), 500

@app.get("/clearlocks")
def clearlocks():
    if not _auth_ok(request):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    removed = []
    for name in ["SingletonLock", "SingletonCookie", "SingletonSocket", "SingletonIPC"]:
        p = os.path.join(PROFILE_DIR, name)
        if os.path.exists(p):
            try:
                os.remove(p)
                removed.append(name)
            except Exception as e:
                return jsonify({"ok": False, "error": f"{name}: {e}", "profile_dir": PROFILE_DIR}), 500
    return jsonify({"ok": True, "removed": removed, "profile_dir": PROFILE_DIR})

@app.get("/unlink")
def unlink():
    if not _auth_ok(request):
        return jsonify({"ok": False, "msg": "Unauthorized"}), 401
    try:
        shutil.rmtree(PROFILE_DIR)
        return jsonify({"ok": True, "msg": "Perfil borrado; vuelve a /warmup y /qr para vincular."})
    except FileNotFoundError:
        return jsonify({"ok": True, "msg": "Perfil no existía. Puedes hacer /warmup."})
    except Exception as e:
        return jsonify({"ok": False, "error": repr(e)}), 500

# ========================
# Arranque
# ========================
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
