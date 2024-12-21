#!/bin/bash

# Instale as dependências
pip install -r requirements.txt

# Gere o Prisma Client
npx prisma generate

# Inicie a aplicação
exec python app.py