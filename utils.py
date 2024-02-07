import json
import requests
import pandas as pd
import os
from tabulate import tabulate


AZURE_PRICING_URL = "https://prices.azure.com/api/retail/prices"
AZURE_PRICING_API_VERION = "2023-01-01-preview"
PRICING_RESPONSE_DIR = "price_api_response"
AZURE_PRICING_MONTHLY_FACTOR=730

class AzurePricingHelper:
    def __init__(self):
        # Open the JSON file
        with open('locations.json') as f:
            self.locations = json.load(f)
        
        with open('locations-AZ.csv', 'r') as f:
            self.region_names_with_AZ = [line.strip() for line in f]
        
        # load vm-series.json and create dicts for :
        # - vm_series_by_category : category -> vm-series
        # - vm_skus_by_series    : vm-series -> vm-skus
        self.vm_series_json = []
        with open('vm-series.json') as f:
            self.vm_series_json = json.load(f)

        self.vm_series_names_by_category = {}
        self.vm_skus_by_series = {}

        for category in self.vm_series_json:
            vm_series = category['vm-series']
            vm_series_names = [item['name'] for item in vm_series]
            self.vm_series_names_by_category[category['category']] = vm_series_names

            for item in vm_series:
                self.vm_skus_by_series[item['name']] = item['vm-skus']

        # load vm-skus-eastus2.json and create dicts for:
        # - vm_configs_by_vm_skus : vm-skus -> vm-configs
                
        # Use East US 2 to retrieve all vm skus
        self.vm_skus_json = []
        with open('vm-skus-eastus2.json') as f:
            self.vm_skus_json = json.load(f)

        self.vm_config_by_vm_sku = {}
        for item in self.vm_skus_json:
            self.vm_config_by_vm_sku[item['name']] = {
                "numberOfCores": item['numberOfCores'],
                "memoryInGB": item['memoryInMB'] / 1024,
            }

        # create dict for converting region name and region code:
        # Read the CSV file into a DataFrame
        df = pd.read_csv('region-codes.csv', header=None, names=['region_name', 'region_code'])
        # Convert the DataFrame to a dictionary
        self.region_code_by_name = df.set_index('region_name')['region_code'].to_dict()

        # create dict for pricing data
        self.price_by_sku_by_region = self.get_all_price_data()

    def get_regions_with_AZ(self):
        # Filter the data
        recommended_locations = [
            {
                'displayName' : item['displayName'],
                'geographyGroup' : item['metadata']['geographyGroup'],
                'geography' : item['metadata']['geography'],
            }
            for item in self.locations if item['metadata'].get('regionCategory') == 'Recommended' and item['displayName'] in self.region_names_with_AZ
            ]

        for region in recommended_locations:
            region['code'] = self.region_code_by_name[region['displayName']]

        # for location in recommended_locations:
        #     print(location['displayName'], location['geographyGroup'], location['geography'])

        return recommended_locations
     
    def get_all_region_codes_with_AZ(self):
        regions = self.get_regions_with_AZ()
        region_codes = []
        for region in regions:
            region_codes.append(region['code'])
        
        return region_codes
    
    def get_all_region_names_with_AZ(self):
        regions = self.get_regions_with_AZ()
        region_codes = []
        for region in regions:
            region_codes.append(region['displayName'])
        
        return region_codes
    
    def get_all_vm_series(self):
        return self.vm_series_json
            
    def get_all_categories(self):
        
        # Extract the 'category' of each virtual machine, remove duplicates by converting the list to a set, and sort in alphabetical order
        categories = [ category for category, _ in self.vm_series_names_by_category.items()]

        return categories
            
    def get_vm_series_name_from_category(self, category):
        return self.vm_series_names_by_category[category]
    
    def get_all_vm_series_names(self):
        all_vm_series_names = []
        for cateogry, item in self.vm_series_names_by_category.items():
            all_vm_series_names.extend(item)

        return all_vm_series_names
        
    def get_vm_skus_from_vm_series_names(self, vm_series_names):
        vm_skus = []

        if vm_series_names:    
            for vm_series_name in vm_series_names:
                vm_skus.extend(self.vm_skus_by_series[vm_series_name])
            
        return vm_skus
    
    
    def get_all_vm_skus(self):
        all_skus = []

        for vm_series, vm_skus in self.vm_skus_by_series.items():
            all_skus.extend(vm_skus)
        
        return all_skus
    
    def get_virtual_machine_config_by_sku(self, vm_sku):
        return self.vm_config_by_vm_sku[vm_sku]
    
    def get_virtual_machine_config_by_skus(self, vm_skus):
        configs = {}
        for sku in vm_skus:
            configs[sku] = self.vm_config_by_vm_sku[sku]

        return configs
            

    def get_vm_vcpu_range(self):
        return [1, 2, 4, 6, 8, 12, 16, 24, 32, 64, 96, 128]
    
    def filter_vm_sku_by_vcpu(self, vm_skus, vcpus):
        filtered_vm_skus = []
        for vm_sku in vm_skus:
            vcpu = self.vm_config_by_vm_sku[vm_sku]['numberOfCores']
            if vcpu in vcpus:
                filtered_vm_skus.append(vm_sku)
        return filtered_vm_skus


    
    def get_region_code_by_name(self, region_name):
        return self.region_code_by_name[region_name]
    

    def retrieve_pricing_data_and_save_local(self, region_list):
        # If region_list is empty, then get all regions with AZ support
        regions = region_list
        if not region_list:
            regions = self.get_all_region_codes_with_AZ()

        for region in regions:
            print(f"Retrieving pricing data for region {region} ...")
            self.get_pricing_api_response_by_region(region)

    def get_pricing_api_response_by_region(self, region_code):

        #construct the param:
        all_vm_series_names = self.get_all_vm_series_names()

        # construct the query for productName
        query = ""
        cur = 1
        for name in all_vm_series_names:
            if cur == 1:
                # this is the first element to process
                query += f"contains(productName, '{name}')"
                cur += 1
            else:
                # not the first one, need to add "or" at the 
                # begining
                query += f" or contains(productName, '{name}')"

        params = {
            "api-version": AZURE_PRICING_API_VERION,
            "$filter": f"armRegionName eq '{region_code}' and serviceName eq 'Virtual Machines' and ({query})",
        }
        # print(params)

        price_items_count = 0
        page = 0

        response = requests.get(url=AZURE_PRICING_URL,params=params)
        if response.status_code == 200:
            price_json = response.json()
            # print(price_json)
            page += 1
            with open(f"./{PRICING_RESPONSE_DIR}/{region_code}-{page}.json", "w") as f:
                f.write(json.dumps(price_json, indent=4))
            

            nextPageLink = price_json['NextPageLink']
            price_items_count += int(price_json['Count'])

            while(nextPageLink):
                response_next = requests.get(nextPageLink)
                if response_next.status_code == 200:
                    price_json_next = response_next.json()
                    page += 1
                    with open(f"./{PRICING_RESPONSE_DIR}/{region_code}-{page}.json", "w") as f:
                        f.write(json.dumps(price_json_next, indent=4))

                    price_items_count += int(price_json_next['Count'])
                    nextPageLink = price_json_next['NextPageLink']

            
            print(f"Processed pricing data for {region_code} : {price_items_count} items / {page} pages.")

        else:
            print(f"Request failed with status code {response.status_code}")
        
    def get_all_price_data(self):
            all_regions = self.get_all_region_codes_with_AZ()
            all_vm_skus = self.get_all_vm_skus()
            
            price_by_sku_by_region = {}
            for sku in all_vm_skus:
                price_by_sku_by_region[sku] = {}

            for region in all_regions:
                # print(f"Loading pricing data from region {region} ...")
                cur = 1
                
                while(os.path.exists(f"./{PRICING_RESPONSE_DIR}/{region}-{cur}.json")):
                    with open(f'./{PRICING_RESPONSE_DIR}/{region}-{cur}.json') as f:
                        price_json = json.load(f)

                        # process the items and update the price dict 
                        for item in price_json['Items']:
                            # Support Pricing query for Linux VM only for now
                            # check if savingsPlan exists, then it's with payg 
                            # The pricing info for a specified VM size includes the following:
                            # region, payg_hourly, sp_1y_hourly, sp_3y_hourly, ri_1y_hourly, ri_3y_hourly
                            if "Windows" in item['productName'] or "Spot" in item['meterName']:
                                continue
                            if item['armSkuName'] not in all_vm_skus:
                                continue
                            
                            if item['armRegionName'] not in price_by_sku_by_region[item['armSkuName']]:
                                # new region for this sku
                                price_by_sku_by_region[item['armSkuName']][item['armRegionName']] = {}

                            price = price_by_sku_by_region[item['armSkuName']][item['armRegionName']]
                            if 'savingsPlan' in item:
                                price['payg_hourly'] = item['retailPrice']
                                price['payg_monthly'] = price['payg_hourly'] * AZURE_PRICING_MONTHLY_FACTOR
                                for sp_item in item['savingsPlan']:
                                    if sp_item['term'] == '3 Years':
                                        price['sp_3y_hourly'] = sp_item['retailPrice']
                                        price['sp_3y_monthly'] = price['sp_3y_hourly'] * AZURE_PRICING_MONTHLY_FACTOR
                                    if sp_item['term'] == '1 Year':
                                        price['sp_1y_hourly'] = sp_item['retailPrice']
                                        price['sp_1y_monthly'] = price['sp_1y_hourly'] * AZURE_PRICING_MONTHLY_FACTOR
                            else: 
                                # it should be reservation:
                                if item['type'] == 'Reservation':
                                    if item['reservationTerm'] == '3 Years':
                                        price['ri_3y_hourly'] = float(item['retailPrice']) / 3 / 12 / AZURE_PRICING_MONTHLY_FACTOR
                                        price['ri_3y_monthly'] = price['ri_3y_hourly'] * AZURE_PRICING_MONTHLY_FACTOR
                                    if item['reservationTerm'] == '1 Year':
                                        price['ri_1y_hourly'] = float(item['retailPrice']) / 12 / AZURE_PRICING_MONTHLY_FACTOR
                                        price['ri_1y_monthly'] = price['ri_1y_hourly'] * AZURE_PRICING_MONTHLY_FACTOR

                        cur += 1
            
            return price_by_sku_by_region
    
    def get_price_data_by_vm_sku_by_region(self, vm_sku, region_code):
        # Get price data by looking up vm sku and region code:
        # Sample price data is :
        # {
        #     "payg_hourly": 14.692,
        #     "sp_3y_hourly": 9.0634948,
        #     "sp_1y_hourly": 12.2296208,
        #     "ri_1y_hourly": 9.604109589041096,
        #     "ri_3y_hourly": 5.45220700152207
        #     "payg_monthly": 10700.16,
        #     "sp_3y_monthly": 6607.2,
        #     "sp_1y_monthly": 8908.16,
        #     "ri_1y_monthly": 6989.12,
        #     "ri_3y_monthly": 3961.6
        # }
        if vm_sku not in self.price_by_sku_by_region:
            raise Exception(f"VM sku {vm_sku} not supported.")

        if region_code not in self.price_by_sku_by_region[vm_sku]:
            raise Exception(f"VM sku {vm_sku} not available in region {region_code}.")
        
        return self.price_by_sku_by_region[vm_sku][region_code]
    
    def batch_query_prices(self, region_names, vm_skus):
        price_data = []
        errmsg = []
        for vm_sku in vm_skus:
            for region_name in region_names:
                region_code = self.get_region_code_by_name(region_name)

                try:
                    vm_price = self.get_price_data_by_vm_sku_by_region(vm_sku, region_code)
                    price_data.append([
                        vm_sku.replace("Standard_", ""), 
                        region_name, 
                        self.vm_config_by_vm_sku[vm_sku]['numberOfCores'],
                        self.vm_config_by_vm_sku[vm_sku]['memoryInGB'],
                        "${:.4f}".format(vm_price['payg_hourly']),
                        "${:.4f}".format(vm_price['sp_1y_hourly']),
                        "${:.4f}".format(vm_price['sp_3y_hourly']),
                        "${:.4f}".format(vm_price['ri_1y_hourly']),
                        "${:.4f}".format(vm_price['ri_3y_hourly']),
                    ])
                except Exception as e:
                    print(e)
                    errmsg.append(e)

        result = tabulate(price_data, headers=["Virtual Machine SKU", "Region", "vCPU", "Memory (GB)", "Pay-as-you-go (Hourly)", "Savings Plans 1 Year (Hourly)", "Savings Plans 3 Years (Hourly)", "Reserved Instances 1 Year (Hourly)", "Reserved Instances 3 Years (Hourly)"], tablefmt="pipe")
        return result, errmsg