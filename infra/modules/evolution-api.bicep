targetScope = 'resourceGroup'

@description('Azure region for Evolution API.')
param location string

@description('Tags propagated to the Evolution resources.')
param tags object = {}

@minLength(2)
@maxLength(60)
@description('Name of the Web App hosting the Evolution API.')
param webAppName string

@description('Container image (with registry) used to run Evolution API.')
param containerImageName string = 'atendai/evolution-api:latest'

@description('App Service plan SKU.')
@allowed([
  'B1'
  'S1'
  'P1v3'
])
param appServicePlanSkuName string = 'B1'

@description('App settings array (each element must contain name/value).')
param appSettings array = []

var planNameBase = '${webAppName}-plan'
var planName = substring(planNameBase, 0, min(length(planNameBase), 40))

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

resource plan 'Microsoft.Web/serverfarms@2023-12-01' = {
  name: planName
  location: location
  tags: tags
  sku: {
    name: appServicePlanSkuName
    tier: skuMap[appServicePlanSkuName].tier
    capacity: skuMap[appServicePlanSkuName].capacity
  }
  properties: {
    reserved: true
  }
}

resource webApp 'Microsoft.Web/sites@2023-12-01' = {
  name: webAppName
  location: location
  tags: tags
  properties: {
    httpsOnly: true
    serverFarmId: plan.id
    siteConfig: {
      linuxFxVersion: format('DOCKER|{0}', containerImageName)
      alwaysOn: true
      ftpsState: 'Disabled'
      appSettings: concat([
        {
          name: 'WEBSITES_PORT'
          value: '8080'
        }
        {
          name: 'WEBSITES_ENABLE_APP_SERVICE_STORAGE'
          value: 'false'
        }
      ], appSettings)
    }
  }
}

output webAppName string = webApp.name

