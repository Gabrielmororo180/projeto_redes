# Transferência Confiável de Arquivos sobre UDP

Projeto da disciplina de Redes de Computadores para implementar transferência confiável de arquivos usando **UDP**, recriando manualmente mecanismos normalmente oferecidos pelo **TCP**, como segmentação, ordenação, verificação de integridade e retransmissão.

## Objetivo

Desenvolver uma aplicação **cliente-servidor** capaz de transferir arquivos usando **UDP**, implementando mecanismos de confiabilidade no nível da aplicação.

## Tecnologias utilizadas

- Python 3
- API de sockets (`socket`)
- UDP (`SOCK_DGRAM`)
- Threads no servidor para múltiplos clientes
- `CRC32` para integridade por segmento
- `SHA-256` para integridade do arquivo final

## Estrutura do projeto

```text
Projeto1/
├── client.py
├── server.py
├── files/
│   ├── arquivo1.txt
│   ├── arquivo2.txt
│   └── 10mb2.txt
├── downloads/
└── README.md
```

## Funcionalidades implementadas

- Uso direto da API de sockets, sem bibliotecas de abstração UDP
- Protocolo de aplicação próprio
- Transferência de arquivos pequenos e grandes
- Segmentação em chunks
- Numeração de sequência por segmento
- Verificação de integridade por **CRC32** em cada segmento
- Verificação de integridade final por **SHA-256**
- Simulação de perda de pacotes no cliente
- Recuperação de perdas com **NACK**
- Atendimento de múltiplos clientes simultâneos com threads

## Como executar

### 1. Iniciar o servidor

```bash
python server.py
```

O servidor fica escutando em:

- IP: `0.0.0.0`
- Porta: `12000`

### 2. Executar o cliente

```bash
python client.py
```

O cliente solicita:

- nome do arquivo
- sequências a serem descartadas para simular perda

Exemplo:

```text
Nome do arquivo: 10mb2.txt
Seq para perder (ex: 1,3,7) ou vazio: 1,2,6
```

## Configuração atual

No código atual, o cliente está configurado para acessar:

- IP do servidor: `127.0.0.1`
- Porta do servidor: `12000`

Esses valores estão definidos no próprio arquivo `client.py`.

## Protocolo de aplicação

O protocolo definido para a comunicação é textual.

### Requisição de arquivo

```text
GET /nome_arquivo
```

### Resposta de sucesso

```text
OK|transfer_id|file_size|chunk_size|total_chunks|sha256
```

Campos:

- `transfer_id`: identificador único da transferência
- `file_size`: tamanho do arquivo em bytes
- `chunk_size`: tamanho de cada segmento
- `total_chunks`: total de segmentos
- `sha256`: hash SHA-256 do arquivo completo

### Pacote de dados

```text
DATA|transfer_id|seq|total_chunks|crc32|payload_b64
```

Campos:

- `transfer_id`: identificador da transferência
- `seq`: número de sequência do segmento
- `total_chunks`: quantidade total de segmentos
- `crc32`: checksum CRC32 do segmento
- `payload_b64`: conteúdo do segmento codificado em Base64

### Final de envio

```text
END|transfer_id
```

### Solicitação de retransmissão

```text
NACK|transfer_id|seq1,seq2,seq3
```

### Erros

```text
ERR|arquivo_nao_encontrado
ERR|arquivo_invalido
ERR|requisicao_invalida
```

## Funcionamento geral

### 1. Requisição

O cliente envia `GET /nome_arquivo` ao servidor.

### 2. Metadados da transferência

O servidor responde com `OK`, informando:

- tamanho do arquivo
- tamanho do chunk
- total de chunks
- hash SHA-256 final

### 3. Segmentação

O arquivo é dividido em segmentos de tamanho fixo:

- `CHUNK_SIZE = 1024` bytes

Cada segmento recebe um número de sequência (`seq`).

### 4. Integridade por segmento

Cada chunk enviado possui um **CRC32** calculado no servidor.

Ao receber um segmento, o cliente:

1. decodifica o conteúdo Base64
2. recalcula o CRC32 localmente
3. compara com o CRC32 recebido
4. aceita o chunk somente se a verificação for válida

### 5. Ordenação

Os segmentos recebidos são armazenados usando o número de sequência como chave.

Depois, o cliente monta o arquivo final escrevendo os chunks na ordem:

```text
0, 1, 2, 3, ...
```

### 6. Detecção de perdas

Quando alguns segmentos não são recebidos, o cliente identifica as sequências faltantes e envia um `NACK`.

### 7. Retransmissão

Ao receber `NACK`, o servidor retransmite apenas os chunks solicitados.

### 8. Validação final

Após montar o arquivo, o cliente calcula o **SHA-256** do arquivo salvo e compara com o hash informado pelo servidor no início da transferência.

## Segmentação e relação com MTU

O tamanho do segmento usado é **1024 bytes**.

A escolha desse valor busca evitar fragmentação excessiva, pois o MTU típico em redes Ethernet costuma ser próximo de **1500 bytes** no nível IP. Como o pacote UDP ainda carrega:

- cabeçalho IP
- cabeçalho UDP
- cabeçalho do protocolo de aplicação
- conteúdo codificado

usar um chunk menor torna a transmissão mais segura e reduz problemas causados por fragmentação.

## Mecanismos de confiabilidade implementados

### Ordenação

- Cada pacote possui número de sequência
- O cliente usa esse número para armazenar e reconstruir o arquivo em ordem

### Integridade

- **CRC32 por segmento**
- **SHA-256 no arquivo completo**

### Recuperação de perdas

- O cliente pode simular perda descartando pacotes específicos
- Os pacotes faltantes são detectados ao final de cada rodada
- O cliente envia `NACK` com as sequências ausentes
- O servidor retransmite apenas os segmentos pedidos

## Simulação de perda

A perda é simulada no cliente, informando as sequências que devem ser descartadas.

Exemplo:

```text
Seq para perder (ex: 1,3,7) ou vazio: 1,2,6
```

Durante a execução, o cliente mostra:

```text
Descartado seq: 1
Descartado seq: 2
Descartado seq: 6
```

Depois disso, ele envia `NACK` para recuperar os segmentos faltantes.

## Suporte a múltiplos clientes

O servidor usa **threads** para atender clientes simultaneamente.

Cada transferência recebe um `transfer_id`, permitindo associar corretamente os `NACKs` ao arquivo e ao cliente correspondente.

## Cenários de teste

- Transferência de pelo menos dois arquivos diferentes
- Transferência de arquivo grande com mais de 10 MB
- Simulação de perda de pacotes
- Retransmissão seletiva com `NACK`
- Solicitação de arquivo inexistente
- Cliente iniciado antes do servidor
- Servidor interrompido durante a transferência
- Dois clientes simultâneos requisitando arquivos diferentes

## Exemplos de uso

### Download normal

```bash
python client.py
```

```text
Nome do arquivo: arquivo1.txt
Seq para perder (ex: 1,3,7) ou vazio:
```

### Download com perda simulada

```bash
python client.py
```

```text
Nome do arquivo: 10mb2.txt
Seq para perder (ex: 1,3,7) ou vazio: 1,2,6
```

## Tratamento de erros

### Arquivo inexistente

Se o arquivo solicitado não existir, o servidor envia:

```text
ERR|arquivo_nao_encontrado
```

O cliente exibe a mensagem de erro e encerra a execução.

### Cliente antes do servidor

Se o cliente for iniciado antes do servidor, ocorre timeout e a aplicação informa:

```text
Servidor não respondeu.
```

### Servidor interrompido durante a transferência

Se o servidor cair durante a transmissão, o cliente continua tentando recuperar os segmentos faltantes até atingir o limite de rodadas. Caso não consiga completar o arquivo, a transferência é encerrada com erro.

## Pontos importantes para apresentação

Durante a apresentação do projeto, é importante demonstrar:

- execução do servidor UDP
- execução de um ou mais clientes UDP
- requisição de pelo menos dois arquivos diferentes
- transferência de arquivo grande
- segmentação em chunks
- uso de números de sequência
- verificação de integridade com CRC32 e SHA-256
- perda simulada
- retransmissão via NACK
- tratamento de arquivo inexistente
- cliente iniciado antes do servidor
- servidor interrompido durante a transferência
- dois clientes simultâneos

## Limitações atuais

- O IP e a porta do servidor estão fixos no código do cliente
- O protocolo é textual e simples, voltado ao objetivo didático do trabalho
- Não há controle de congestionamento
- Não há janela deslizante
- Não há ACK positivo individual

## Conclusão

O projeto demonstra como implementar confiabilidade sobre UDP no nível da aplicação, utilizando segmentação, ordenação, verificação de integridade e retransmissão seletiva. Dessa forma, parte do comportamento normalmente fornecido pelo TCP é recriado manualmente com UDP.

## Autores

Preencha aqui com os nomes do grupo.
