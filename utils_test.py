import utils
import os
import json

helper = utils.AzurePricingHelper()

# # Get all vm skus:
# print(helper.get_all_vm_skus())

# # Get all regions with AZ, with all information
# print(helper.get_regions_with_AZ())

# # Get all regions with AZ, with only code
# print(helper.get_all_region_codes_with_AZ())

# Retrieve pricing data
regions = ["westus2", "eastus2"]
# regions = []
# helper.retrieve_pricing_data_and_save_local(regions)

# Get VM sku by filtering config
# vm_skus = ["Standard_F4s_v2", "Standard_D2as_v5"]
# vcpus = [2, 4]
# filtered_vm_skus = helper.filter_vm_sku_by_vcpu(vm_skus, vcpus)
# print(filtered_vm_skus)

# Get vm config by SKU
vm_skus = "Standard_D4as_v5"
print(helper.get_virtual_machine_config_by_sku(vm_skus))

# Get all price data:
# print(json.dumps(helper.get_price_data(), indent=4))

# Get price data for a specified vm sku and region
# vm_sku = "Standard_D4as_v5"
# region_code = "westus2"
# print(json.dumps(helper.get_price_data_by_vm_sku_by_region(vm_sku, region_code), indent=4))

# Batch query price data and generate table for output
# vm_skus = ["Standard_D4as_v5", "Standard_D8as_v5"]
# region_names = ["East US 2", "Southeast Asia"]
# result, e = helper.batch_query_prices(region_names, vm_skus)
# print(result, e)


