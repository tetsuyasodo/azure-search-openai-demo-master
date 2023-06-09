param location string = resourceGroup().location
param tags object = {}

param vnetName string
param vnetAddressPrefix string = ''

param peSubnetName string
param peSubnetAddressPrefix string = ''

param appSubnetName string
param appSubnetAddressPrefix string = ''

resource vnet 'Microsoft.Network/virtualNetworks@2021-05-01' = {
  name: vnetName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        vnetAddressPrefix
      ]
    }
    subnets: [
      {
        name: peSubnetName
        properties: {
          addressPrefix: peSubnetAddressPrefix
          //networkSecurityGroup: { id: nsg_default.id }
        }
      }
      {
        name: appSubnetName
        properties: {
          addressPrefix: appSubnetAddressPrefix
          //networkSecurityGroup: { id: nsg_default.id }
          delegations: [
            {
              name: 'delegation'
              properties: {
                serviceName: 'Microsoft.Web/serverfarms'
              }
            }
          ]
        }
      }
    ]
  }
}

output vnetId string = vnet.id
output subnetId string = vnet.properties.subnets[0].id
output appSubnetId string = vnet.properties.subnets[1].id
