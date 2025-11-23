targetScope = 'subscription'

@description('Azure region used for the resource group and child resources.')
param location string = 'eastus2'

@description('Name of the resource group that will be created (or updated).')
param resourceGroupName string

@description('Optional tags applied to every resource.')
param tags object = {
  environment: 'hackathon'
  workload: 'whatsappchatbot'
  project: 'HackathonOpenAI'
}

@minLength(5)
@maxLength(50)
@description('Globally unique name for the Azure Container Registry (lowercase letters and numbers only).')
param acrName string

@minLength(2)
@maxLength(60)
@description('Name of the Linux Web App (container).')
param webAppName string

@description('Docker image name without the registry hostname (example: whatsappchatbot-app).')
param containerImageName string = 'whatsappchatbot-app'

@description('Initial docker tag configured on the Web App. The CI pipeline updates the image afterwards.')
param containerImageTag string = 'latest'

@description('App Service plan SKU for the Linux container workload.')
@allowed([
  'B1'
  'S1'
  'P1v3'
])
param appServicePlanSkuName string = 'P1v3'

@description('Optional App Service settings (array of { name, value }).')
param appSettings array = []

@description('Deploy a managed Evolution API App Service (container).')
param deployEvolutionService bool = false

@description('Name of the Evolution API Web App (only used when deployEvolutionService=true).')
param evolutionWebAppName string = ''

@description('App Service plan SKU for the Evolution API (B1/S1/P1v3).')
@allowed([
  'B1'
  'S1'
  'P1v3'
])
param evolutionPlanSkuName string = 'B1'

@description('Docker image used by the Evolution API App Service.')
param evolutionImageName string = 'atendai/evolution-api:latest'

@description('App settings for the Evolution API (array of { name, value }).')
param evolutionAppSettings array = []

@description('Mongo database name used by both apps.')
param mongoDbName string = 'whatsappchatbot'

@description('Mongo collection name used for storing interactions.')
param mongoCollectionName string = 'interactions'

@description('Name of the container group that will host MongoDB.')
param mongoContainerGroupName string = 'hackathonopenai-mongo'

@minLength(3)
@maxLength(60)
@description('DNS label (lowercase, unique per region) for the Mongo endpoint.')
param mongoDnsLabel string

@minLength(3)
@maxLength(24)
@description('Storage account (lowercase letters and numbers) used for Mongo data.')
param mongoStorageAccountName string

@description('Azure Files share mounted at /data/db.')
param mongoFileShareName string = 'mongodata'

@description('Admin username for Mongo.')
param mongoAdminUsername string = 'mongoadmin'

@secure()
@description('Admin password for Mongo (provide at deploy time).')
param mongoAdminPassword string

@description('Docker image for Mongo.')
param mongoImage string = 'mongo:7.0'

@description('Registry login server for the Mongo image (leave empty to pull anonymously).')
param mongoRegistryLoginServer string = ''

@description('Registry username when pulling from a private registry.')
param mongoRegistryUsername string = ''

@secure()
@description('Registry password when pulling from a private registry.')
param mongoRegistryPassword string = ''

@description('Port exposed by the Mongo container.')
param mongoPort int = 27017

@description('Requested CPU for the Mongo container.')
param mongoCpuCores int = 1

@description('Requested memory (GB) for the Mongo container.')
param mongoMemoryInGb int = 2

@description('Quota (GB) for the Azure Files share that stores Mongo data.')
param mongoFileShareQuota int = 10

resource rg 'Microsoft.Resources/resourceGroups@2021-04-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module mongo 'modules/mongo-container.bicep' = {
  name: 'mongoContainerStack'
  scope: rg
  params: {
    location: location
    tags: tags
    containerGroupName: mongoContainerGroupName
    dnsNameLabel: mongoDnsLabel
    mongoImage: mongoImage
    mongoPort: mongoPort
    adminUsername: mongoAdminUsername
    adminPassword: mongoAdminPassword
    cpuCores: mongoCpuCores
    memoryInGb: mongoMemoryInGb
    storageAccountName: mongoStorageAccountName
    fileShareName: mongoFileShareName
    fileShareQuota: mongoFileShareQuota
    registryLoginServer: mongoRegistryLoginServer
    registryUsername: mongoRegistryUsername
    registryPassword: mongoRegistryPassword
  }
}

var mongoConnectionString = mongo.outputs.connectionString

var whatsappMongoSettings = [
  {
    name: 'MONGO_CONNECTION_URI'
    value: mongoConnectionString
  }
  {
    name: 'MONGO_DB_NAME'
    value: mongoDbName
  }
  {
    name: 'MONGO_COLLECTION_NAME'
    value: mongoCollectionName
  }
]

var evolutionMongoSettings = [
  {
    name: 'DATABASE_ENABLED'
    value: 'true'
  }
  {
    name: 'DATABASE_PROVIDER'
    value: 'mongodb'
  }
  {
    name: 'DATABASE_CONNECTION_URI'
    value: mongoConnectionString
  }
  {
    name: 'DATABASE_CONNECTION_DB_PREFIX_NAME'
    value: mongoDbName
  }
]

module whatsappchatbot 'modules/whatsappchatbot-app.bicep' = {
  name: 'whatsappchatbotStack'
  scope: rg
  params: {
    location: location
    tags: tags
    acrName: acrName
    webAppName: webAppName
    containerImageName: containerImageName
    containerImageTag: containerImageTag
    appServicePlanSkuName: appServicePlanSkuName
    customAppSettings: concat(appSettings, whatsappMongoSettings)
  }
}

module evolution 'modules/evolution-api.bicep' = if (deployEvolutionService) {
  name: 'evolutionStack'
  scope: rg
  params: {
    location: location
    tags: tags
    webAppName: evolutionWebAppName
    containerImageName: evolutionImageName
    appServicePlanSkuName: evolutionPlanSkuName
    appSettings: concat(evolutionMongoSettings, evolutionAppSettings)
  }
}

output resourceGroup string = rg.name
output acrLoginServer string = whatsappchatbot.outputs.acrLoginServer
output webAppName string = whatsappchatbot.outputs.webAppName
output planId string = whatsappchatbot.outputs.planId
output appInsightsName string = whatsappchatbot.outputs.appInsightsName
output evolutionWebApp string = deployEvolutionService ? evolution.outputs.webAppName : ''
output mongoFqdn string = mongo.outputs.fqdn
output mongoPort int = mongo.outputs.port
@secure()
output mongoConnectionUri string = mongoConnectionString

