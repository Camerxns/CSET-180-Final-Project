from flask import Flask, render_template, request, session, redirect, url_for
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from flask_sqlalchemy import SQLAlchemy
from models import ChatMessages
from environs import Env


app = Flask(__name__)
app.config["SECRET_KEY"] = "hjhjsdahhds"
socketio = SocketIO(app)



env = Env()
env.read_env()

db = SQLAlchemy()
MYSQL_USERNAME = env("MYSQL_USERNAME")
MYSQL_PASSWORD = env("MYSQL_PASSWORD")
MYSQL_HOST = env("MYSQL_HOST")
MYSQL_PORT = env.int("MYSQL_PORT")
MYSQL_DATABASE = "CSET180_FINAL_PROJECT"

app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"
db.init_app(app)


rooms = {}


def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += str(random.randint(0, 9))

        if code not in rooms:
            break

    return code


# def write_to_text_file(username, room, message):
#     with open("chatlog.txt", "a") as file:
#         file.write(f"Username: {username}, Room: {room}, Message: {message}\n")

@app.route("/", methods=["POST", "GET"])
def home():
    session.clear()
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("chat2.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("chat2.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("chat2.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room"))

    return render_template("chat2.html")


@app.route("/room")
def room():
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("chat2"))

    return render_template("chatroom.html", code=room, messages=rooms[room]["messages"])


@socketio.on("message")
def message(data):
    name = session.get('name')
    room = session.get("room")
    if room not in rooms:
        return

    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")
    chat_message = ChatMessages(user_id=name, message=data, chat_id=room)
    db.session.add(chat_message)
    db.session.commit()
    print('Message comitted')


@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")


@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]

    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")



if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)