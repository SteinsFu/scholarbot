# Boost Papers Agent

## Setup
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
4. Setup Dify:
    1. Go to the "Settings" tab in Dify.
    2. Install the OpenAI plugin and enter your API key by clicking the "API-KEY" Setup button.
    3. Download or configure any other models and settings as needed.
5. Import the Boost Papers Agent:
    1. Go to the "Studio" tab in Dify.
    2. Click on "Import DSL file" and upload the `dify_dsl/boost-papers-agent.yaml` file from this repository.

## Development of the Dify DSL
(In progress...)