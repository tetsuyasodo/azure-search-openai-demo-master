param name string
param location string = resourceGroup().location
param tags object = {}

param customSubDomainName string = name
param deployments array = []
param kind string = 'OpenAI'
param publicNetworkAccess string = 'Enabled'
param sku object = {
  name: 'S0'
}
param private bool = false
param sourceIpAddress string = ''

resource account 'Microsoft.CognitiveServices/accounts@2022-10-01' = {
  name: name
  location: location
  tags: tags
  kind: kind
  properties: {
    customSubDomainName: customSubDomainName
    publicNetworkAccess: publicNetworkAccess
    //shoud be Disabled for closed environment. Set to Enabled for convenience during the workshop
    networkAcls: {
      defaultAction: (private) ? 'Deny' : 'Allow'
      ipRules: (private) ? [
        {
          value: sourceIpAddress 
        }
      ] : []
    } 
  } 
  sku: sku
}

@batchSize(1)
resource deployment 'Microsoft.CognitiveServices/accounts/deployments@2022-10-01' = [for deployment in deployments: {
  parent: account
  name: deployment.name
  properties: {
    model: deployment.model
    raiPolicyName: contains(deployment, 'raiPolicyName') ? deployment.raiPolicyName : null
    scaleSettings: deployment.scaleSettings
  }
}]

output endpoint string = account.properties.endpoint
output id string = account.id
output name string = account.name
