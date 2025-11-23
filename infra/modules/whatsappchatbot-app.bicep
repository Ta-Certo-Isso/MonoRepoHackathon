targetScope = 'resourceGroup'

@description('Azure region for the WhatsApp Chatbot workload.')
param location string

@description('Tags propagated to child resources.')
param tags object = {}

@minLength(5)
@maxLength(50)
@description('Container registry name. Must match the value used by the CI pipeline.')
param acrName string

@minLength(2)
@maxLength(60)
@description('Name of the Web App that will run the WhatsApp Chatbot container.')
param webAppName string

@description('Docker image name without registry hostname.')
param containerImageName string

@description('Docker tag configured during the initial deployment.')
param containerImageTag string = 'latest'

@description('App Service plan SKU. Use P1v3 (or higher) for production workloads.')
@allowed([
  'B1'
  'S1'
  'P1v3'
])
param appServicePlanSkuName string = 'P1v3'

@description('Additional App Service appSettings entries (array of { name, value }).')
param customAppSettings array = []

var planNameBase = '${webAppName}-plan'
var planNameLength = min(length(planNameBase), 40)
var planName = substring(planNameBase, 0, planNameLength)

var appInsightsNameBase = '${webAppName}-ai'
var appInsightsNameLength = min(length(appInsightsNameBase), 60)
var appInsightsName = substring(appInsightsNameBase, 0, appInsightsNameLength)

var skuMap = {
  B1: {
    tier: 'Basic'
    size: 'B1'
    capacity: 1
  }
  S1: {
    tier: 'Standard'
    size: 'S1'
    capacity: 1
  }
  P1v3: {
    tier: 'PremiumV3'
    size: 'P1v3'
    capacity: 1
  }
}

var selectedSku = skuMap[appServicePlanSkuName]

resource acr 'Microsoft.ContainerRegistry/registries@2023-08-01-preview' = {
  name: acrName
  location: location
  tags: tags
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
    publicNetworkAccess: 'Enabled'
  }
}

resource appPlan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  sku: {
    name: appServicePlanSkuName
    tier: selectedSku.tier
    capacity: selectedSku.capacity
  }
  properties: {
    reserved: true
    maximumElasticWorkerCount: 1
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    Flow_Type: 'Bluefield'
    Request_Source: 'rest'
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    httpsOnly: true
    serverFarmId: appPlan.id
    siteConfig: {
      linuxFxVersion: format('DOCKER|{0}/{1}:{2}', acr.properties.loginServer, containerImageName, containerImageTag)
      appSettings: concat([
        {
          name: 'WEBSITES_PORT'
          value: '8000'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'false'
        }
        {
          name: 'WEBSITE_RUN_FROM_PACKAGE'
          value: '0'
        }
        {
          name: 'APPLICATIONINSIGHTS_CONNECTION_STRING'
          value: appInsights.properties.ConnectionString
        }
        {
          name: 'APPINSIGHTS_INSTRUMENTATIONKEY'
          value: appInsights.properties.InstrumentationKey
        }
      ], customAppSettings)
      acrUseManagedIdentityCreds: true
      alwaysOn: true
      ftpsState: 'Disabled'
    }
  }
}

resource acrPullAssignment 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(webApp.id, 'acrpull')
  scope: acr
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: webApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

output acrLoginServer string = acr.properties.loginServer
output webAppName string = webApp.name
output planId string = appPlan.id
output appInsightsName string = appInsights.name

