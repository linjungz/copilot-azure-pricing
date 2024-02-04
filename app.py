import streamlit as st
import utils



helper = utils.AzurePricingHelper()

regions_with_az = helper.get_regions_with_AZ()
# Extract the 'displayName' of each region
regions = [region['displayName'] for region in regions_with_az]
# Extract the 'geographyGroup' of each region and remove duplicates by converting the list to a set
geography_groups = list(set(region['geographyGroup'] for region in regions_with_az))

vm_categories = helper.get_all_categories()

selected_geography_groups = []
selected_regions = []
selected_categories = []
selected_vm_series_names = []
selected_vm_vcpus = []

# Fucntion called by submit button
def submit_btn_on_click(region_names, vm_skus, vm_vcpus):
    filtered_vm_skus = helper.filter_vm_sku_by_vcpu(vm_skus, vm_vcpus)
    if filtered_vm_skus:
        result, err = helper.batch_query_prices(region_names, filtered_vm_skus)
        # print(result, err)
        st.markdown(result)
    else:
        st.markdown("No VM SKUs found for the given configuration")



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
            vcpus = helper.get_vm_vcpu_range()
            selected_vm_vcpus = st.multiselect(
                label="vCPU(s)",
                options=vcpus,
                placeholder=f"Select # of vCPUs",
                default=2
            )

        col1, col2, col3 = st.columns(3)
        col2.button("Submit", type="primary", on_click=submit_btn_on_click, args=(selected_regions, selected_vm_sizes, selected_vm_vcpus))
        # col3.button("Reset", type="secondary", on_click=send_message, args=("reset", "assistant"))



    
    



