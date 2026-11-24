# UrbInclusiva — API (Backend)

API do **UrbInclusiva**, plataforma colaborativa de mapeamento de barreiras urbanas em Cuiabá e na Baixada Cuiabana. Pessoas reportam obstáculos (calçadas quebradas, falta de rampa, piso tátil danificado etc.) com **foto, categoria e GPS**, visualizam os pinos no mapa e confirmam se o obstáculo ainda existe. Os mapas se atualizam em **tempo real** para quem está na região.

Projeto do **Grupo 04 — Mobilidade** (Conecta Jovem). O aplicativo mobile (Flutter) fica em outro repositório; este contém **apenas o backend**.

---

## Sumário

1. [Tecnologias](#tecnologias)
2. [Como o projeto funciona](#como-o-projeto-funciona)
3. [Estrutura de pastas](#estrutura-de-pastas)
4. [Banco de dados](#banco-de-dados)
5. [Endpoints](#endpoints)
6. [Como rodar](#como-rodar)
7. [Migrations](#migrations)
8. [Acesso externo (ngrok)](#acesso-externo-ngrok)
9. [Regras de negócio](#regras-de-negócio)
10. [Integrantes do grupo](#integrantes-do-grupo)

---

## Tecnologias

| Camada | Tecnologia |
|---|---|
| API | Python + [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn (assíncrona) |
| Banco de dados | PostgreSQL com extensão PostGIS |
| Acesso ao banco | SQLAlchemy assíncrono + asyncpg + GeoAlchemy2 |
| Migrations | Alembic (usa a conexão síncrona, via psycopg2) |
| Armazenamento de fotos | Supabase Storage (bucket público `fotos`) |
| Tempo real | WebSockets do FastAPI (biblioteca `websockets`) |
| Exposição pública | ngrok (HTTPS e WSS) |

---

## Como o projeto funciona

```
 App Flutter ──HTTPS / WSS──▶  API FastAPI (este repositório)
                                │        │
                                │        └──▶ Supabase Storage (fotos)
                                │
                                └──▶ PostgreSQL/PostGIS (rede da LogLab, via VPN)
```

1. O app envia a **foto** (`POST /fotos`). A API valida o arquivo, envia ao Supabase Storage e devolve a **URL pública**.
2. O app registra a **ocorrência** (`POST /ocorrencias`) com categoria, coordenadas e a URL da foto. A API grava no banco e avisa por WebSocket os aparelhos que estão na região.
3. O app busca no mapa as ocorrências **ativas num raio** ao redor do usuário (`GET /ocorrencias`), com filtro opcional por categoria.
4. Outras pessoas respondem **"Ainda está aí?"** (`POST /ocorrencias/{id}/validacoes`). Com duas respostas "Não está mais" de aparelhos diferentes, o pino sai do mapa e a API avisa por WebSocket quem está na região.

O usuário é **anônimo**: não há login nem senha. Cada aparelho é identificado pelo header `X-Device-Id`, que a API transforma em **hash SHA-256** antes de gravar. O identificador original nunca é armazenado.

---

## Estrutura de pastas

```
back_acessibilidade_urbana/
├── .env.example            # modelo das variáveis de ambiente (sem valores)
├── .gitignore
├── README.md
├── requirements.txt        # dependências Python
├── alembic.ini             # configuração do Alembic
├── alembic/
│   ├── env.py              # liga o Alembic ao models.py e à conexão do banco
│   ├── script.py.mako      # modelo dos arquivos de migration
│   └── versions/           # migrations (versionadas no Git)
└── app/
    ├── __init__.py
    ├── main.py             # cria o app FastAPI e inclui as rotas
    ├── database.py         # conexões com o banco (síncrona e assíncrona) e Base
    ├── models.py           # tabelas do banco
    ├── schemas.py          # formatos de entrada e saída da API
    ├── dependencies.py     # sessão do banco, aparelho atual e limite de envios
    ├── routes/
    │   ├── __init__.py
    │   ├── fotos.py        # upload de fotos
    │   ├── ocorrencias.py  # criar ocorrência e buscar por raio
    │   ├── validacoes.py   # "Ainda está aí?"
    │   ├── realtime.py     # endpoint WebSocket
    │   └── saude.py        # teste de conexão com o banco
    └── services/
        ├── __init__.py
        ├── storage.py              # upload de imagens no Supabase Storage
        ├── ocorrencia_service.py   # criação e busca por raio de ocorrências
        ├── validacao_service.py    # regras do "Ainda está aí?" e remoção do pino
        └── connection_manager.py   # controle dos WebSockets conectados
```

| Item | Responsabilidade |
|---|---|
| `main.py` | Cria o `FastAPI()` e registra os routers. |
| `database.py` | Lê o `.env` e cria as duas conexões com o banco: a **síncrona** (Alembic) e a **assíncrona** (API). Define também a `Base`. |
| `models.py` | Classes das tabelas (com construtor). |
| `schemas.py` | Define o que a API aceita e devolve em JSON (Pydantic), inclusive as mensagens do WebSocket. |
| `dependencies.py` | Fábrica de sessões assíncronas, `get_db`, `dispositivo_atual` (hash do `device_id`) e `limitar_envios` (3 por hora). |
| `routes/` | Camada HTTP e WebSocket: recebe os dados, chama os services e responde. |
| `services/` | Regras de negócio e integrações externas. |
| `alembic/` | Histórico de alterações do banco. |

---

## Banco de dados

| Tabela | Para que serve | Campos principais |
|---|---|---|
| `usuario` | Um registro por aparelho | `device_hash` (SHA-256, chave primária) |
| `categoria_obstaculo` | Lista fechada de 11 categorias | `id`, `slug`, `nome` |
| `ocorrencia` | Os pinos do mapa | `id` (UUID), `device_hash`, `categoria_id`, `localizacao` (PostGIS), `foto_chave`, `status`, `criado_em`, `removido_em` |
| `validacao` | Respostas do "Ainda está aí?" | `id` (UUID), `ocorrencia_id`, `device_hash`, `ainda_existe`, `criado_em` |

- **`localizacao`** é `geography(Point, 4326)`: ponto em latitude/longitude (GPS), com distâncias em metros.
- **`status`** é booleano: `True` = ocorrência ativa, `False` = removida do mapa.
- **`foto_chave`** guarda o nome do arquivo no bucket; a URL pública é montada pela API.
- **`ON DELETE CASCADE`:** apagar um `usuario` apaga as ocorrências e votos dele; apagar uma `ocorrencia` apaga as validações dela.
- **`UNIQUE (ocorrencia_id, device_hash)`:** um aparelho tem um único voto por ocorrência.
- **Índices:** um índice espacial (GiST) parcial, apenas das ocorrências ativas, para a busca por raio; e um índice em `(device_hash, criado_em)` para o limite de envios.

### Categorias

As 11 categorias fixas (`slug`) são inseridas por migration: `calcada_quebrada`, `piso_tatil`, `rampa_ausente`, `rampa_inadequada`, `degrau_elevado`, `obstaculo_fixo`, `bloqueio_temporario`, `semaforo_sonoro`, `boca_de_lobo`, `obra_sem_rota` e `outra_barreira`.

---

## Endpoints

Documentação interativa (Swagger): `http://127.0.0.1:8000/docs`

| Método | Rota | Header `X-Device-Id` | Descrição |
|---|---|:---:|---|
| `POST` | `/fotos` | não | Envia uma imagem (campo `foto`, JPEG/PNG/WebP, até 5 MB) e devolve `{"url": "..."}` |
| `POST` | `/ocorrencias` | sim (limite de 3 por hora) | Registra uma ocorrência |
| `GET` | `/ocorrencias` | não | Lista ocorrências ativas num raio, com filtro por categorias |
| `POST` | `/ocorrencias/{id}/validacoes` | sim | Responde "Ainda está aí?" |
| `WS` | `/ws` | não | Atualização do mapa em tempo real |
| `GET` | `/saude/banco` | não | Testa a comunicação com o banco |

### `POST /fotos`

Corpo `multipart/form-data` com o arquivo no campo `foto`.

```json
{ "url": "https://<projeto>.supabase.co/storage/v1/object/public/fotos/<arquivo>.jpg" }
```

Respostas: `200` (enviada) e `400` (formato não permitido ou arquivo maior que 5 MB).

### `POST /ocorrencias`

```json
{
  "category": "rampa_ausente",
  "latitude": -15.6014,
  "longitude": -56.0979,
  "photo_url": "https://<projeto>.supabase.co/storage/v1/object/public/fotos/<arquivo>.jpg"
}
```

Respostas: `201` (criada, devolve o mesmo formato de cada item do `GET`), `401` (header ausente ou inválido), `422` (categoria inexistente, URL de foto que não é do bucket ou dados inválidos) e `429` (limite de envios por hora atingido).

### `GET /ocorrencias`

| Parâmetro | Descrição |
|---|---|
| `lat`, `lng` | Centro da busca |
| `raio_m` | Raio em metros (máximo de 8.000) |
| `categorias` | Opcional. Lista de `slug` separados por vírgula (ex.: `rampa_ausente,piso_tatil`) |

Devolve até 300 ocorrências ativas, das mais próximas para as mais distantes:

```json
[
  {
    "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
    "category": "rampa_ausente",
    "latitude": -15.6014,
    "longitude": -56.0979,
    "photo_url": "https://<projeto>.supabase.co/storage/v1/object/public/fotos/<arquivo>.jpg",
    "created_at": "2026-12-01T14:32:10Z"
  }
]
```

Respostas: `200` e `422` (parâmetros inválidos, como raio acima de 8.000 m).

### `POST /ocorrencias/{id}/validacoes`

```json
{ "still_exists": false }
```

Resposta `200`:

```json
{
  "ocorrencia_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "still_exists": false,
  "ocorrencia_ativa": true
}
```

`ocorrencia_ativa` fica `false` quando esse voto fez o pino sair do mapa. Cada aparelho tem um único voto por ocorrência: se votar de novo, o voto anterior é atualizado.

Outras respostas: `401` (header ausente ou inválido), `403` (o autor não pode votar no próprio pino) e `404` (ocorrência inexistente ou já removida).

### `WS /ws`

Depois de conectar, o app envia a área que está vendo e reenvia sempre que o mapa se move:

```json
{ "latitude": -15.6014, "longitude": -56.0979, "radius_m": 3000 }
```

O raio máximo é de 8.000 m. A API responde:

```json
{ "event": "area_set" }
```

ou, se o JSON ou a área forem inválidos (a conexão continua aberta):

```json
{ "event": "error", "detail": "Área inválida" }
```

A partir daí, a API envia **apenas os eventos de ocorrências dentro da área informada**:

```json
{ "event": "occurrence_created", "data": { "id": "...", "category": "...", "latitude": 0, "longitude": 0, "photo_url": "...", "created_at": "..." } }
{ "event": "occurrence_removed", "data": { "id": "..." } }
```

Observações:

- A API aceita até **200 conexões simultâneas**. Acima disso, a conexão é encerrada com o código `1013` (tente novamente mais tarde).
- O WebSocket só entrega as novidades enquanto está aberto. Ao **reconectar**, o app deve refazer o `GET /ocorrencias` para sincronizar o mapa.
- Em produção a conexão usa `wss://`.

---

## Como rodar

### Pré-requisitos

- **Python 3.11 ou superior** e **Git**
- **VPN Sangfor EasyConnect conectada**: o banco fica em rede privada e só responde com a VPN ligada. O passo a passo e as credenciais estão no **POP-CONECTA-G04** (documento interno; as credenciais não devem ser colocadas neste repositório)
- Um projeto no **Supabase** com um bucket **público** chamado `fotos`

### Passo a passo

**1. Clone o repositório**

```bash
git clone <URL-DO-REPOSITORIO>
cd back_acessibilidade_urbana
```

**2. Crie e ative o ambiente virtual**

```powershell
# Windows (PowerShell)
python -m venv venv
venv\Scripts\activate
```

```bash
# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

**3. Instale as dependências**

```bash
pip install -r requirements.txt
```

**4. Configure o `.env`**

Copie o `.env.example` para `.env` e preencha:

| Variável | O que é |
|---|---|
| `DB_HOST` | Endereço do servidor PostgreSQL |
| `DB_PORT` | Porta do banco |
| `DB_NAME` | Nome do banco |
| `DB_USER` | Usuário do banco |
| `DB_PASSWORD` | Senha do banco (entre aspas simples) |
| `SUPABASE_URL` | URL do projeto, no formato `https://<id>.supabase.co` |
| `SUPABASE_KEY` | Chave secreta do Supabase (somente no backend) |

**5. Crie as tabelas e as categorias**

```bash
alembic upgrade head
```

**6. Suba a API** (sempre a partir da raiz do projeto)

```bash
uvicorn app.main:app
```

Use **um único processo**: as conexões WebSocket ficam na memória da API, então não suba com vários workers.

**7. Confira**

Abra `http://127.0.0.1:8000/docs` e execute `GET /saude/banco`. O esperado é `{"banco": "ok", "postgis": true}`.

---

## Migrations

| Comando | O que faz |
|---|---|
| `alembic upgrade head` | Aplica todas as migrations pendentes |
| `alembic revision --autogenerate -m "mensagem"` | Gera uma migration a partir das mudanças no `models.py` |
| `alembic current` | Mostra a versão atual do banco |
| `alembic downgrade -1` | Desfaz a última migration |

Há duas migrations: a primeira cria as quatro tabelas e os índices, e a segunda insere as 11 categorias iniciais. A primeira exige a extensão **PostGIS** habilitada no banco.

O Alembic usa a conexão **síncrona** (`psycopg2`) e ignora a tabela `spatial_ref_sys`, que pertence ao PostGIS.

---

## Acesso externo (ngrok)

Para o app no celular acessar a API rodando na máquina da equipe, a API é exposta por um túnel do **ngrok**, com URL pública fixa e HTTPS/WSS.

```powershell
ngrok config add-authtoken SEU_TOKEN    # uma única vez
ngrok http 8000                         # com a API e a VPN ligadas
```

O domínio exibido pelo ngrok é o endereço da API configurado no app (`https://...` para as rotas e `wss://.../ws` para o tempo real). A máquina precisa ficar ligada, com a VPN conectada, enquanto a API estiver em uso.

---

## Regras de negócio

- **Anonimato (RF01, RNF04):** sem login. O `device_id` é transformado em hash SHA-256 no backend; nenhum dado pessoal é coletado ou exposto.
- **Limite de envios (RNF05):** no máximo **3 ocorrências por hora** por aparelho. Acima disso, a API responde `429`.
- **Foto obrigatória:** toda ocorrência tem foto, categoria e coordenadas GPS. A URL da foto precisa ser de um arquivo enviado por `POST /fotos`.
- **Validação colaborativa (RF06):** o autor **não** responde ao próprio pino. Cada aparelho tem um voto por ocorrência, que pode ser alterado. Quando **dois aparelhos diferentes** respondem "Não está mais", o pino é removido do mapa (`status = False`).
- **Filtro por categoria (RF07):** a busca por raio aceita uma ou mais categorias.
- **Tempo real (RF08):** novos pinos e remoções são enviados por WebSocket aos usuários conectados na região.
- **Privacidade nos logs:** a API não registra o identificador do aparelho nem as coordenadas.
- **Segurança de comunicação (RNF05):** todo o tráfego externo usa HTTPS/WSS.

---

## Integrantes do grupo

**Grupo 04 — Mobilidade** · Projeto UrbInclusiva · Conecta Jovem

| Nome | Função | GitHub |
|---|---|---|
| Luciano Tadeu Simões Simplicio Junior | Líder da equipe | [@Luciano-Tadeu](https://github.com/Luciano-Tadeu) |
| Ágatha Cristina Campos de Matos | Líder de Gestão | [@usuario](https://github.com/usuario) |
| João Pedro Cunha Andrade Pereira | Testes | [@usuario](https://github.com/usuario) |
| Josué Mendonça Neres | Backend e Integração | [@usuario](https://github.com/usuario) |
| Emelly A. | Pesquisador de UX | [@usuario](https://github.com/usuario) |