param location string = resourceGroup().location
param tags object = {}

param nsgName string = ''
param securityRules array = []

resource nsg 'Microsoft.Network/networkSecurityGroups@2022-11-01' = {
  name: nsgName
  location: location
  tags: tags
  properties: {
    securityRules: securityRules    
  }
}

output nsgId string = nsg.id
