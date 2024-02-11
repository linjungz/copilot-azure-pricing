# Copilot for Azure Pricing

The Copilot for Azure Pricing is a demo project created using LangChain and Azure GPT-4. It is designed to provide suggestions on Azure region and virtual machine types based on the latest pricing data and other considerations. This AI-powered agent aims to assist users in making informed decisions when it comes to choosing the most cost-effective options for their Azure deployments.

## Get Started

Follow these steps to get started:

1. Clone the repository:

```bash
git clone https://github.com/linjungz/copilot-azure-pricing.git
```

2. Change into the `copilot-azure-pricing` directory:

```bash
cd copilot-azure-pricing
```

3. Install the required Python packages:

Create virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependancies:

```bash
pip install -r requirements.txt
```

4. Configure environment variables

Create a `.env` file in the root directory and set following environment variables like this:

```bash
AZURE_OPENAI_API_KEY=YOUR_API_KEY
AZURE_OPENAI_API_ENDPOINT=YOUR_ENDPOINT
AZURE_OPENAI_API_DEPLOYMENT=YOUR_DEPLOYMENT_NAME
AZURE_OPENAI_API_VERSION=YOUR_API_VERSION
```

You could refer to the [Azure Quickstart Guide](https://learn.microsoft.com/en-us/azure/ai-services/openai/chatgpt-quickstart?tabs=command-line%2Cpython&pivots=programming-language-python) or [this repo](https://github.com/linjungz/chat-with-your-doc?tab=readme-ov-file#azure-openai-services) to get the `API_KEY`, `ENDPOINT` and `DEPLOYMENT NAME`.

5. Run the app

```bash
$ streamlit run app.py
```