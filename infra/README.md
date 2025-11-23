# Azure IaC para o WhatsApp Chatbot

Este diretório centraliza toda a infraestrutura do módulo WhatsApp Chatbot do projeto **Tá Certo Isso?** usando **Bicep**. O template principal (`main.bicep`) está em escopo de **assinatura** e já cria o Resource Group antes de provisionar os recursos do workload (ACR, App Service Plan, Web App e Application Insights).

## Estrutura

- `main.bicep`: cria/atualiza o Resource Group e invoca os módulos do workload.
- `modules/whatsappchatbot-app.bicep`: recursos do chatbot (ACR, App Service Plan Linux, Web App para container, Application Insights e role assignment `AcrPull`).
- `modules/evolution-api.bicep`: App Service Linux dedicado à Evolution API (container `atendai/evolution-api`), usado quando `deployEvolutionService=true`.
- `modules/mongo-container.bicep`: provisiona um Azure Container Instance + Azure Files para rodar o MongoDB gerenciado pelo time.

## Parâmetros Relevantes

| Parâmetro | Descrição |
| --- | --- |
| `location` | Região Azure (ex: `brazilsouth`). |
| `resourceGroupName` | Nome do resource group que será criado/atualizado. |
| `acrName` | Nome único do Container Registry (`[a-z0-9]`, 5-50 chars). |
| `webAppName` | Nome do App Service (DNS global). |
| `containerImageName` | Nome da imagem Docker sem o registry (default `whatsappchatbot-app`). |
| `containerImageTag` | Tag inicial configurada no Web App (default `latest`). |
| `appServicePlanSkuName` | SKU do App Service (`B1`, `S1` ou `P1v3`). |
| `deployEvolutionService` | Se true, provisiona um App Service adicional rodando Evolution API. |
| `evolutionWebAppName` | Nome do App Service da Evolution API. |
| `evolutionPlanSkuName` | SKU do plano da Evolution API (`B1`, `S1`, `P1v3`). |
| `evolutionAppSettings` | App settings do container Evolution (ex.: `AUTHENTICATION_API_KEY`). |
| `mongoDbName` | Nome do database Mongo usado por ambos os serviços (default `whatsappchatbot`). |
| `mongoCollectionName` | Nome da collection usada para armazenar interações (default `interactions`). |
| `mongoContainerGroupName` | Nome do Azure Container Instance que executa o MongoDB. |
| `mongoDnsLabel` | Label DNS pública (`<label>.<região>.azurecontainer.io`) usada para expor a porta 27017. |
| `mongoStorageAccountName` | Storage account (Azure Files) onde o `/data/db` é persistido. |
| `mongoFileShareName` | Share criado dentro do storage para montar no container. |
| `mongoAdminUsername` / `mongoAdminPassword` | Credenciais raiz do MongoDB (o password deve ser informado via parâmetro/secret). |
| `mongoImage` | Imagem Docker utilizada (recomendado `hackathonopenaiacr.azurecr.io/mongo:7.0`). |
| `mongoRegistryLoginServer` | Hostname do registro privado usado para a imagem (ex.: `hackathonopenaiacr.azurecr.io`). |
| `mongoRegistryUsername` / `mongoRegistryPassword` | Credenciais do registry (obrigatório quando usar imagem privada). |
| `mongoPort` | Porta exposta pelo container (default `27017`). |
| `mongoCpuCores` / `mongoMemoryInGb` | Recursos reservados para o container. |
| `mongoFileShareQuota` | Tamanho (GB) do Azure Files que armazena os dados. |

## Deploy manual

```bash
az login
az deployment sub create \
  --name hackathonopenai-manual \
  --location eastus2 \
  --template-file infra/main.bicep \
  --parameters @infra/parameters/hackathonopenai.json \
               mongoRegistryUsername=$env:AZ_MONGO_REGISTRY_USERNAME \
               mongoRegistryPassword=$env:AZ_MONGO_REGISTRY_PASSWORD \
               mongoAdminPassword=$env:AZ_MONGO_ADMIN_PASSWORD
```

> ⚠️ Ajuste os valores do arquivo `infra/parameters/hackathonopenai.json` (principalmente `location`, `resourceGroupName`, `acrName`, `webAppName`, `evolutionWebAppName` e os app settings) antes de rodar o comando, respeitando as regiões liberadas para a sua assinatura. Para segredos (`mongoAdminPassword`, `mongoRegistryPassword`) prefira passar via variável de ambiente, como mostrado acima.

## Evolution API gerenciada

Quando `deployEvolutionService=true`, o template publica automaticamente um segundo App Service Linux (`evolutionWebAppName`) usando a imagem `atendai/evolution-api:latest`. Porém, versões recentes da Evolution ainda exigem um banco PostgreSQL/MySQL e Redis para executar as migrações Prisma — mesmo quando o Mongo é configurado. Caso não tenha esses recursos na assinatura, mantenha `deployEvolutionService=false` e execute a Evolution API em uma infraestrutura separada usando o `Nichols/evolution/docker-compose.yml`, que inclui Postgres + Redis conforme o guia oficial v2 ([instalação](https://doc.evolution-api.com/v2/pt/install/docker), [variáveis](https://doc.evolution-api.com/v2/pt/env)). Depois de subir o stack externo, use o mesmo `AUTHENTICATION_API_KEY` e `WEBHOOK_GLOBAL_URL` para integrar com o App Service do WhatsApp Chatbot.

## MongoDB executando em container

Em vez do Cosmos DB, o template agora provisiona automaticamente:

1. Um **Azure Container Instance** rodando a imagem `mongo` (configurável), com autenticação obrigatória (`MONGO_INITDB_ROOT_USERNAME/PASSWORD`).
2. Um **Azure Files share** montado em `/data/db` para garantir persistência entre reinicializações.
3. Um endpoint público (`https://<mongoDnsLabel>.<location>.azurecontainer.io:27017`) já liberado para o App Service do bot e para qualquer outro consumidor autorizado.

O connection string dessa instância é aplicado automaticamente:

- Ao App Service do WhatsApp Chatbot (`MONGO_CONNECTION_URI`, `MONGO_DB_NAME`, `MONGO_COLLECTION_NAME`), permitindo que o módulo **Leli** leia os dados depois.
- (Opcional) Ao App Service da Evolution API, caso `deployEvolutionService=true`, seguindo as recomendações de Mongo opcional descritas na [documentação oficial](https://doc.evolution-api.com/v1/pt/optional-resources/mongo-db).

> 💡 Proteja esse endpoint usando restrições de IP no App Service / firewall corporativo ou exponha o container dentro de uma VNet, conforme a maturidade do ambiente.

### Publicando a imagem do Mongo no ACR

O Azure Container Instance pode encontrar limites ao puxar diretamente do Docker Hub (`RegistryErrorResponse`). A recomendação é enviar a imagem `mongo:7.0` para o ACR criado pelo próprio template:

```powershell
az acr login --name hackathonopenaiacr
docker pull mongo:7.0
docker tag mongo:7.0 hackathonopenaiacr.azurecr.io/mongo:7.0
docker push hackathonopenaiacr.azurecr.io/mongo:7.0

$acrCreds = az acr credential show --name hackathonopenaiacr | ConvertFrom-Json
$env:AZ_MONGO_REGISTRY_USERNAME = $acrCreds.username
$env:AZ_MONGO_REGISTRY_PASSWORD = $acrCreds.passwords[0].value
$env:AZ_MONGO_ADMIN_PASSWORD = Read-Host -Prompt "Senha raiz do Mongo"
```

Depois disso, execute o `az deployment ...` passando os parâmetros conforme o bloco anterior. همیشه que renovar a senha do ACR, gere novos valores para `mongoRegistryUsername`/`mongoRegistryPassword`.

## Integração com o GitHub Actions

O workflow `.github/workflows/ci-azure.yml` executa o mesmo comando acima antes de buildar/pushar a imagem. Para que funcione:

1. Configure os secrets `AZURE_CREDENTIALS` (Service Principal com `Contributor`) **e** `AZURE_MONGO_ADMIN_PASSWORD` (a senha raiz que será aplicada no Mongo).
2. Ajuste as variáveis de ambiente no workflow (`AZURE_RESOURCE_GROUP`, `AZURE_LOCATION`, `AZURE_ACR_NAME`, `AZURE_WEBAPP_NAME`) para os mesmos nomes usados nos parâmetros do Bicep.
3. O pipeline fará:
   - `az deployment sub create` → cria/atualiza RG + recursos.
   - `az acr login` → autentica no ACR criado.
   - Build + push da imagem (`<acr>.azurecr.io/whatsappchatbot-app`).
   - Deploy do container no App Service apontando para a tag `latest`.

Com isso, todo o stack (infra + app) passa a ser criado automaticamente em novos ambientes. 

