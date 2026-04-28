# Transferência de Arquivos Confiável sobre UDP — Estado Atual

Implementado o servidor UDP básico que responde a requisições `GET /<arquivo>` e envia metadados da transferência (ID, tamanho, chunk, total, SHA-256). Cliente de teste envia `GET` e recebe a primeira resposta (`OK` ou `ERR`).

- server.py
  - Escuta UDP em 0.0.0.0:12000
  - Valida requisição `GET /<nome>`
  - Proteção contra path traversal (`safe_resolve`)
  - Calcula SHA-256 do arquivo (`sha256_file`)
  - Envia mensagem `OK|transfer_id|file_size|CHUNK_SIZE|total_chunks|file_hash`
  - Envia `END|transfer_id` ao final
- client.py
  - Envia `GET /arquivo.txt`
  - Recebe e mostra resposta do servidor (OK ou ERR)
- Estrutura esperada: pasta `files/` ao lado dos scripts para colocar arquivos a serem servidos

## Protocolo

- Cliente → Servidor: `GET /nome_arquivo`
- Servidor → Cliente:
  - `OK|transfer_id|file_size|chunk_size|total_chunks|sha256`
  - `DATA|...` (ainda não enviado nesta versão simplificada)
  - `END|transfer_id`
  - `ERR|mensagem` (erros: requisição inválida, arquivo inválido, não encontrado)
