from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading

app = Flask(__name__)

# Dados simulados
events = [
    {"id": 1, "name": "Workshop de React", "date": "15/11/2024", "slots": 20},
    {"id": 2, "name": "Conferência de UX", "date": "20/11/2024", "slots": 15},
    {"id": 3, "name": "Hackathon 2024", "date": "25/11/2024", "slots": 30},
    {"id": 4, "name": "DevOps Summit", "date": "30/11/2024", "slots": 25},
    {"id": 5, "name": "AI Conference", "date": "05/12/2024", "slots": 40},
]

registrations = []  # Inscrições

# Lock para evitar condições de corrida
event_lock = threading.Lock()

# Semáforos para gerenciar vagas disponíveis em eventos
event_semaphores = {event["id"]: threading.Semaphore(event["slots"]) for event in events}

# Rota principal
@app.route("/")
def index():
    return render_template("index.html", events=events)

# Rota para inscrição em eventos
@app.route("/register/<int:event_id>", methods=["GET", "POST"])
def register(event_id):
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Evento não encontrado!", 404

    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]

        # Usar o semáforo para garantir acesso às vagas disponíveis
        if event_semaphores[event_id].acquire(blocking=False):  # Verifica se há vagas
            with event_lock:  # Garante manipulação segura dos dados do evento
                if event["slots"] > 0:
                    registrations.append({"name": name, "email": email, "event": event["name"]})
                    event["slots"] -= 1
                    return redirect(url_for("index"))
                else:
                    # Libera o semáforo caso não tenha mais vagas (inconsistência evitada)
                    event_semaphores[event_id].release()
                    return "Vagas esgotadas!", 400
        else:
            return "Vagas esgotadas!", 400

    return render_template("register.html", event=event)

# Rotas do administrador (manutenção de outras funcionalidades)
@app.route("/admin")
def admin():
    """Exibe a interface para o administrador gerenciar eventos."""
    return render_template("admin.html", events=events)

@app.route("/admin/add", methods=["GET", "POST"])
def add_event():
    """Adiciona um novo evento."""
    if request.method == "POST":
        name = request.form["name"]
        date = request.form["date"]
        slots = int(request.form["slots"])

        with event_lock:
            new_event = {
                "id": len(events) + 1,
                "name": name,
                "date": date,
                "slots": slots,
            }
            events.append(new_event)
            event_semaphores[new_event["id"]] = threading.Semaphore(slots)  # Cria semáforo para o novo evento
        return redirect(url_for("admin"))

    return render_template("add_event.html")

@app.route("/admin/edit/<int:event_id>", methods=["GET", "POST"])
def edit_event(event_id):
    """Edita um evento existente."""
    event = next((e for e in events if e["id"] == event_id), None)
    if not event:
        return "Evento não encontrado!", 404

    if request.method == "POST":
        with event_lock:
            event["name"] = request.form["name"]
            event["date"] = request.form["date"]
            new_slots = int(request.form["slots"])
            event["slots"] = new_slots
            # Atualiza o semáforo para refletir o número de slots
            event_semaphores[event_id] = threading.Semaphore(new_slots)
        return redirect(url_for("admin"))

    return render_template("edit_event.html", event=event)

@app.route("/admin/delete/<int:event_id>", methods=["POST"])
def delete_event(event_id):
    """Remove um evento."""
    global events
    with event_lock:
        events = [e for e in events if e["id"] != event_id]
        event_semaphores.pop(event_id, None)  # Remove o semáforo associado
    return redirect(url_for("admin"))

if __name__ == "__main__":
    app.run(debug=True)
