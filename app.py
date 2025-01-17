import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from prisma import Prisma
import pytz

prisma = Prisma()

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

async def check_db_connection():
    try:
        result = await prisma.message.find_first()
        if result is not None:
            print("Conexão com o banco de dados está funcionando corretamente.")
            return True
        else:
            print("Conexão com o banco de dados estabelecida, mas nenhuma mensagem encontrada.")
            return True
    except Exception as e:
        print(f"Erro ao verificar a conexão com o banco de dados: {e}")
        return False

async def connect_to_db():
    try:
        await prisma.connect()
        print("Conexão com o banco de dados estabelecida com sucesso")
        connection_status = await check_db_connection()
        if not connection_status:
            print("Falha na verificação da conexão com o banco de dados.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")

def init_db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_to_db())

@app.route("/")
def index():
    return render_template("index.html")

async def fetch_all_messages():
    try:
        if not prisma.is_connected():
            await prisma.connect()

        messages = await prisma.message.find_many(order={"timestamp": "asc"})
        return [
            {"nickname": msg.nickname, "message": msg.message, "image": msg.image, "ip": msg.ip}
            for msg in messages
        ]
    except Exception as e:
        print(f"Erro ao buscar mensagens: {e}")
        return []

def get_public_ip():
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    return ip

async def save_message(data):
    try:
        if not prisma.is_connected():
            await prisma.connect()

        ip = get_public_ip()
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        timestamp = datetime.now(brazil_tz)

        message_data = {
            "nickname": data.get("nickname", ""),
            "message": data.get("message", ""),
            "timestamp": timestamp,
            "ip": ip,
            "image": data.get("image", None)
        }

        print("Dados da mensagem a serem salvos:", message_data)

        await prisma.message.create(data=message_data)
        print("Mensagem salva com sucesso:", message_data)
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}, Dados: {data}")

async def delete_old_messages():
    try:
        if not prisma.is_connected():
            await prisma.connect()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        await prisma.message.delete_many(where={"timestamp": {"lt": cutoff}})
    except Exception as e:
        print(f"Erro ao deletar mensagens antigas: {e}")

@socketio.on('connect')
def handle_connect():
    print("Novo usuário conectado")

@socketio.on("message")
def handle_message(data):
    print(f"Mensagem recebida: {data}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(save_message(data))
        loop.run_until_complete(delete_old_messages())
        emit("message", data, broadcast=True)
    except Exception as e:
        print(f"Erro ao processar mensagem: {e}")

if __name__ == "__main__":
    print("Iniciando o servidor Flask com SocketIO...")
    init_db()
    try:
        socketio.run(app, host="0.0.0.0", port=5000)
    except Exception as e:
        print(f"Erro ao iniciar o servidor: {e}")