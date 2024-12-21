@echo off

:: Instale as dependências
pip install -r requirements.txt

:: Gere o Prisma Client
prisma generate

:: Inicie a aplicação
python app.py