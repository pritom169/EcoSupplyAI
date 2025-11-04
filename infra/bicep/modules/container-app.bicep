// Azure Container App (generic, parameterized per service)
param name string
param location string
param tags object
param containerAppsEnvironmentId string
param registryLoginServer string
param managedIdentityId string
param imageName string
param containerPort int
param cpu string
param memory string
param minReplicas int
param maxReplicas int
param envVars array

resource containerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: name
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: { '${managedIdentityId}': {} }
  }
  properties: {
    managedEnvironmentId: containerAppsEnvironmentId
    configuration: {
      ingress: {
        external: true
        targetPort: containerPort
        transport: 'http'
      }
      registries: [
        {
          server: registryLoginServer
          identity: managedIdentityId
        }
      ]
    }
    template: {
      containers: [
        {
          name: name
          image: imageName
          resources: { cpu: json(cpu), memory: memory }
          env: envVars
        }
      ]
      scale: {
        minReplicas: minReplicas
        maxReplicas: maxReplicas
        rules: [
          {
            name: 'http-scaling'
            http: { metadata: { concurrentRequests: '50' } }
          }
        ]
      }
    }
  }
}
