from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
import os
from langchain.agents import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.agents.format_scratchpad.openai_tools import format_to_openai_tool_messages
from langchain.agents.output_parsers.openai_tools import OpenAIToolsAgentOutputParser
from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, HumanMessage
import utils

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
def get_available_regions() -> dict:
    """
    Return a json of all available Azure regions with support for Availability Zones
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
def get_virtual_machine_config_by_sku(sku: str) -> dict:
    """
    Return a json of the virtual machine configuration, by a specified virtual machine sku
    The configuration is a dictionary and contains following information:
    - numberOfCores: number of VCPUs
    - memoryInGB: memory capactiy in GiB
    """

tools = [
    get_available_regions, 
    get_latest_virtual_machines_types,
    get_virtual_machine_config_by_sku
]
llm_with_tools = llm.bind_tools(tools)

# Define Prompt

prompt = ChatPromptTemplate.from_messages([
    ("system", 
     """
     You're a powerful and friendly AI Agent for Azure cloud planning.

     # Scope

     ## Provide Suggestion
     You could provide suggestion on following topics:

     ### Which region(s) to choose based on following criteria
         - The region should support availability zones
         - The region should be near to the user's geographic location
        
     ### Which Virtual Machine type(s) to choose strictly based on following criteria
         - Use only latest or widely used virtual machine type
         - The use case for the user's application, for example:
           #### Whether it's production or for test.
                - If it's for test, vm with burstable cpu could be used for economical purpose. But this is not recommended for production.
         - The number of VCPUs and memory capacity required for the application
     
     But before you provide any suggestion, you need to understand user's requirement first:
     - Whether this application is production or test
     - The number of VCPUs and memory capacity required for the application
     - The geographic location of the user

     If you don't know the answer, don't make it up.

     You don't answer any question about other cloud providers.
     If user asks about other cloud providers, you should respond with "I can only help with Azure cloud."
     If user asks about other topics, you should respond with "I can only help with questions related to Azure cloud."

     # Response
     - The language of your response should be strictly adhere to user's input. For example, if user input is in Chinese, please answer in Chinese.
     - Please answer the question concisely. You could explain the details if user requested.
     - When referring to VM types, you could use more user-friendly name, for example, when refer to "Standard_D2asv5", you could simply sai D2asv5
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

agent_executor = AgentExecutor(agent=agent, tools=tools).with_config(
    {"run_name": "Agent"}
)

# # Invoke Agent with chat_history
# # input1 = "how many letters in the word educa?"
# # result = agent_executor.invoke({"input": input1, "chat_history": chat_history})
# # chat_history.extend(
# #     [
# #         HumanMessage(content=input1),
# #         AIMessage(content=result["output"])
# #     ]
# # )
# # agent_executor.invoke({"input": "", "chat_history": chat_history})

async def chat():
    chat_history = []

    while(True):
        user_input = input("User: ")
        chunks = []
        final_result = ""
        
        # for chunk in agent_executor.stream(
        #     { "input": user_input, "chat_history": chat_history }
        # ):
        #     # Agent Action
        #     if "actions" in chunk:
        #         for action in chunk["actions"]:
        #             print(f"Calling Tool: `{action.tool}` with input `{action.tool_input}`")
        #     # Observation
        #     elif "steps" in chunk:
        #         for step in chunk["steps"]:
        #             print(f"Tool Result: `{step.observation}`")
        #     # Final result
        #     elif "output" in chunk:
        #         print(f'Final Output: {chunk["output"]}')
        #         final_result = chunk["output"]
        #     else:
        #         raise ValueError()
        #     print("---")

        async for event in agent_executor.astream_events(
            { "input": user_input, "chat_history": chat_history},
            version="v1",
        ):
            kind = event["event"]
            if kind == "on_chain_start":
                if (
                    event["name"] == "Agent"
                ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                    print(
                        f"Starting agent: {event['name']} with input: {event['data'].get('input')}"
                    )
            elif kind == "on_chain_end":
                if (
                    event["name"] == "Agent"
                ):  # Was assigned when creating the agent with `.with_config({"run_name": "Agent"})`
                    print()
                    print("--")
                    print(
                        f"Done agent: {event['name']} with output: {event['data'].get('output')['output']}"
                    )
            if kind == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    # Empty content in the context of OpenAI means
                    # that the model is asking for a tool to be invoked.
                    # So we only print non-empty content
                    print(content, end="|")
            elif kind == "on_tool_start":
                print("--")
                print(
                    f"Starting tool: {event['name']} with inputs: {event['data'].get('input')}"
                )
            elif kind == "on_tool_end":
                print(f"Done tool: {event['name']}")
                print(f"Tool output was: {event['data'].get('output')}")
                print("--")
            

        chat_history.extend(
            [
                HumanMessage(content=user_input),
                AIMessage(content=final_result)
            ]
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(chat())