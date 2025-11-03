// Managed Identity for EcoSupplyAI services
param name string
param location string
param tags object

resource managedIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: name
  location: location
  tags: tags
}

output principalId string = managedIdentity.properties.principalId
output identityId string = managedIdentity.id
