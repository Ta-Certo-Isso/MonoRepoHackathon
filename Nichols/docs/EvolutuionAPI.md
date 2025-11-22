Introdução
Evolution API é um projeto dedicado a capacitar pequenas empresas, empreendedores, freelancers e indivíduos com recursos limitados.
Nossa missão é fornecer uma solução de mensagens de WhatsApp™ via API, permitindo que esses grupos reforcem seus negócios locais ou online.
O melhor de tudo é que o nosso serviço é totalmente gratuito, concebido para apoiar aqueles que se esforçam para ter sucesso num cenário de mercado competitivo.
Acesse nosso repositório e faça parte da nossa comunidade para fazer parte do projeto.
​
Início Rápido
Você precisará ter o Docker instalado em sua máquina, veja a Documentação Oficial do Docker
Para executar a versão de teste e testar as principais funcionalidades da API, copie o comando abaixo, modifique o valor de AUTHENTICATION_API_KEY para um de sua preferência, e execute o comando:

Copy
docker run -d \
    --name evolution_api \
    -p 8080:8080 \
    -e AUTHENTICATION_API_KEY=mude-me \
    atendai/evolution-api:latest
A execução via CLI é recomendada para implantações rápidas, principalmente para testes ou desenvolvimento. Não deve ser usada em produção. Em vez disso, recomendamos que você use o docker-compose para facilitar a implantação e manutenção.
Isso executará um contêiner Docker expondo a aplicação na porta 8080 e você poderá começar a testar e solicitar o código QR do WhatsApp usando o conteúdo da variável de autenticação com o cabeçalho apikey definido.
Para garantir que a API está em execução, acesse http://localhost:8080 em seu navegador. Esta deve ser a resposta do seu navegador:

Copy
{
   "status":200,
   "message":"Welcome to the Evolution API, it is working!",
   "version":"1.x.x",
   "swagger":"http://localhost:8080/docs",
   "manager":"http://localhost:8080/manager",
   "documentation":"https://doc.evolution-api.com"
}

Docker
Estas instruções de instalação assumem que você já instalou o Docker em sua máquina. Você pode encontrar informações sobre como instalar o Docker na Documentação Oficial do Docker.
O EvolutionAPI está pronto para o Docker e pode ser facilmente implantado com o Docker no modo standalone e swarm. O repositório oficial do EvolutionAPI possui todos os arquivos de composição necessários para instalar a API.
​
Docker Run
​
Início Rápido
A instalação CLI é recomendada para implantação rápida, principalmente para testes ou desenvolvimento. Não deve ser usada para produção. Em vez disso, recomendamos que você use o docker-compose para facilitar a implantação e a manutenção.
A maneira mais rápida de fazer deploy da EvolutionAPI com o Docker é usando docker run na interface de linha de comando.
Terminal

Copy
docker run -d \
    --name evolution-api \
    -p 8080:8080 \
    -e AUTHENTICATION_API_KEY=mude-me \
    atendai/evolution-api
Isso executará um contêiner do Docker expondo a aplicação na porta 8080 e você poderá começar a testar e solicitar o código QR do WhatsApp usando o conteúdo da variável de autenticação com o cabeçalho apikey definido.
​
Início Rápido com Volumes
Você também pode fazer deploy usando volumes docker para manter os dados persistentes da sua EvolutionAPI e todas as instâncias do WhatsApp em sua máquina local, evitando problemas com a reinicialização do contêiner usando o docker run na interface de linha de comando.
Execute o comando a seguir para implementar o EvolutionAPI com os volumes necessários. Este comando mapeia os volumes evolution_store e evolution_instances para os respectivos diretórios dentro do contêiner.
Terminal

Copy
docker run -d \
    --name evolution-api \
    -p 8080:8080 \
    -e AUTHENTICATION_API_KEY=mude-me \
    -v evolution_store:/evolution/store \
    -v evolution_instances:/evolution/instances \
    atendai/evolution-api
​
Docker Compose
Fazer deploy da EvolutionAPI usando o Docker Compose simplifica a configuração e o gerenciamento de seus contêineres Docker. Ele permite que você defina seu ambiente Docker em um arquivo docker-compose.yaml e, em seguida, use um único comando para iniciar tudo.
Este é um exemplo do Docker Compose para ambientes standalone, ou seja, um único servidor em execução. Para a sincronização de dois servidores em paralelo, use o Swarm. Isso é para usuários Docker mais avançados.
​
Standalone
Atenção: os comandos aqui descritos como docker compose, podem não funcionar em versões mais antigas, e devem ser substituídos por docker-compose.
O Docker standalone é adequado quando sua API de evolução será executada apenas em uma máquina e você não precisará de escalabilidade ou outros recursos do Docker Swarm por enquanto. É a maneira mais conveniente de usar o Docker para a maioria das pessoas.
Crie um arquivo docker-compose.yml com este conteúdo:
docker-compose.yml

Copy
version: '3'
services:
  evolution-api:
    container_name: evolution_api
    image: atendai/evolution-api
    restart: always
    ports:
      - "8080:8080"
    env_file:
      - .env
    volumes:
      - evolution_store:/evolution/store
      - evolution_instances:/evolution/instances

volumes:
  evolution_store:
  evolution_instances:
Crie um arquivo .env no mesmo diretório com o seguinte:
.env

Copy
AUTHENTICATION_API_KEY=mude-me
Para mais configurações, pegue o arquivo de exemplo no repositório oficial. E veja o guia aqui
Navegue até o diretório que contém seu arquivo docker-compose.yml e execute: serviços definidos no arquivo

Copy
docker compose up -d
Este comando baixará as imagens Docker necessárias, criará os serviços, redes e volumes definidos e iniciará o serviço da EvolutionAPI.
Após executar o comando docker-compose up, você deve ver os logs indicando que os serviços estão em execução.

Copy
docker logs evolution_api
Para parar o serviço, utilize:

Copy
docker compose down
Abra seu navegador e acesse http://localhost:8080 para verificar se o EvolutionAPI está operacional.

Recursos Opcionais
Websocket
Evolution API utiliza o socket.io para emitir eventos, aproveitando a tecnologia WebSocket. Isso torna o desenvolvimento de integrações mais eficiente e direto para os desenvolvedores. WebSocket fornece um canal de comunicação full-duplex sobre uma única conexão duradoura, permitindo o fluxo de dados em tempo real entre o cliente e o servidor.
Para ativar os websockets, defina a variável de ambiente WEBSOCKET_ENABLED como true. Veja mais em Variáveis de Ambiente
​
Conexão ao WebSocket
Para se conectar ao servidor WebSocket na Evolution API, você pode usar o seguinte formato de URL:

Copy
wss://api.seusite.com/nome_instancia
Substitua api.seusite.com pelo domínio real da sua API e nome_instancia pelo nome da sua instância específica.
Exemplo de Estabelecimento de Conexão WebSocket Aqui está um exemplo básico de como estabelecer uma conexão WebSocket usando JavaScript:

Copy
const socket = io('wss://api.seusite.com/nome_instancia', {
  transports: ['websocket']
});

socket.on('connect', () => {
  console.log('Conectado ao WebSocket da Evolution API');
});

// Escutando eventos
socket.on('nome_evento', (data) => {
  console.log('Evento recebido:', data);
});

// Lidando com desconexão
socket.on('disconnect', () => {
  console.log('Desconectado do WebSocket da Evolution API');
});
Neste exemplo, substitua nome_evento pelo evento específico que você deseja escutar.
​
Manipulando Eventos
Uma vez conectado, você pode escutar vários eventos emitidos pelo servidor. Cada evento pode carregar dados relevantes para o contexto do evento. Por exemplo, se estiver ouvindo atualizações de mensagens, você pode receber dados contendo o conteúdo da mensagem atualizada e metadados.
​
Enviando Mensagens
Você também pode enviar mensagens para o servidor usando o método emit:

Copy
socket.emit('send_message', { message: 'Olá, Mundo!' });
// Neste caso, send_message é o nome do evento, e o objeto { message: 'Olá, Mundo!' } é os dados sendo enviados.
​
Fechando a Conexão
Para fechar a conexão WebSocket, use o método disconnect:

Copy
socket.disconnect();
Lembre-se de manipular a conexão de forma responsável, desconectando quando sua aplicação ou componente for desmontado para evitar vazamentos de memória e garantir o uso eficiente de recursos.
Ao aproveitar os WebSockets, a Evolution API oferece uma maneira poderosa de interagir com o sistema em tempo real, proporcionando uma experiência contínua tanto para desenvolvedores quanto para usuários finais.

Recursos Opcionais
Redis
​
Configuração
O Redis é um armazenamento de estrutura de dados em memória, usado como banco de dados, cache e corretor de mensagens. Ele suporta estruturas de dados como strings, hashes, listas, conjuntos e muito mais. Incorporar o Redis pode melhorar significativamente o desempenho da Evolution API, permitindo acesso mais rápido aos dados e cache eficiente.
Defina as variáveis de ambiente do Redis no arquivo .env para Docker ou no arquivo dev-env.yml para NPM da seguinte forma:

Copy
# Defina como true para habilitar o Redis.
CACHE_REDIS_ENABLED=false
# URI do seu servidor Redis.
CACHE_REDIS_URI=redis://redis:6379
# Chave de prefixo para dados do Redis.
CACHE_REDIS_PREFIX_KEY=evolution
# Tempo que os dados são mantidos em cache
CACHE_REDIS_TTL=604800
# Salva as credencias de conexão do whatsapp no redis
CACHE_REDIS_SAVE_INSTANCES=true
Veja mais em Variáveis de ambiente.

Variáveis de Ambiente
Veja o arquivo de exemplo do env no repositório oficial.
​
Principais variáveis
Variável	Valor	Exemplo
SERVER_URL	O endereço para seu servidor em execução. Esse endereço é utilizado para retornar dados de requisição interna, como links de webhook.	https://exemplo.evolution-api.com
WEBSOCKET_ENABLED	Habilitar ou não o WebSocket	true
WEBSOCKET_GLOBAL_EVENTS	Habilita os WebSocket de forma global	true
CONFIG_SESSION_PHONE_CLIENT	Nome que será exibido na conexão do smartphone	EvolutionAPI
CONFIG_SESSION_PHONE_NAME	Nome do navegador que será exibido na conexão do smartphone	Chrome
​
Logs
Variável	Valor	Exemplo
LOG_LEVEL	Logs que serão mostrados entre: ERROR,WARN,DEBUG,INFO,LOG,VERBOSE,DARK,WEBHOOKS	ERROR,WARN,DEBUG,INFO,LOG,VERBOSE,DARK,WEBHOOKS
LOG_COLOR	Mostrar ou não cores nos Logs (true ou false)	true
LOG_BAILEYS	Quais logs da Baileys serão mostrados entre: “fatal”, “error”, “warn”, “info”, “debug” e “trace”	error
​
Storage Temporáreo
Armazenamento temporáreo de dados. Valores são true ou false para armazena ou não.
Variável	Valor
STORE_MESSAGES	Guarda mensagens
STORE_MESSAGE_UP	Guarda atualização das mensagens
STORE_CONTACTS	Guarda contatos
STORE_CHATS	Guarda conversas
​
Limpeza do Storage Temporáreo
Limpeza do armazenamento temporáreo.
Variável	Valor
CLEAN_STORE_CLEANING_INTERVAL	Intervalo de limpeza em segundos
CLEAN_STORE_MESSAGES	Se excluirá as mensagens (true ou false)
CLEAN_STORE_MESSAGE_UP	Se excluirá as atualizações de mensagens (true ou false)
CLEAN_STORE_CONTACTS	Se excluirá os contatos (true ou false)
CLEAN_STORE_CHATS	Se excluirá as conversas (true ou false)
​
Storage Persistente
Configurações de conexão:
Variável	Valor	Exemplo
DATABASE_ENABLED	Se o armazenamento persistente está habilitado	true
DATABASE_CONNECTION_URI	A URI de conexão do MongoDB	true
DATABASE_CONNECTION_DB_PREFIX_NAME	Quais logs da Baileys serão mostrados entre: “fatal”, “error”, “warn”, “info”, “debug” e “trace”	error
Quais dados serão salvos (true ou false)
Variável	Valor
DATABASE_SAVE_DATA_INSTANCE	Salva dados de instâncias
DATABASE_SAVE_DATA_NEW_MESSAGE	Salva novas mensagens
DATABASE_SAVE_MESSAGE_UPDATE	Salva atualizações de mensagens
DATABASE_SAVE_DATA_CONTACTS	Salva contatos
DATABASE_SAVE_DATA_CHATS	Salva conversas
​
Redis
Variável	Valor	Exemplo
CACHE_REDIS_ENABLED	Se o Redis está habilitado (true ou false)	true
CACHE_REDIS_URI	A URI de conexão do Redis	redis://redis:6379
CACHE_REDIS_PREFIX_KEY	Prefixo do nome de chave	evolution
CACHE_REDIS_TTL	Tempo para manter os dados no Redis	604800
CACHE_REDIS_SAVE_INSTANCES	Salva as credencias de conexão do whatsapp no Redis	false
CACHE_LOCAL_ENABLED	Faz cache em memória, alternativa ao Redis	false
CACHE_LOCAL_TTL	Tempo para manter os dados localmente	604800
​
RabbitMQ
Variável	Valor	Exemplo
RABBITMQ_ENABLED	Habilita o RabbitMQ (true ou false)	true
RABBITMQ_GLOBAL_ENABLED	Habilita o RabbitMQ de forma global (true ou false)	false
RABBITMQ_URI	URI de conexão do RabbitMQ	amqp://guest:guest@rabbitmq:5672
RABBITMQ_EXCHANGE_NAME	Nome do exchange	evolution_exchange
RABBITMQ_EVENTS_APPLICATION_STARTUP	Envia um evento na inicialização do app	false
RABBITMQ_EVENTS_QRCODE_UPDATED	Envia eventos de Atualização do QR Code	true
RABBITMQ_EVENTS_MESSAGES_SET	Envia eventos de Criação de Mensagens (recuperação de mensagens)	true
RABBITMQ_EVENTS_MESSAGES_UPSERT	Envia eventos de Recebimento de Mensagens	true
RABBITMQ_EVENTS_MESSAGES_UPDATE	Envia eventos de Atualização de Mensagens	true
RABBITMQ_EVENTS_MESSAGES_DELETE	Envia eventos de Deleção de Mensagens	true
RABBITMQ_EVENTS_SEND_MESSAGE	Envia eventos de Envio de Mensagens	true
RABBITMQ_EVENTS_CONTACTS_SET	Envia eventos de Criação de Contatos	true
RABBITMQ_EVENTS_CONTACTS_UPSERT	Envia eventos de Criação de Contatos (recuperação de contatos)	true
RABBITMQ_EVENTS_CONTACTS_UPDATE	Envia eventos de Atualização de Contatos	true
RABBITMQ_EVENTS_PRESENCE_UPDATE	Envia eventos de Atualização de presença (“digitando…” ou “gravando…“)	true
RABBITMQ_EVENTS_CHATS_SET	Envia eventos de Criação de Conversas (recuperação de conversas)	true
RABBITMQ_EVENTS_CHATS_UPSERT	Envia eventos de Criação de Conversas (recebimento ou envio de mensagens em novos chats)	true
RABBITMQ_EVENTS_CHATS_UPDATE	Envia eventos de Atualização de Conversas	true
RABBITMQ_EVENTS_CHATS_DELETE	Envia eventos de Deleção de Conversas	true
RABBITMQ_EVENTS_GROUPS_UPSERT	Envia eventos de Criação de Grupos	true
RABBITMQ_EVENTS_GROUPS_UPDATE	Envia eventos de Atualização de Grupos	true
RABBITMQ_EVENTS_GROUP_PARTICIPANTS_UPDATE	Envia eventos de Atualização nos Participantes de Grupos	true
RABBITMQ_EVENTS_CONNECTION_UPDATE	Envia eventos de Atualização de Conexão	true
RABBITMQ_EVENTS_LABELS_EDIT	Envia eventos de Edição de Etiquetas	true
RABBITMQ_EVENTS_LABELS_ASSOCIATION	Envia eventos de Associação de Etiquetas	true
RABBITMQ_EVENTS_CALL	Envia eventos de Chamadas	true
RABBITMQ_EVENTS_TYPEBOT_START	Envia eventos de Início de fluxo do Typebot	false
RABBITMQ_EVENTS_TYPEBOT_CHANGE_STATUS	Envia eventos de Atualização no status do Typebot	false
​
SQS
Variável	Valor
SQS_ENABLED	Se o SQS está habilitado (true ou false)
SQS_ACCESS_KEY_ID	O ID de chave do SQS
SQS_SECRET_ACCESS_KEY	Chave de acesso
SQS_ACCOUNT_ID	ID da conta
SQS_REGION	Região do SQS
​
Instâncias
Variável	Valor	Exemplo
DEL_INSTANCE	Em quantos minutos uma instânica será excluída se não conectada. Use “false” para nunca excluir.	5
DEL_TEMP_INSTANCES	Deleta instâncias fechadas na inicialização	true
​
CORS
Variável	Valor	Exemplo
CORS_ORIGIN	As origens permitidas pela API separadas por vírgula (utilize ”*” para aceiteitar requisições de qualquer origem).	https://meu-frontend.com,https://meu-outro-frontend.com
CORS_METHODS	Métodos HTTP permitidos separados por vírgula.	POST,GET,PUT,DELETE
CORS_CREDENTIALS	Permisão de cookies em requisições (true ou false).	true
​
Webhook
Variável	Valor
WEBHOOK_GLOBAL_URL	Url que receberá as requisições de webhook
WEBHOOK_GLOBAL_ENABLED	Se os webhooks estão habilitados (true ou false)
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS	
Eventos de webhook com valor true ou false:
Variável
WEBHOOK_EVENTS_APPLICATION_STARTUP
WEBHOOK_EVENTS_QRCODE_UPDATED
WEBHOOK_EVENTS_MESSAGES_SET
WEBHOOK_EVENTS_MESSAGES_UPSERT
WEBHOOK_EVENTS_MESSAGES_UPDATE
WEBHOOK_EVENTS_MESSAGES_DELETE
WEBHOOK_EVENTS_SEND_MESSAGE
WEBHOOK_EVENTS_CONTACTS_SET
WEBHOOK_EVENTS_CONTACTS_UPSERT
WEBHOOK_EVENTS_CONTACTS_UPDATE
WEBHOOK_EVENTS_PRESENCE_UPDATE
WEBHOOK_EVENTS_CHATS_SET
WEBHOOK_EVENTS_CHATS_UPSERT
WEBHOOK_EVENTS_CHATS_UPDATE
WEBHOOK_EVENTS_CHATS_DELETE
WEBHOOK_EVENTS_GROUPS_UPSERT
WEBHOOK_EVENTS_GROUPS_UPDATE
WEBHOOK_EVENTS_GROUP_PARTICIPANTS_UPDATE
WEBHOOK_EVENTS_CONNECTION_UPDATE
WEBHOOK_EVENTS_LABELS_EDIT
WEBHOOK_EVENTS_LABELS_ASSOCIATION
WEBHOOK_EVENTS_CALL
WEBHOOK_EVENTS_NEW_JWT_TOKEN
WEBHOOK_EVENTS_TYPEBOT_START
WEBHOOK_EVENTS_TYPEBOT_CHANGE_STATUS
WEBHOOK_EVENTS_CHAMA_AI_ACTION
WEBHOOK_EVENTS_ERRORS
WEBHOOK_EVENTS_ERRORS_WEBHOOK
​
QR Code
Variável	Valor
QRCODE_LIMIT	Por quanto tempo o QR code durará
QRCODE_COLOR	Cor do QR code gerado
​
Typebot
Variável	Valor
TYPEBOT_API_VERSION	Versão da API (versão fixa ou latest)
TYPEBOT_KEEP_OPEN	Mantém o Typebot aberto (true ou false)
​
Autenticação
Variável	Valor
AUTHENTICATION_TYPE	Tipo de autenticação (jwt ou apikey)
AUTHENTICATION_API_KEY	Chave da API que será usada para autenticação
AUTHENTICATION_EXPOSE_IN_FETCH_INSTANCES	
AUTHENTICATION_JWT_EXPIRIN_IN	Tempo de expiração do token JWT
AUTHENTICATION_JWT_SECRET	Segredo usado para gerar o JWT

Recursos Disponíveis
​
Recursos de Mensagens e Grupos
​
Mensagens (Individuais ou em Grupo)
Recurso	Disponibilidade	Descrição
Envio de Texto	✅	(Texto simples, em negrito, itálico, riscado, em formato de código e emojis)
Envio de Mídia	✅	(Vídeo, imagem e documento)
Envio de Áudio Narrado	✅	(Funcionando bem no Android e iOS)
Envio de Localização	✅	(Com nome e descrição do local)
Envio de Contato	✅	(Com Nome, Empresa, Telefone, E-mail e URL)
Envio de Reação	✅	(Envie qualquer emoji para reação)
Envio de Pré-visualização de Link	✅	(Busca por informações de SEO) 🆕
Envio de Resposta	✅	(Marcar mensagens em resposta) 🆕
Envio de Menção	✅	(Individual, para alguns ou todos os membros) 🆕
Envio de Enquete	✅	(Enviar e receber votos de uma enquete) 🆕
Envio de Status/História	✅	(Texto, pré-visualização de link, vídeo, imagem e forma de onda) 🆕
Envio de Adesivo	✅	(Imagem estática) 🆕
Envio de Lista (Homologação)	✅	(Testando)
Envio de Botões (Descontinuado)	❌	(Só funciona na API em nuvem)
​
Perfil
Recurso	Disponibilidade	Descrição
Atualizar Nome	✅	(Alterar o nome do perfil conectado)
Atualizar Foto	✅	(Alterar a foto do perfil conectado) 🆕
Atualizar Status	✅	(Alterar o status do perfil conectado) 🆕
E muitos outros…		
​
Grupo
Recurso	Disponibilidade	Descrição
Criar Grupo	✅	(Novos grupos)
Atualizar Foto	✅	(Alterar foto do grupo)
Atualizar Assunto	✅	(Alterar o nome do grupo) 🆕
Atualizar Descrição	✅	(Alterar a descrição do grupo) 🆕
Obter Todos os Grupos	✅	(Obter todos os grupos e participantes) 🆕
E muitos outros…		

Webhooks
Os Webhooks permitem integração em tempo real entre a Evolution API e o WhatsApp™, permitindo sincronização e compartilhamento automatizados de dados.
É exatamente esse recurso que possibilita a criação de bots de autoatendimento e sistemas multi-serviço.
​
Ativando Webhooks
Existem duas maneiras de ativar o webhook:
No arquivo .env com eventos globais
Chamando o endpoint /webhook/instance
​
Eventos de webhook da instância
A maioria dos usuários preferirá a ativação por instância, desta forma é mais fácil controlar os eventos recebidos, no entanto em alguns casos é necessário um webhook global, isso pode ser feito usando a variável de webhook global.
Aqui está um exemplo com alguns eventos comuns ouvidos:
/webhook/instance

Copy
{
  "url": "{{webhookUrl}}",
  "webhook_by_events": false,
  "webhook_base64": false,
  "events": [
      "QRCODE_UPDATED",
      "MESSAGES_UPSERT",
      "MESSAGES_UPDATE",
      "MESSAGES_DELETE",
      "SEND_MESSAGE",
      "CONNECTION_UPDATE",
      "TYPEBOT_START",
      "TYPEBOT_CHANGE_STATUS"
  ]    
}
​
Parâmetros
Parâmetro	Tipo	Obrigatório	Descrição
enabled	boolean	Sim	Insira “true” para criar ou alterar dados do Webhook, ou “false” se quiser parar de usá-lo.
url	string	Sim	URL do Webhook para receber dados do evento.
webhook_by_events	boolean	Não	Deseja gerar uma URL específica do Webhook para cada um dos seus eventos.
events	array	Não	Lista de eventos a serem processados. Se você não quiser usar alguns desses eventos, apenas remova-os da lista.
É extremamente necessário que o payload obedeça às regras para criar um arquivo JSON, considerando o arranjo correto de itens, formatação, colchetes, chaves e vírgulas, etc. Antes de consumir o endpoint, se tiver dúvidas sobre a formatação JSON, vá para https://jsonlint.com/ e valide.
​
Eventos Globais de Webhook
Cada URL e eventos de Webhook da instância serão solicitados no momento em que forem criados Defina um webhook global que ouvirá eventos habilitados de todas as instâncias
.env

Copy
WEBHOOK_GLOBAL_URL=''
WEBHOOK_GLOBAL_ENABLED=false

# Com esta opção ativada, você trabalha com uma URL por evento de webhook, respeitando a URL global e o nome de cada evento
WEBHOOK_GLOBAL_WEBHOOK_BY_EVENTS=false

## Defina os eventos que você deseja ouvir, todos os eventos listados abaixo são suportados
WEBHOOK_EVENTS_APPLICATION_STARTUP=false
WEBHOOK_EVENTS_QRCODE_UPDATED=true

# Alguns eventos extras para erros
WEBHOOK_EVENTS_ERRORS=false
WEBHOOK_EVENTS_ERRORS_WEBHOOK=
​
Eventos Suportados
Estes são os eventos de webhook disponíveis e suportados:
Variável de ambiente	URL	Descrição
APPLICATION_STARTUP	/application-startup	Notifica quando uma inicialização de aplicativo ocorre
QRCODE_UPDATED	/qrcode-updated	Envia o base64 do qrcode para leitura
CONNECTION_UPDATE	/connection-update	Informa o status da conexão com o WhatsApp
MESSAGES_SET	/messages-set	Envia uma lista de todas as suas mensagens carregadas no WhatsApp. Este evento ocorre apenas uma vez
MESSAGES_UPSERT	/messages-upsert	Notifica quando uma mensagem é recebida
MESSAGES_UPDATE	/messages-update	Informa quando uma mensagem é atualizada
MESSAGES_DELETE	/messages-delete	Informa quando uma mensagem é excluída
SEND_MESSAGE	/send-message	Notifica quando uma mensagem é enviada
CONTACTS_SET	/contacts-set	Realiza o carregamento inicial de todos os contatos. Este evento ocorre apenas uma vez
CONTACTS_UPSERT	/contacts-upsert	Recarrega todos os contatos com informações adicionais. Este evento ocorre apenas uma vez
CONTACTS_UPDATE	/contacts-update	Informa quando o contato é atualizado
PRESENCE_UPDATE	/presence-update	Informa se o usuário está online, se ele está realizando alguma ação como escrever ou gravar e seu último visto: ‘indisponível’, ‘disponível’, ‘compondo’, ‘gravando’, ‘pausado’
CHATS_SET	/chats-set	Envia uma lista de todos os chats carregados
CHATS_UPDATE	/chats-update	Informa quando o chat é atualizado
CHATS_UPSERT	/chats-upsert	Envia qualquer nova informação de chat
CHATS_DELETE	/chats-delete	Notifica quando um chat é excluído
GROUPS_UPSERT	/groups-upsert	Notifica quando um grupo é criado
GROUPS_UPDATE	/groups-update	Notifica quando um grupo tem suas informações atualizadas
GROUP_PARTICIPANTS_UPDATE	/group-participants-update	Notifica quando uma ação ocorre envolvendo um participante: ‘adicionar’, ‘remover’, ‘promover’, ‘rebaixar’
NEW_TOKEN	/new-jwt	Notifica quando o token (jwt) é atualizado
​
Webhook por eventos
Ao habilitar as opções WEBHOOK_BY_EVENTS nos webhooks globais e locais, os seguintes caminhos serão adicionados ao final do webhook.
Adicione ao final da URL o nome do evento com um traço (-) entre as palavras que compõem o evento.
​
Exemplo
Supondo que sua URL de webhook fosse https://sub.domain.com/webhook/. A Evolution adicionará automaticamente ao final da URL o nome do evento quando webhook_by_events estiver definido como verdadeiro.
Evento	Nova URL de Webhook por Eventos
APPLICATION_STARTUP	https://sub.domain.com/webhook/application-startup
QRCODE_UPDATED	https://sub.domain.com/webhook/qrcode-updated
CONNECTION_UPDATE	https://sub.domain.com/webhook/connection-update
MESSAGES_SET	https://sub.domain.com/webhook/messages-set
MESSAGES_UPSERT	https://sub.domain.com/webhook/messages-upsert
MESSAGES_UPDATE	https://sub.domain.com/webhook/messages-update
MESSAGES_DELETE	https://sub.domain.com/webhook/messages-delete
SEND_MESSAGE	https://sub.domain.com/webhook/send-message
CONTACTS_SET	https://sub.domain.com/webhook/contacts-set
CONTACTS_UPSERT	https://sub.domain.com/webhook/contacts-upsert
CONTACTS_UPDATE	https://sub.domain.com/webhook/contacts-update
PRESENCE_UPDATE	https://sub.domain.com/webhook/presence-update
CHATS_SET	https://sub.domain.com/webhook/chats-set
CHATS_UPDATE	https://sub.domain.com/webhook/chats-update
CHATS_UPSERT	https://sub.domain.com/webhook/chats-upsert
CHATS_DELETE	https://sub.domain.com/webhook/chats-delete
GROUPS_UPSERT	https://sub.domain.com/webhook/groups-upsert
GROUPS_UPDATE	https://sub.domain.com/webhook/groups-update
GROUP_PARTICIPANTS_UPDATE	https://sub.domain.com/webhook/group-participants-update
NEW_TOKEN	https://sub.domain.com/webhook/new-jwt
​
Localizando Webhook
Se necessário, há uma opção para localizar qualquer webhook ativo na instância específica.
Método	Endpoint
GET	[baseUrl]/webhook/find/[instance]
​
Dados retornados da solicitação:
Chamando o endpoint retornará todas as informações sobre o webhook que está sendo usado pela instância.
Resultado

Copy
{
  "enabled": true,
  "url": "[url]",
  "webhookByEvents": false,
  "events": [
    [eventos]
  ]
}
-----
## Atalho de setup para o MVP Nichols

Use este docker para testar o webhook Nichols localmente:

```
docker run -d --name evolution_api -p 8080:8080 ^
  -e AUTHENTICATION_API_KEY=troque-me ^
  -e SERVER_URL=http://localhost:8080 ^
  -e WEBHOOK_GLOBAL_URL=https://seu-render.onrender.com/webhook/evolution ^
  -e WEBHOOK_GLOBAL_ENABLED=true ^
  -e WEBHOOK_EVENTS_MESSAGES_UPSERT=true ^
  evoapicloud/evolution-api:latest
```

- Escaneie o QR em `http://localhost:8080/manager`.
- Use o mesmo `AUTHENTICATION_API_KEY` no header `apikey` ao chamar `sendText`/`sendWhatsAppAudio`.
- Se usar docker-compose, copie as mesmas vari�veis para o `.env`.
