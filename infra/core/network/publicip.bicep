param location string = resourceGroup().location
param tags object = {}

param publicIpName string

resource publicip 'Microsoft.Network/publicIPAddresses@2022-07-01' = {
  name: publicIpName
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Regional'
  }
  properties: {
    publicIPAddressVersion: 'IPv4'
    publicIPAllocationMethod:'Static'
    dnsSettings: {
      domainNameLabel: toLower(publicIpName)
    }
  }
}
output pipId string = publicip.id
