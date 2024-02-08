import streamlit as st
import utils
from langchain_community.callbacks import StreamlitCallbackHandler
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
from langchain.agents import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage

AGENT_LANGUAGE = "Simplified Chinese"


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


# Sidebar for user to manually choose the region/vm types they want
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

# Chat UI for interact with agent directly
st_callback = StreamlitCallbackHandler(st.container())

load_dotenv()

# Define LLM
llm = AzureChatOpenAI(
    api_version="2023-12-01-preview",
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_API_ENDPOINT"),
    model="gpt-4-1106-preview",
    temperature=0,
    streaming=True
)

# Define Tool

helper = utils.AzurePricingHelper()

# @tool
# def get_word_length(word: str) -> int:
#     """Return the length of a word"""
#     return len(word)

@tool
def get_regions_with_availability_zones() -> dict:
    """
    Return a json of all Azure regions,  with support for Availability Zones
    Actually Azure has lots of regions, but here we only return part of them, which has support for Availability Zones.
    Each region has the following information:
    displayName: The user-friendly name of the region. For example, "West US 2" or "Southeast Asia".
    geography: The geography or country to which the region resides. For example, "Brazil" or "Italy" or "United States".
    geographyGroup: The geography group to which the region belongs. For example, "Asia Pacific" or "Europe" or "Middle East" or "US" or "South America".
    code: The codename of the region, which is used to identify the region in the API. For example, "westus2" or "southeastasia".
    """
    regions = helper.get_regions_with_AZ()
    return regions

@tool
def get_latest_virtual_machines_types() -> dict:
    """
    Return a json of all Azure virtual machines(VMs) types or skus to query.
    # All the VMs are grouped by Category
    - category: name of the category, for example "General Purpose" or "Compute Optimized". 
    - description: , describing the target use cases for the VMs.
    # Each category has a list of Virtual Machine Series.
    - name: name of the series, for example "Dasv5" or "Esv5".
    - description: describing the hardware configuration, for example which CPU is used, CPU memomry ratio and target use cases.
    - skus: a list of VM skus. This is a code name for the VM sizes, for example "Standard_D4as_v5" or "Standard_D8as_v5".
    Note that this's not a completed list of all available types. But we need only the latest or widely used ones. If user request to support more types, they could contact author of this AI agent.
    """
    return helper.get_all_vm_series()

@tool
def get_virtual_machine_config_by_skus(skus: list) -> dict:
    """
    Return a json of the virtual machine configuration, by a list of specified virtual machine skus
    The configuration is a dictionary and contains following information:
    The key is the SKU of the virtual machine
    The value is a dict for the vm configuration:
    - numberOfCores: number of VCPUs
    - memoryInGB: memory capactiy in GiB
    """
    return helper.get_virtual_machine_config_by_skus(skus)

@tool
def get_latest_virtual_machine_price(sku: str, region: str) -> dict:
    """
    Return a json of latest virtual machine price data.
    The price data depends on virtual machine sku and region.
    The sku is the code name for the virtual machine, for example "Standard_D4as_v5" or "Standard_D8as_v5".
    The region name is the code name for the region, for example "westus2" or "southeastasia".
    The returned price data contains following information:
    - payg_hourly:  hourly price, for Pay-as-you-go 
    - sp_3y_hourly: hourly price, for Savings Plans 3 Years 
    - sp_1y_hourly: hourly price, for Savings Plans 1 Year
    - ri_3y_hourly: hourly price, for Reserved Instances 3 Years
    - ri_1y_hourly: hourly price, for Reserved Instances 1 Year
    All the price data are in USD.
    """
    return helper.get_price_data_by_vm_sku_by_region(sku, region)

tools = [
    get_regions_with_availability_zones, 
    get_latest_virtual_machines_types,
    get_virtual_machine_config_by_skus,
    get_latest_virtual_machine_price
]
llm_with_tools = llm.bind_tools(tools)

# Define Prompt

prompt = ChatPromptTemplate.from_messages([
    ("system", 
     f"""
     You're a powerful and friendly AI Agent that provides suggestions to user who are planning to use Azure cloud.

     # Task Description
     Your main job is to provide suggestions on Azure regions and virtual machines.
     
     ## Understand Requirement
     Before making any suggestion, you need to understand user's requirements first:
     - Whether application is for production or test.
     This is extremely important. Don't choose virtual machine types with burstable CPU for production.
     - The number of VCPUs and memory capacity requried by the virtual machines.
     - The geographic location of the application. Need to know where the end users of the application are.
     
     ## Provide Suggestions
     Based on user's requirement, you could provide suggestions.
     Here's a list of rules that you should follow to make the suggestions and explain why to the user.

     ### Region:
     - Although there's lots of Azure regions globally, you only provide suggestions on regions with support for availability zones.
     - The region should be near to the end users of the application. If the end users are spread in a very large geographic area, 
     then choose the location where the the main portion of the end users are. Otherwise, suggest the user to choose more than one region to support this application.
     - For applications running in South America, you could suggest regions not only in South America, but also in North America. 
     You could suggest that user could not only compare the prices in different regions, but also take network latency into consideration. 
     This rule also applies to applications running in Africa. You could suggest user could check regions in Europe at the same time.
     
     ### Virtual Machine Types:
     - Use only latest or widely used virtual machine type. 
     - Whether this application is for production or test.
     If it's for test, vm with burstable cpu could be used for economical purpose. 
     But this is not recommended for production.
     - The number of VCPUs and memory capacity should be sufficient for the application
     You could check the price for virtual machine types that satisfied these rules and suggest one virtual machine types that's most cost-effective.

     ### Virtual Machine Prices:
     - By default, provide the pay-as-you-go price for virtual machine is enough. 
     - Price is dependent on region. That is, same virtual machine type could have different prices in different regions.
     So when querying price, you should check price of sku in each region requested.
     - All the prices are in USD. Please format it using currency.
     
     ## Summary
     You should ask if the suggestion is ok for the user. 
     If user is satisfied with the suggestion, you could generate a report to summarize the user's requirement and your suggest. 
     The summary should include following parts:
     - User's requirement
     - Suggestions for region, virtual machine types and price. 
     The output should be in a table to be more readable.
     The VM configuration(CPU and memory) should be included.
     The price is in USD and should be formatted as currency
     - Mind the user that the suggestion is generated by AI Agent, with the personal knowledge and experience provided by the author of this AI Agent. It's not Azure offical recommendation.
     User could check the offical Azure website to double check all the information before making final decision.


     # Cautious

     If you don't know the answer, don't make it up.
     When answering the question about price, make sure you refer to the latest price data for each sku in each region requested.
     You don't answer any question about other cloud providers.
     If user asks about other cloud providers, you should respond with "I can only help with Azure cloud."
     If user asks about other topics, you should respond with "I can only help with questions related to Azure cloud."

     # Response
     - The language of your response should be in {AGENT_LANGUAGE} . 
     - Please answer the question concisely. You could explain the details if user requested.
     - When referring to VM types, you could use more user-friendly name, for example, when refer to "Standard_D2asv5", you could simply sai D2asv5
     - When referring to region, you should stick to English only. Don't translate the region name to other language.
     """),
    MessagesPlaceholder(variable_name="chat_history"),
    ("user", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Define Agent
agent = (
    {
        "input": lambda x: x["input"],
        "agent_scratchpad": lambda x: format_to_openai_tool_messages(
            x["intermediate_steps"]
        ),
        "chat_history": lambda x: x["chat_history"]
    }
    | prompt
    | llm_with_tools
    | OpenAIToolsAgentOutputParser()
)

agent_executor = AgentExecutor(
    agent=agent, 
    tools=tools, 
    verbose=True,
    max_execution_time=60).with_config(
    {"run_name": "Agent"}
)

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

chat_history = []


# Display chat messages from history on app rerun
chat_history_user = ""
chat_history_assistant = ""

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
    if message['role'] == 'user':
        chat_history_user = message["content"]
    if message['role'] == 'assistant':
        chat_history_assistant = message['content']
        chat_history.extend(
            [
                HumanMessage(content=chat_history_user),
                AIMessage(content=chat_history_assistant)
            ]
        )
        
    print("chat_history: ", chat_history)
    print("messages: ", st.session_state.messages)



if user_input := st.chat_input():
    st.chat_message("user").write(user_input)
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("assistant"):
        st_callback = StreamlitCallbackHandler(
            st.container(),
            # expand_new_thoughts=False
        )
        response = agent_executor.invoke(
            {"input": user_input, "chat_history": chat_history},
            {"callbacks": [st_callback]}
        ) 
        st.write(response["output"])   
        st.session_state.messages.append({"role": "assistant", "content": response["output"]})
    

    



