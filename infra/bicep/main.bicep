// =============================================================================
// EcoSupplyAI - Azure Infrastructure (Bicep)
// =============================================================================
targetScope = 'subscription'

@allowed(['dev', 'staging', 'prod'])
param environment string = 'dev'
param location string = 'eastus2'
param projectName string = 'ecosupplyai'
@secure()
param azureOpenAIApiKey string = ''
@secure()
param jwtSecretKey string = ''

var prefix = '${projectName}-${environment}'
var tags = {
  project: projectName
  environment: environment
  managedBy: 'bicep'
}

// Resource Group
resource rg 'Microsoft.Resources/resourceGroups@2023-07-01' = {
  name: '${prefix}-rg'
  location: location
  tags: tags
}

// Managed Identity
module identity 'modules/identity.bicep' = {
  name: '${prefix}-identity'
  scope: rg
  params: { name: '${prefix}-identity', location: location, tags: tags }
}

// Azure Container Registry
module acr 'modules/acr.bicep' = {
  name: '${prefix}-acr'
  scope: rg
  params: {
    name: replace('${prefix}acr', '-', '')
    location: location
    tags: tags
    sku: environment == 'prod' ? 'Premium' : 'Standard'
    managedIdentityPrincipalId: identity.outputs.principalId
  }
}

// Azure OpenAI Service
module openai 'modules/openai.bicep' = {
  name: '${prefix}-openai'
  scope: rg
  params: {
    name: '${prefix}-openai'
    location: location
    tags: tags
    sku: 'S0'
    deployments: [
      { name: 'gpt-4o', model: 'gpt-4o', version: '2024-08-06', capacity: environment == 'prod' ? 80 : 20 }
      { name: 'text-embedding-3-large', model: 'text-embedding-3-large', version: '1', capacity: environment == 'prod' ? 120 : 30 }
    ]
  }
}

// Azure AI Search
module search 'modules/search.bicep' = {
  name: '${prefix}-search'
  scope: rg
  params: {
    name: '${prefix}-search'
    location: location
    tags: tags
    sku: environment == 'prod' ? 'standard' : 'basic'
    replicaCount: environment == 'prod' ? 3 : 1
  }
}

// Key Vault
module keyvault 'modules/keyvault.bicep' = {
  name: '${prefix}-kv'
  scope: rg
  params: {
    name: '${prefix}-kv'
    location: location
    tags: tags
    managedIdentityPrincipalId: identity.outputs.principalId
    secrets: [
      { name: 'azure-openai-api-key', value: azureOpenAIApiKey }
      { name: 'jwt-secret-key', value: jwtSecretKey }
    ]
  }
}

// Azure Monitor / Application Insights
module monitoring 'modules/monitoring.bicep' = {
  name: '${prefix}-monitoring'
  scope: rg
  params: {
    name: '${prefix}-monitoring'
    location: location
    tags: tags
    logAnalyticsRetentionDays: environment == 'prod' ? 90 : 30
  }
}

// Container Apps Environment
module containerAppsEnv 'modules/container-apps-env.bicep' = {
  name: '${prefix}-cae'
  scope: rg
  params: {
    name: '${prefix}-cae'
    location: location
    tags: tags
    logAnalyticsWorkspaceId: monitoring.outputs.logAnalyticsWorkspaceId
    appInsightsConnectionString: monitoring.outputs.appInsightsConnectionString
  }
}

// Container Apps (one per microservice)
var serviceDefinitions = [
  { name: 'api-gateway',       port: 8000, cpu: '0.5',  memory: '1Gi',   minReplicas: 2, maxReplicas: 10 }
  { name: 'chat-agent',        port: 8001, cpu: '0.5',  memory: '1Gi',   minReplicas: 1, maxReplicas: 5  }
  { name: 'rag-pipeline',      port: 8002, cpu: '1.0',  memory: '2Gi',   minReplicas: 2, maxReplicas: 6  }
  { name: 'scoring-service',   port: 8003, cpu: '0.5',  memory: '1Gi',   minReplicas: 2, maxReplicas: 8  }
  { name: 'forecast-service',  port: 8004, cpu: '1.0',  memory: '2Gi',   minReplicas: 1, maxReplicas: 3  }
  { name: 'content-generator', port: 8005, cpu: '0.5',  memory: '1Gi',   minReplicas: 1, maxReplicas: 5  }
  { name: 'workflow-engine',   port: 8006, cpu: '0.25', memory: '0.5Gi', minReplicas: 1, maxReplicas: 3  }
  { name: 'mcp-server',        port: 8007, cpu: '0.25', memory: '0.5Gi', minReplicas: 1, maxReplicas: 3  }
]

module containerApps 'modules/container-app.bicep' = [for svc in serviceDefinitions: {
  name: '${prefix}-ca-${svc.name}'
  scope: rg
  params: {
    name: '${prefix}-${svc.name}'
    location: location
    tags: tags
    containerAppsEnvironmentId: containerAppsEnv.outputs.environmentId
    registryLoginServer: acr.outputs.loginServer
    managedIdentityId: identity.outputs.identityId
    imageName: '${acr.outputs.loginServer}/${svc.name}:latest'
    containerPort: svc.port
    cpu: svc.cpu
    memory: svc.memory
    minReplicas: environment == 'prod' ? svc.minReplicas : 1
    maxReplicas: environment == 'prod' ? svc.maxReplicas : 2
    envVars: [
      { name: 'SERVICE_NAME',  value: svc.name }
      { name: 'SERVICE_PORT',  value: string(svc.port) }
      { name: 'ENVIRONMENT',   value: environment }
      { name: 'AZURE_OPENAI_ENDPOINT',  secretRef: 'azure-openai-endpoint' }
      { name: 'AZURE_OPENAI_API_KEY',   secretRef: 'azure-openai-api-key' }
      { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: monitoring.outputs.appInsightsConnectionString }
    ]
  }
}]

output resourceGroupName string = rg.name
output acrLoginServer string = acr.outputs.loginServer
output openAIEndpoint string = openai.outputs.endpoint
output searchEndpoint string = search.outputs.endpoint
