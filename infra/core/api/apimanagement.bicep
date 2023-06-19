param name string
param location string = resourceGroup().location
param tags object = {}

param publisherEmail string
param publisherName string

//vnet itegration
param private bool = false
param apimsubnetId string
param publicIpAddressId string

@allowed([
  'Developer'
  'Standard'
  'Premium'
])
param sku string = 'Developer'


@allowed([
  1
  2
])
param skuCount int = 1

resource apiManagementService 'Microsoft.ApiManagement/service@2021-08-01' = {
  name: name
  location: location
  tags: tags
  sku: {
    name: sku
    capacity: skuCount
  }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    // vnet integration for access backend via private endpoint
    virtualNetworkType: ( private ) ? 'External' : 'None'
    virtualNetworkConfiguration: ( private ) ? {
        subnetResourceId: apimsubnetId 
    } : null
    publicIpAddressId: ( private ) ? publicIpAddressId : null
  }
}
