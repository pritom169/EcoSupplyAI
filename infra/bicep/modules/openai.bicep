// Azure OpenAI Service
param name string
param location string
param tags object
param sku string = 'S0'
param deployments array

resource openai 'Microsoft.CognitiveServices/accounts@2023-10-01-preview' = {
  name: name
  location: location
  tags: tags
  kind: 'OpenAI'
  sku: { name: sku }
  properties: {
    customSubDomainName: name
    publicNetworkAccess: 'Enabled'
  }
}

resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2023-10-01-preview' = [for d in deployments: {
  parent: openai
  name: d.name
  sku: {
    name: 'Standard'
    capacity: d.capacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: d.model
      version: d.version
    }
  }
}]

output endpoint string = openai.properties.endpoint
