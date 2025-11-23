targetScope = 'resourceGroup'

@description('Location for the MongoDB workload.')
param location string

@description('Common resource tags.')
param tags object

@description('Name of the container group that will host MongoDB.')
param containerGroupName string

@description('DNS label (lowercase, globally unique per region) for the public endpoint.')
@minLength(3)
@maxLength(60)
param dnsNameLabel string

@description('Docker image used for MongoDB.')
param mongoImage string = 'mongo:7.0'

@description('Registry login server for the Mongo image (leave empty for Docker Hub).')
param registryLoginServer string = ''

@description('Registry username when pulling from a private registry.')
param registryUsername string = ''

@secure()
@description('Registry password when pulling from a private registry.')
param registryPassword string = ''

@description('Port exposed by the MongoDB container.')
param mongoPort int = 27017

@description('Admin username injected into the Mongo container.')
param adminUsername string = 'mongoadmin'

@secure()
@description('Admin password for MongoDB. Provide a strong value at deploy time.')
param adminPassword string

@description('CPU cores reserved for the Mongo container.')
param cpuCores int = 1

@description('Memory (GB) reserved for the Mongo container.')
param memoryInGb int = 2

@description('Storage account used to persist Mongo data (lowercase letters and numbers).')
@minLength(3)
@maxLength(24)
param storageAccountName string

@description('Azure Files share that backs /data/db.')
@minLength(3)
@maxLength(63)
param fileShareName string = 'mongodata'

@description('Quota (GB) for the Azure Files share that stores Mongo data.')
param fileShareQuota int = 10

var storageApiVersion = '2023-01-01'

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    allowBlobPublicAccess: false
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
  }
}

resource fileService 'Microsoft.Storage/storageAccounts/fileServices@2023-01-01' = {
  name: 'default'
  parent: storage
}

resource fileShare 'Microsoft.Storage/storageAccounts/fileServices/shares@2023-01-01' = {
  name: fileShareName
  parent: fileService
  properties: {
    shareQuota: fileShareQuota
  }
}

var storageKey = listKeys(storage.id, storageApiVersion).keys[0].value

resource containerGroup 'Microsoft.ContainerInstance/containerGroups@2023-05-01' = {
  name: containerGroupName
  location: location
  tags: tags
  properties: {
    osType: 'Linux'
    restartPolicy: 'Always'
    ipAddress: {
      type: 'Public'
      dnsNameLabel: dnsNameLabel
      ports: [
        {
          protocol: 'TCP'
          port: mongoPort
        }
      ]
    }
    imageRegistryCredentials: empty(registryLoginServer) ? [] : [
      {
        server: registryLoginServer
        username: registryUsername
        password: registryPassword
      }
    ]
    containers: [
      {
        name: 'mongo'
        properties: {
          image: mongoImage
          resources: {
            requests: {
              cpu: cpuCores
              memoryInGB: memoryInGb
            }
          }
          ports: [
            {
              port: mongoPort
            }
          ]
          environmentVariables: [
            {
              name: 'MONGO_INITDB_ROOT_USERNAME'
              value: adminUsername
            }
            {
              name: 'MONGO_INITDB_ROOT_PASSWORD'
              secureValue: adminPassword
            }
          ]
          volumeMounts: [
            {
              name: 'mongo-data'
              mountPath: '/data/db'
            }
          ]
        }
      }
    ]
    volumes: [
      {
        name: 'mongo-data'
        azureFile: {
          shareName: fileShareName
          storageAccountName: storageAccountName
          storageAccountKey: storageKey
        }
      }
    ]
  }
}

var fqdn = containerGroup.properties.ipAddress.fqdn

@secure()
output connectionString string = format(
  'mongodb://{0}:{1}@{2}:{3}/?authSource=admin&tls=false',
  adminUsername,
  adminPassword,
  fqdn,
  mongoPort
)

output fqdn string = fqdn
output port int = mongoPort

