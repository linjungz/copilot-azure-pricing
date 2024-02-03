import json
import requests
import pandas as pd

AZURE_PRICING_URL = "https://prices.azure.com/api/retail/prices"
AZURE_PRICING_API_VERION = "2023-01-01-preview"

class AzurePricingHelper:
    def __init__(self):
        # Open the JSON file
        with open('locations.json') as f:
            self.locations = json.load(f)
        
        with open('locations-AZ.csv', 'r') as f:
            self.region_names_with_AZ = [line.strip() for line in f]
        
        # load vm-series.json and create dicts for :
        # - vm_series_by_category : category -> vm-series
        # - vm_sizes_by_series    : vm-series -> vm-sizes
        self.vm_series_json = []
        with open('vm-series.json') as f:
            self.vm_series_json = json.load(f)

        self.vm_series_names_by_category = {}
        self.vm_sizes_by_series = {}

        for category in self.vm_series_json:
            vm_series = category['vm-series']
            vm_series_names = [item['name'] for item in vm_series]
            self.vm_series_names_by_category[category['category']] = vm_series_names

            for item in vm_series:
                self.vm_sizes_by_series[item['name']] = item['vm-sizes']

        # load vm-sizes-eastus2.json and create dicts for:
        # - vm_configs_by_vm_sizes : vm-sizes -> vm-configs
                
        self.vm_sizes_json = []
        with open('vm-sizes-eastus2.json') as f:
            self.vm_sizes = json.load(f)

        self.vm_configs_by_vm_sizes = {}
        for item in self.vm_sizes_json:
            self.vm_configs_by_vm_sizes[item['name']] = {
                "numberOfCores": item['numberOfCores'],
                "memoryInGB": item['memoryInMB'] / 1024,
            }

        # create dict for converting region name and region code:
        # Read the CSV file into a DataFrame
        df = pd.read_csv('region-codes.csv', header=None, names=['region_name', 'region_code'])
        # Convert the DataFrame to a dictionary
        self.region_code_by_name = df.set_index('region_name')['region_code'].to_dict()

    def load_regions_with_AZ(self):
        # Filter the data
        recommended_locations = [
            {
                'displayName' : item['displayName'],
                'geographyGroup' : item['metadata']['geographyGroup'],
                'geography' : item['metadata']['geography'],
            }
            for item in self.locations if item['metadata'].get('regionCategory') == 'Recommended' and item['displayName'] in self.region_names_with_AZ
            ]

        # for location in recommended_locations:
        #     print(location['displayName'], location['geographyGroup'], location['geography'])

        return recommended_locations

    def load_categories(self):
        
        # Extract the 'category' of each virtual machine, remove duplicates by converting the list to a set, and sort in alphabetical order
        categories = [ category for category, _ in self.vm_series_names_by_category.items()]

        return categories
            
    def get_vm_series_name_from_category(self, category):
        return self.vm_series_names_by_category[category]
        
    def get_vm_sizes_from_vm_series_names(self, vm_series_names):
        vm_sizes = []

        if vm_series_names:    
            for vm_series_name in vm_series_names:
                vm_sizes.extend(self.vm_sizes_by_series[vm_series_name])
            
        return vm_sizes

    def vm_cpu_range(self):
        return [1, 2, 4, 6, 8, 12, 16, 24, 32, 64, 96, 128]
    
    def get_region_code_by_name(self, region_name):
        return self.region_code_by_name[region_name]
        
    def query_vm_price(self, region_code, vm_size):
        params = {
            "api-version": AZURE_PRICING_API_VERION,
            "$filter": f"serviceName eq 'Virtual Machines' and armRegionName eq '{region_code}' and skuName eq '{vm_size}' and contains(productName, 'Virtual Machines')",
        }

        price = {}
        response = requests.get(AZURE_PRICING_URL, params=params)
        # Check that the request was successful
        if response.status_code == 200:
            # Parse the response as JSON
            pricing_info = response.json()
            # print(pricing_info)
            
            # Extract the price from the response
            for item in pricing_info['Items']:
                # Support Linux only for now
                # check if savingsPlan exists, then it's with payg 
                if 'savingsPlan' in item:
                    price['payg_hourly'] = item['retailPrice']
                    for sp_item in item['savingsPlan']:
                        if sp_item['term'] == '3 Years':
                            price['sp_3y_hourly'] = sp_item['retailPrice']
                        if sp_item['term'] == '1 Year':
                            price['sp_1y_hourly'] = sp_item['retailPrice']
                else: 
                    # it should be reservation:
                    if item['type'] == 'Reservation':
                        if item['reservationTerm'] == '3 Years':
                            price['ri_3y_hourly'] = float(item['retailPrice']) / 3 / 12 / 730
                        if item['reservationTerm'] == '1 Year':
                            price['ri_1y_hourly'] = float(item['retailPrice']) / 12 / 730
            # print(price)
        else:
            print(f"Request failed with status code {response.status_code}")
        
        return price

        
            