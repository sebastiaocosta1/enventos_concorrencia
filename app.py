from flask import Flask, render_template, request, redirect, url_for, jsonify
from threading import Thread, Lock
import time

app = Flask(__name__)

# Dados simulados
events = [
    {"id": 1, "name": "Workshop de React", "date": "15/11/2024", "slots": 20},
    {"id": 2, "name": "Conferência de UX", "date": "20/11/2024", "slots": 15},
    {"id": 3, "name": "Hackathon 2024", "date": "25/11/2024", "slots": 30},
    {"id": 4, "name": "DevOps Summit", "date": "30/11/2024", "slots": 25}    
]

registrations = []  # Inscrições
connected_sessions = []  # Sessões conectadas
waiting_sessions = []  # Lista de espera
max_connections = 3

# Lock para garantir acesso seguro às listas
list_lock = Lock()

# Função para gerenciar a lista de espera em uma thread separada
def manage_waiting_sessions():
    while True:
        with list_lock:
            if len(connected_sessions) < max_connections and waiting_sessions:
                # Promove o próximo da lista de espera para conectado
                next_session = waiting_sessions.pop(0)
                connected_sessions.append(next_session)
                print(f"Promovido da lista de espera: {next_session}")
        time.sleep(1)  # Evita consumo excessivo de recursos

# Inicia a thread ao iniciar a aplicação
Thread(target=manage_waiting_sessions, daemon=True).start()

@app.route("/")
def index():
    return render_template("index.html", events=events)

@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Evento não encontrado!", 404

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        if event["slots"] > 0:
            registrations.append({"name": name, "email": email, "event": event["name"]})
            event["slots"] -= 1
            return redirect(url_for("index"))
        else:
            return "Vagas esgotadas!", 400

    return render_template("register.html", event=event)

@app.route("/admin")
def admin():
    return render_template("admin.html", events=events)

@app.route("/admin/add", methods=["GET", "POST"])
def add_event():
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        slots = int(request.form["slots"])

        new_event = {"id": len(events) + 1, "name": name, "date": date, "slots": slots}
        events.append(new_event)
        return redirect(url_for("admin"))

    return render_template("add_event.html")

@app.route("/admin/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Evento não encontrado!", 404

    if request.method == "POST":
        event["name"] = request.form["name"]
        event["date"] = request.form["date"]
        event["slots"] = int(request.form["slots"])
        return redirect(url_for("admin"))

    return render_template("edit_event.html", event=event)

@app.route("/admin/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    global events
    events = [e for e in events if e["id"] != event_id]
    return redirect(url_for("admin"))

@app.route("/register_tab", methods=["POST"])
def register_tab():
    tab_session_id = request.json.get("tabSessionId")
    if not tab_session_id:
        return jsonify({"error": "Tab session ID is required"}), 400

    with list_lock:
        if tab_session_id in connected_sessions or tab_session_id in waiting_sessions:
            return jsonify({"message": "Tab already registered", "tabSessionId": tab_session_id})

        if len(connected_sessions) < max_connections:
            connected_sessions.append(tab_session_id)
            status = "connected"
        else:
            waiting_sessions.append(tab_session_id)
            status = "waiting"

    return jsonify({"message": f"Tab {status}", "tabSessionId": tab_session_id})

@app.route("/list_tabs", methods=["GET"])
def list_tabs():
    with list_lock:
        return jsonify({"connected": connected_sessions, "waiting": waiting_sessions})

@app.route("/remove_tab", methods=["POST"])
def remove_tab():
    tab_session_id = request.json.get("tabSessionId")
    if not tab_session_id:
        return jsonify({"error": "Tab session ID is required"}), 400

    with list_lock:
        if tab_session_id in connected_sessions:
            connected_sessions.remove(tab_session_id)
        elif tab_session_id in waiting_sessions:
            waiting_sessions.remove(tab_session_id)
        else:
            return jsonify({"error": "Tab not found"}), 404

    return jsonify({"message": "Tab removed"})

@app.route("/admin/set_max_connections", methods=["GET", "POST"])
def set_max_connections():
    global max_connections
    if request.method == "POST":
        try:
            max_connections = int(request.form["max_connections"])
            return redirect(url_for("admin"))
        except ValueError:
            return "Valor inválido!", 400
    return render_template("set_max_connections.html", max_connections=max_connections)

if __name__ == "__main__":
    app.run(debug=True)
