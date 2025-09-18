# ExCyTIn-Bench: Evaluating LLM agents on Cyber Threat Investigation

We present the first benchmark to test LLM-based agents on threat hunting in the form of security question-answering pairs.

- The Q&A dataset is in `all_questions.json` file.
- Checkout the incident reports in `incident_reports` folder.
- Explore questions and graphs with jupyter notebooks in `notebooks` folder.

## Database Download

Since including the database download link would reveal the identity of the data provider, we cannot include it here. Thus, the code is for inspection purposes, since the environment cannot be setup without the database.

## Environment Setup

1. We are using MYSQL docker container for the database. Please first install docker and docker-compose and then pull the mysql image:
    ```bash
    docker pull mysql:9.0
    ```

2. Make sure your docker is open, then run the following command to set up the mysql container for 8 different databases:
    ```bash
    cd secgym/env
    bash setup_docker.sh
    ```
    It will run this command: `python secgym/database/setup_database.py --csv <path_to_csv_folder> --port <port> --sql_file <path_to_sql_file> --container_name <container_name> `.

    This script will create 8 different containers. Note that these container are binded to the csv files in the `data_anonymized` folder. This will take up 10GB of disk space.
    Check out volumes with `docker system df -v`.

    To set docker for a database that contains all the data (all 8 attacks), please uncomment the first command in `setup_docker.sh`. Note that this will take up 33GB of disk space.

3. Setup the environment using conda or venv and install the requirements:
    ```bash
    pip install -e .
    ```

4. LLM setup
    We are using [AG2 (Autogen)](https://docs.ag2.ai/latest/) for API calling. Setup your API key in the `secgym/myconfig.py` file. You can follow the instructions [here](https://autogen-ai.github.io/autogen/docs/notebooks/autogen_uniformed_api_calling#config-list-setup).


## Runs

2. Run Baseline
    ```bash
    python experiments/run_exp.py
    ```

## Rerun the question generation process

Currently, we already have the questions generated for the 8 different incidents in the `secgym/questions/tests` folder. If you want to rerun the question generation process, please follow the steps below:

1. Run QA Gen
    ```bash
    python experiments/run_qa_gen.py
    ```
After all the questions are generated, you should expect new files in `secgym/questions` folder like `incident_<i>_qa.json` where `i` is the incident number.
You can upload these files to the `secgym` repo. We already generated the questions there.
