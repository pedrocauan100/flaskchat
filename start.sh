#!/bin/bash

# Instale as dependências
pip install -r requirements.txt

# Gere o Prisma Client
prisma generate

# Inicie a aplicação
exec uvicorn app:app --host 0.0.0.0 --port 5000