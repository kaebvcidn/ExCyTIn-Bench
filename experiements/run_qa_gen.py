from secgym.myconfig import CONFIG_LIST
from secgym.qagen.qa_gen import QAGen
import os
import argparse
import json
import random

def get_args():
    parser = argparse.ArgumentParser(description="Run Alert QA Generation")
    parser.add_argument("--qa_path", "-q", type=str, default="newqa.json", help="Path to save the generated QA")
    parser.add_argument("--graph_path", "-g", type=str, default="sample_incident.graphml", help="Path to the alert graph")
    parser.add_argument("--cache_seed", type=int, default=42, help="Seed for the cache")
    parser.add_argument("--include_entry", action="store_true", help="Include full alert entry in the question prompt")
    parser.add_argument("--model", "-m", type=str, default="o1-ga", help="Model to use for QA generation")
    parser.add_argument("--solution_model", "-s", type=str, default="o1-ga", help="Model to use for solution generation")
    parser.add_argument("--include_incident", action="store_false", help="Include incident context in the question prompt")
    parser.add_argument("--split", type=str, default="train", help="Split to generate QA for")
    parser.add_argument("--relevant_type", type=str, default="low", help="Relevance type for the QA")
    parser.add_argument("--train_cap", type=int, default=100, help="Cap for the number of training questions")
    args = parser.parse_args()
    return args

args = get_args()
graph_files = [
     'incident_34.graphml',
     'incident_166.graphml',
    'incident_55.graphml',
     'incident_5.graphml',
     'incident_38.graphml',
     'incident_134.graphml',
     'incident_39.graphml',
    'incident_322.graphml'
 ]

# Changes: You can pass in one config list with different models
# BE SURE TO include a "tags": [<model_name>] for each dictionary in the config_list to include the model name
# We will filter out the config list passed in to only include the model that model_name in the tags is equal to qa_gen_model
# config_list = [
#     {
#         "model": "some name",
#         "tags": ["gpt-4o"]
#     },
#     {
#         "model": "some name",
#         "tags": ["gpt-3.5"]
#     }
# ]
# If qa_gen_model = "gpt-4o", the config_list for qa_gen will be only the first dictionary in the config_list


# form question file name
qa_file_suffix = "qa"
if args.include_entry:
    qa_file_suffix += "_entry"
if args.include_incident:
    qa_file_suffix += "_incident"
qa_file_suffix += f"_{args.model}"
if args.solution_model is not None and args.solution_model != args.model:
    qa_file_suffix += f"_{args.solution_model}"
qa_file_suffix += f"_c{args.cache_seed}.json"

set_split = args.split
relevance_type = args.relevant_type
train_cap = args.train_cap
original_qa_path = "../env/questions/legacy/old_high_score/test"

if relevance_type == "low":
    saved_paths_path = "./low_split"
    new_qa_path = f"../env/questions/min_overlap/{set_split}"
elif relevance_type == "high":
    saved_paths_path = "./high_split"
    new_qa_path = f"../env/questions/max_overlap/{set_split}"
elif relevance_type == "median":
    saved_paths_path = "./median_split"
    new_qa_path = f"../env/questions/median_overlap/{set_split}"
else:
    raise ValueError("Invalid relevance type")

os.makedirs(new_qa_path, exist_ok=True)


t = 0
print(f"Generating QA for the {set_split} set with relevance type {relevance_type}")
for file in graph_files:
    skip_count = 0
    qagenena = QAGen(
        config_list=CONFIG_LIST, 
        graph_path=os.path.join("graph_files", file),
        cache_seed=41
    )

    # 1. load the original question file if it exists
    qas = []
    existing_qa_map = {}
    origin_qa_file = f"{original_qa_path}/{file.split('.')[0]}_{qa_file_suffix}"
    if os.path.exists(origin_qa_file):
        with open(origin_qa_file, "r") as f:
            qas = json.load(f)    
    for qa in qas:
        existing_qa_map[(qa["start_alert"], qa["end_alert"])] = qa

    # 1.2 resume from new qa file if it exists
    current_qa_path = f"{new_qa_path}/{file.split('.')[0]}_{qa_file_suffix}"
    if os.path.exists(current_qa_path):
        with open(current_qa_path, "r") as f:
            new_qas = json.load(f)
            for qa in new_qas:
                existing_qa_map[(qa["start_alert"], qa["end_alert"])] = qa

    # 2. open graph paths file json
    with open(os.path.join(saved_paths_path, file.split('.')[0] + ".json"), "r") as f:
        question_paths = json.load(f)
    path_from_split = question_paths[set_split]
    if set_split == 'train' and train_cap > 0:
        path_from_split = random.sample(path_from_split, min(train_cap, len(path_from_split)))
    print(f"Generating QA for {file}... for {len(path_from_split)} questions")

    all_questions = []
    for path_dict in path_from_split:
        start_alert = path_dict["start_alert"]
        end_alert = path_dict["end_alert"]
        if (start_alert, end_alert) in existing_qa_map:
            all_questions.append(existing_qa_map[(start_alert, end_alert)])
            print(f"Reusing question for {start_alert} -> {end_alert}")
        else:
            print(f"Generating question for {start_alert} -> {end_alert}")
            question = qagenena.generate_one_question(path_dict)
            all_questions.append(question)
        # save the questions
        # Note this is a new path
        with open(current_qa_path, "w") as f:
            json.dump(all_questions, f, indent=4)
    t+=len(path_from_split)

print(f"Total {set_split} questions: {t}")
