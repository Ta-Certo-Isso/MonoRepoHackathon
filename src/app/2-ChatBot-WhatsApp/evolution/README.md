# Evolution API via Docker Compose

Para manter o WhatsApp Chatbot no Azure, mas hospedar a Evolution API em um ambiente próprio (VM, VPS, etc.), basta usar o `docker-compose.yml` deste diretório. Ele segue a recomendação da documentação v2: banco relacional obrigatório (Postgres/MySQL) e Redis para cache/sessões ([instalação Docker](https://doc.evolution-api.com/v2/pt/install/docker), [variáveis](https://doc.evolution-api.com/v2/pt/env), [requisitos de banco e Redis](https://doc.evolution-api.com/v2/pt/requirements/database), [https://doc.evolution-api.com/v2/pt/requirements/redis](https://doc.evolution-api.com/v2/pt/requirements/redis)).

## Passo a passo

1. Copie o exemplo de variáveis:
   ```bash
   cp env.evolution.example .env.evolution
   ```
2. Edite `.env.evolution` e ajuste:
   - `POSTGRES_*`: credenciais do banco (o compose já provisiona o Postgres).
   - `SERVER_URL`: URL pública onde a Evolution ficará acessível (use HTTPS).
   - `AUTHENTICATION_API_KEY`: gere uma chave segura; use o mesmo valor em `EVOLUTION_API_KEY` no Nichols.
   - `WEBHOOK_GLOBAL_URL`: mantenha apontando para `https://hackathonopenai-api.azurewebsites.net/webhook/evolution`.
3. Suba os serviços (Postgres + Redis + Evolution):
   ```bash
   docker compose up -d --force-recreate
   ```
4. Exponha a API com ngrok (ou outro túnel) e atualize `SERVER_URL`:
   ```bash
   ngrok http 8080
   curl http://127.0.0.1:4040/api/tunnels | jq -r '.tunnels[0].public_url'
   # substitua SERVER_URL no .env e rode docker compose up -d novamente
   ```
5. Abra o log para capturar o QR Code:
   ```bash
   docker compose logs -f evolution_api
   ```
6. Depois de parear a instância, configure as variáveis no App Service do bot (`EVOLUTION_BASE_URL`, `EVOLUTION_API_KEY`, `EVOLUTION_INSTANCE`).

> **Importante:** A Evolution ainda exige Postgres/MySQL mesmo quando o Mongo está habilitado (o container executa migrações Prisma na inicialização). Por isso o compose inclui o Postgres e exporta sua connection string automaticamente.

## Portas e TLS

- Por padrão o serviço escuta em `8080`. Use um proxy reverso (Nginx, Caddy, Traefik) ou um Load Balancer do seu provedor para expor HTTPS público.
- Certifique-se de atualizar `SERVER_URL` com o domínio final; essa URL é usada nos payloads enviados ao bot e nos links de QR code.

## Backup / Dados

- O volume `postgres_data` persiste os dados do Postgres (instâncias, histórico, etc.). Provisione snapshots ou backups conforme o provedor.
- O Redis deste compose é efêmero (não persiste em disco); para ambientes de produção, considere Redis gerenciado ou inclua um volume dedicado.
- Para habilitar o armazenamento opcional em Mongo (mensagens, contatos, etc.), use o cluster exposto pelo IaC no Azure (`mongodb://mongoadmin:<senha>@<label>.<region>.azurecontainer.io:27017/?authSource=admin&tls=false`) e preencha `DATABASE_ENABLED=true`, `DATABASE_PROVIDER=mongodb`, `DATABASE_CONNECTION_URI` e `DATABASE_CONNECTION_DB_PREFIX_NAME` como mostrado em `env.evolution.example`. Consulte a documentação oficial para ajustar as flags `DATABASE_SAVE_*`.

