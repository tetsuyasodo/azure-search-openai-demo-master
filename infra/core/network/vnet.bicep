param location string = resourceGroup().location
param tags object = {}

param vnetName string
param vnetAddressPrefix string = ''

param peSubnetName string
param peSubnetAddressPrefix string = ''

param appSubnetName string
param appSubnetAddressPrefix string = ''

param apimSubnetName string
param apimSubnetAddressPrefix string = ''
param apimNSGId string = ''

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
        name: apimSubnetName
        properties: {
          addressPrefix: apimSubnetAddressPrefix
          networkSecurityGroup: { 
            id: apimNSGId 
          }
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
output subnetId string = filter(vnet.properties.subnets, (subnet) => subnet.name == peSubnetName)[0].id
output appSubnetId string = filter(vnet.properties.subnets, (subnet) => subnet.name == appSubnetName)[0].id
output apimSubnetId string = filter(vnet.properties.subnets, (subnet) => subnet.name == apimSubnetName)[0].id
