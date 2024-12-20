import asyncio
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from prisma import Prisma
import pytz

# Inicializa o Prisma
prisma = Prisma()

# Configura o Flask e o SocketIO
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")


# Função assíncrona para verificar a conexão com o banco de dados
async def check_db_connection():
    try:
        # Tenta buscar um registro para verificar a conexão
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


# Função assíncrona para conectar ao banco de dados
async def connect_to_db():
    try:
        await prisma.connect()
        print("Conexão com o banco de dados estabelecida com sucesso")
        # Verifica se a conexão está funcionando corretamente
        connection_status = await check_db_connection()
        if not connection_status:
            print("Falha na verificação da conexão com o banco de dados.")
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")


# Inicializa o banco de dados
def init_db():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(connect_to_db())


# Rota principal
@app.route("/")
def index():
    return render_template("index.html")


# Função assíncrona para buscar todas as mensagens
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


# Função para obter o IP público do usuário
def get_public_ip():
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0]
    elif request.headers.get('X-Real-IP'):
        ip = request.headers.get('X-Real-IP')
    else:
        ip = request.remote_addr
    return ip


# Função assíncrona para salvar uma mensagem
async def save_message(data):
    try:
        if not prisma.is_connected():
            await prisma.connect()

        # Obter o IP real do usuário
        ip = get_public_ip()

        # Ajustar o timestamp para o fuso horário do Brasil
        brazil_tz = pytz.timezone('America/Sao_Paulo')
        timestamp = datetime.now(brazil_tz)

        message_data = {
            "nickname": data.get("nickname", ""),
            "message": data.get("message", ""),
            "timestamp": timestamp,
            "ip": ip,
            "image": data.get("image", None)  # Usar .get para campo opcional
        }

        print("Dados da mensagem a serem salvos:", message_data)  # Log dos dados a serem salvos

        await prisma.message.create(data=message_data)
        print("Mensagem salva com sucesso:", message_data)
    except Exception as e:
        print(f"Erro ao salvar mensagem: {e}, Dados: {data}")


# Função assíncrona para deletar mensagens antigas
async def delete_old_messages():
    try:
        if not prisma.is_connected():
            await prisma.connect()

        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        await prisma.message.delete_many(where={"timestamp": {"lt": cutoff}})
    except Exception as e:
        print(f"Erro ao deletar mensagens antigas: {e}")


# Evento de conexão de um novo usuário
@socketio.on('connect')
def handle_connect():
    print("Novo usuário conectado")


# Evento de recebimento de mensagem
@socketio.on("message")
def handle_message(data):
    print(f"Mensagem recebida: {data}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Salva a mensagem no banco de dados e deleta as antigas
    try:
        loop.run_until_complete(save_message(data))
        loop.run_until_complete(delete_old_messages())
        # Envia a nova mensagem para todos os usuários conectados
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