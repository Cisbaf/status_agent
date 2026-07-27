# Status Agent

Sistema de monitoramento e histórico de status de agentes de um sistema externo
(discador/PABX), construído com um pipeline de mensageria assíncrona.

## Visão geral da arquitetura

```
API externa (XML)  --(polling 1x/s)-->  Producer  --(RabbitMQ)-->  Consumer  -->  MongoDB
```

- **Producer** (`producer/`): a cada ~1 segundo, consulta uma API externa que
  retorna o status de cada agente em XML. Compara o estado atual de cada
  agente com o último estado conhecido em memória e, ao detectar qualquer
  mudança de campo, publica o registro completo em uma fila do RabbitMQ.
  Erros de conexão/timeout com a API são publicados em uma fila separada de
  erros.
- **RabbitMQ**: fila de mensagens que desacopla a coleta de dados (producer)
  da persistência (consumer). Inclui o plugin de management, com painel web
  para inspecionar filas e mensagens.
- **Consumer** (`consumer/`): consome as mensagens da fila principal e
  mantém, no MongoDB, uma collection por agente (identificada pelo `id` do
  agente). Compara o novo dado com o último registro salvo: se houve mudança
  de status, insere um novo documento (histórico); se foi qualquer outra
  mudança, apenas atualiza o último registro.
- **MongoDB**: persistência do histórico de status por agente. Inclui
  mongo-express como interface web de inspeção.

## Por que RabbitMQ (e não Kafka)

Este projeto usava originalmente Kafka + Zookeeper como mensageria. Dado o
volume de uso real (poucos tópicos, baixíssimo throughput, sem necessidade de
replicação ou múltiplos consumer groups), o Kafka era um exagero de
infraestrutura: consumia ~1GB de heap Java praticamente ocioso, além de exigir
Zookeeper e uma UI dedicada. A migração para RabbitMQ manteve o mesmo padrão
de uso (fila ponto-a-ponto com controle de entrega) com uma fração da pegada
de memória (dezenas de MB a mais de 100MB, contra ~1GB do Kafka), um único
container a menos (sem Zookeeper) e uma interface de management já embutida.

## Requisitos

- Docker e Docker Compose
- Uma URL de API externa válida (XML) com o formato esperado (ver `producer/api.py`)

## Configuração

Copie o arquivo de exemplo e preencha com os valores reais do seu ambiente:

```bash
cp .env.example .env
```

Variáveis disponíveis:

| Variável | Descrição |
|---|---|
| `API_URI` | URL completa do webservice XML, incluindo token de autenticação |
| `RABBITMQ_URI` | URI de conexão AMQP (`amqp://usuario:senha@host:porta/vhost`) |
| `QUEUE_STATUS_AGENT` | Nome da fila principal de status dos agentes |
| `QUEUE_API` | Nome da fila de erros de conexão com a API externa |
| `MONGO_URI` | URI de conexão com o MongoDB |
| `DB_CLIENT` | Nome do banco de dados MongoDB usado |
| `TIMEOUT_API_CONN` | Timeout (segundos) de conexão HTTP com a API externa |
| `TIMEOUT_API_READ` | Timeout (segundos) de leitura HTTP com a API externa |

O `.env` nunca deve ser versionado (já está no `.gitignore`).

## Subindo o ambiente

```bash
docker compose up -d --build
```

Isso sobe 5 serviços:

| Serviço | Porta local | Descrição |
|---|---|---|
| `rabbitmq` | 5672 (AMQP), 15672 (management) | Fila de mensagens |
| `mongo` | 27017 | Banco de dados |
| `mongo-express` | 8081 | Interface web do MongoDB |
| `producer` | — | Coleta e publica mudanças de status |
| `consumer` | — | Consome e persiste no MongoDB |

Painel do RabbitMQ: `http://localhost:15672` (usuário/senha conforme definidos
no `docker-compose.yml`, variáveis `RABBITMQ_DEFAULT_USER`/`RABBITMQ_DEFAULT_PASS`).

Painel do Mongo Express: `http://localhost:8081`.

> Nas portas efetivamente usadas neste ambiente, consulte o `docker-compose.yml`
> — alguns ambientes (ex: paralelos a uma instância de produção na mesma
> máquina) usam portas remapeadas para evitar conflito.

## Persistência de dados (volume do MongoDB)

O `docker-compose.yml` declara o volume do Mongo como `external: true`. Isso
permite apontar este projeto para um volume Docker já existente (por exemplo,
o volume de uma versão anterior da aplicação), preservando o histórico ao
trocar de stack. Se estiver subindo um ambiente novo do zero, crie o volume
manualmente antes (`docker volume create <nome>`) ou ajuste o `name:` do
volume no compose para deixá-lo gerenciado automaticamente.

## Testes

Cada serviço (`producer/` e `consumer/`) tem sua própria suíte de testes
unitários com `pytest`, usando mocks para RabbitMQ, MongoDB e a API externa —
não é necessário nenhum serviço real rodando para testar.

Rodando os testes do producer:

```bash
cd producer
pip install -r requirements.txt
pytest tests/ -v
```

Rodando os testes do consumer:

```bash
cd consumer
pip install -r requirements.txt
pytest tests/ -v
```

Ou, sem instalar nada localmente, via Docker:

```bash
docker run --rm -v "$(pwd)/producer:/app" -w /app python:3.12-slim \
  bash -c "pip install -q -r requirements.txt && python -m pytest tests/ -v"

docker run --rm -v "$(pwd)/consumer:/app" -w /app python:3.12-slim \
  bash -c "pip install -q -r requirements.txt && python -m pytest tests/ -v"
```

O que é coberto pelos testes:

- **`producer/tests/test_utils.py`**: conversão de timezone (UTC -> América/São Paulo).
- **`producer/tests/test_api.py`**: parsing do XML da API, filtro de agentes válidos,
  tratamento de timeout e outros erros de rede.
- **`producer/tests/test_monitoring_status_agent.py`**: detecção de mudanças de
  estado por agente, ignorando campos de timestamp, e registro no producer.
- **`producer/tests/test_control_producer.py`**: publicação de mensagens no
  RabbitMQ, declaração de filas, serialização, retry e reconexão em caso de
  falha de conexão.
- **`consumer/tests/test_agent_controller.py`**: decisão entre inserir novo
  documento (mudança de status) ou atualizar o existente (outras mudanças),
  e carregamento do último registro salvo.
- **`consumer/tests/test_monitoring_controller.py`**: roteamento de mensagens
  para o controller correto por `id` de agente.
- **`consumer/tests/test_main.py`**: callback de consumo de mensagens
  (ack em caso de sucesso, nack + requeue em caso de erro de parsing ou de
  processamento).

## Estrutura do projeto

```
.
├── docker-compose.yml
├── .env.example
├── producer/
│   ├── main.py              # ponto de entrada; monta as dependências e inicia o loop
│   ├── api.py                # consulta e parseia a API externa
│   ├── control_producer.py   # publisher assíncrono para RabbitMQ
│   ├── monitoring.py         # detecção de mudanças de estado por agente
│   ├── utils.py               # conversão de timezone
│   └── tests/
├── consumer/
│   ├── main.py              # ponto de entrada; consome do RabbitMQ
│   ├── monitoring.py         # roteia mensagens para o controller do agente
│   ├── agent.py               # lógica de persistência/histórico no MongoDB
│   └── tests/
```

## Observações operacionais

- O cache do MongoDB (WiredTiger) é limitado explicitamente a 1.5GB
  (`--wiredTigerCacheSizeGB`) e o container tem um teto de memória de 2GB,
  para evitar que o banco consuma toda a RAM disponível conforme o volume de
  dados cresce — importante em servidores que hospedam múltiplas aplicações.
- O producer tenta reconectar ao RabbitMQ automaticamente na inicialização
  (até 10 tentativas) e durante a operação normal, tolerando indisponibilidade
  temporária do broker.
- O consumer usa confirmação manual de mensagens (`ack`/`nack` com requeue),
  então uma falha ao processar uma mensagem não a descarta — ela volta para
  a fila para nova tentativa.
