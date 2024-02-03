import streamlit as st
import utils
from tabulate import tabulate



helper = utils.AzurePricingHelper()
regions_with_az = helper.load_regions_with_AZ()
# Extract the 'displayName' of each region
regions = [region['displayName'] for region in regions_with_az]
# Extract the 'geographyGroup' of each region and remove duplicates by converting the list to a set
geography_groups = list(set(region['geographyGroup'] for region in regions_with_az))
vm_categories = helper.load_categories()
selected_geography_groups = []
selected_regions = []
selected_categories = []
selected_vm_series_names = []

# Fucntion called by submit button
def batch_query_prices(regions, vm_sizes):
    price_data = []
    for vm_size in vm_sizes:
        for region_name in regions:
            region_code = helper.get_region_code_by_name(region_name)
            vm_price = helper.query_vm_price(region_code, vm_size)
            price_data.append([
                vm_size, 
                region_name, 
                "${:.4f}".format(vm_price['payg_hourly']),
                "${:.4f}".format(vm_price['sp_1y_hourly']),
                "${:.4f}".format(vm_price['sp_3y_hourly']),
                "${:.4f}".format(vm_price['ri_1y_hourly']),
                "${:.4f}".format(vm_price['ri_3y_hourly']),
            ])

    print(tabulate(price_data, headers=["VM Size", "Region", "PAYG", "SP 1Y", "SP 3Y", "RI 1Y", "RI 3Y"], tablefmt="pretty"))

with st.sidebar:
    st.title('Copilot for Azure Pricing')

    # Select Regions
    with st.expander("Regions", True):

        # Use the multiselect widget to let the user select geography groups
        selected_geography_groups = st.multiselect(
            'Select the geography groups you are interested in:',
            sorted(geography_groups),
            placeholder="Select geography groups",
            label_visibility="collapsed"
        )

        # Filter the regions to only include regions from the selected geography groups
        if selected_geography_groups == []:
            filtered_regions = [region['displayName'] for region in regions_with_az]
        else:
            filtered_regions = [region['displayName'] for region in regions_with_az if region['geographyGroup'] in selected_geography_groups]

        # Use the multiselect widget to let the user select regions
        selected_regions = st.multiselect(
            'Select the regions you are interested in:',
            sorted(filtered_regions),
            placeholder="Select regions",
            label_visibility="collapsed"
        )

    if selected_regions:
        # Select Virtual Machine Type
        with st.expander("Virtual Machine Type", True):
            # Use the multiselect widget to let the user select categories
            selected_categories = st.multiselect(
                'Select the virtual machine categories you are interested in:',
                vm_categories,
                placeholder="Select VM category",
                label_visibility="collapsed"
            )

            # For each selected category, create a multiselect widget for the user to select VM series
            selected_vm_series = {}
            for category in selected_categories:
                # Filter the VM series to only include series from the selected category
                filtered_vm_series_name = helper.get_vm_series_name_from_category(category)

                # Use the multiselect widget to let the user select VM series
                selected_vm_series[category] = st.multiselect(
                    label="Select VM",
                    options=filtered_vm_series_name,
                    placeholder=f"Select VM series for {category}",
                    label_visibility="collapsed"
                )
            
            for category, vm_series_names in selected_vm_series.items():
                selected_vm_series_names.extend(vm_series_names)
                
            selected_vm_sizes = helper.get_vm_sizes_from_vm_series_names(selected_vm_series_names)
            # print(selected_vm_sizes)

    if selected_vm_series_names:
        with st.expander("Virtual Machine Configuration", True):
            selected_vm_cpu = st.multiselect(
                label="vCPU(s)",
                options=helper.vm_cpu_range(),
                placeholder=f"Select # of vCPUs",
            )

        col1, col2, col3 = st.columns(3)
        col2.button("Submit", type="primary", on_click=batch_query_prices, args=(selected_regions, selected_vm_sizes))
        # col3.button("Reset", type="secondary", on_click=send_message, args=("reset", "assistant"))



    
    



