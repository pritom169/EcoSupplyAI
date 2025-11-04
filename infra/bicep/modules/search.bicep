// Azure AI Search
param name string
param location string
param tags object
param sku string = 'basic'
param replicaCount int = 1

resource search 'Microsoft.Search/searchServices@2023-11-01' = {
  name: name
  location: location
  tags: tags
  sku: { name: sku }
  properties: {
    replicaCount: replicaCount
    partitionCount: 1
    hostingMode: 'default'
  }
}

output endpoint string = 'https://${search.name}.search.windows.net'
