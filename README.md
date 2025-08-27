# Boost Papers Agent

## Setup

### Method 1: Use the Dify Online Service
1. Go to https://cloud.dify.ai/apps and register an account.
2. Setup Dify (Plugins and API keys):
    1. Go to the "Settings" tab in Dify.
    2. Download plugins and configure settings:
       1. Click "Plugins" on the top-right corner
       2. Search and download the following plugins:
          - `Jina AI`
          - `Gemini`
          - `OpenAI`
          - `Slack Bot`
    3. For Gemeni or OpenAI, go to "Settings" > "Model Provider" and enter your API key by clicking the "API-KEY" Setup button.
    4. For other plugins requiring API keys (e.g. Jina AI)
       1. Obtain your API key from your service (e.g. https://jina.ai/)
       2. In Dify, go to "Plugin" and click your plugin (e.g. Jina AI), and enter your api key in the Authorization field. 
3. Import the Boost Papers Agent:
    1. Go to the "Studio" tab in Dify.
    2. Click on "Import DSL file" and upload the `dify_dsl/boost-papers-agent.yaml` file from this repository.

### Method 2: Setup Local Dify Server (or Deploy to Cloud)
1. Install Docker:
    - For Ubuntu, you can follow the official Docker installation guide: [Install Docker Engine on Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
    - For MacOS/Windows, you can download Docker Desktop from [Docker Hub](https://www.docker.com/products/docker-desktop).
2. Dify:
    1. Clone the Dify repository:
        ```bash
        git clone https://github.com/langgenius/dify.git
        cd dify/docker
        cp .env.example .env
        ```
    2. Run Dify:
        ```bash
        sudo docker compose up -d
        ```
3. Access Dify:
    1. Open your web browser and go to `http://localhost` to access the Dify web interface.
        - Or if you are running Dify on a remote server, replace `localhost` with the server's IP address or domain name.
    2. Create an account and log in.
4. Setup Dify (Plugins and API keys):
    1. Go to the "Settings" tab in Dify.
    2. Download plugins and configure settings:
       1. Click "Plugins" on the top-right corner
       2. Search and download the following plugins:
          - `Jina AI`
          - `Gemini`
          - `OpenAI`
          - `Slack Bot`
    3. For Gemeni or OpenAI, go to "Settings" > "Model Provider" and enter your API key by clicking the "API-KEY" Setup button.
    4. For other plugins requiring API keys (e.g. Jina AI)
       1. Obtain your API key from your service (e.g. https://jina.ai/)
       2. In Dify, go to "Plugin" and click your plugin (e.g. Jina AI), and enter your api key in the Authorization field. 
5. Import the Boost Papers Agent:
    1. Go to the "Studio" tab in Dify.
    2. Click on "Import DSL file" and upload the `dify_dsl/boost-papers-agent.yaml` file from this repository.

## Development 

### Dify Workflow
- [x] Accept pdf url as input
- [x] Accept pdf file as input
- [x] Extract text from pdf url
- [x] Extract text from pdf file
- [x] Instruct LLM to summarize paper
- [x] Instruct LLM to find related papers
- [ ] Slack integration (require AWS or GCP)

### Others
- [ ] (in progress...) PDF embeddings visualization

*← Feel free to add any TODOs...*




## PDF embeddings visualization (in progress...)

Create an interactive 3D visualization of how a set of PDFs are semantically correlated using sentence embeddings (PyTorch).

### Install
```bash
conda create -n boost-proj python==3.12
conda activate boost-proj
pip install -r requirements.txt
```

### Run (CLI)
Create embeddings
```bash
python pdf_correlator.py
```

Visualize embeddings
```bash
tensorboard --logdir tensorboard_logs
```
