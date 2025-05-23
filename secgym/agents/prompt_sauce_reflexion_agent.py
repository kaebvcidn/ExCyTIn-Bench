from autogen import OpenAIWrapper
from secgym.agents.agent_utils import sql_parser, msging, call_llm
# from tenacity import retry, wait_fixed
import random

BASE_PROMPT = """You are a security analyst working on investigating a security incident. 
You need to answer a given question about the security incident by querying the database of security logs provided to you.
The logs are stored in a MySQL database, you can use SQL queries to retrieve entries as needed.
Note there are more than 20 tables in the database, so you may need to explore the schema or check example entries to understand the database structure.

A security incident is composed of a group of related alerts connected by data elements or entities that are shared between the alerts such as User accounts, Hosts, Mailboxes, IP addresses, Files, Cloud applications, Processes, URLs etc. Alerts are signals that result from various threat detection activities. These signals indicate the occurrence of malicious or suspicious events in your environment. Besides the security alert signals, you can also find additional information in the raw logs like device events, user activities, network traffic, etc. 

The best way to approach the question is to start from the alert(s) that are part of the security incident and then explore the related logs to understand the context of the incident. If the security incident table is available to you, first thing to do should be to find all the information about the given incident from the security incident table. 

Other important tables to look at are the alert tables, which contains alerts and other additional information that was generated by the security monitoring tools. Once you find the alerts that are part of the security incident, you can explore the entities that are shared between the alerts to understand the context of the incident. These entities can be further used to find additional information from the logs and even alerts that you might have missed.

Your response should always be a thought-action pair:
Thought: <your reasoning>
Action: <your SQL query>

In Thought, you can analyse and reason about the current situation, 
Action can be one of the following: 
(1) execute[<your query>], which executes the SQL query
(2) submit[<your answer>], which is the final answer to the question
"""


O1_PROMPT = """You are a security analyst working on investigating a security incident. 
You need to answer a given question about the security incident by querying the database of security logs provided to you.
The logs are stored in a MySQL database, you can use SQL queries to retrieve entries as needed.
Note there are more than 20 tables in the database, so you may need to explore the schema or check example entries to understand the database structure.

A security incident is composed of a group of related alerts connected by data elements or entities that are shared between the alerts such as User accounts, Hosts, Mailboxes, IP addresses, Files, Cloud applications, Processes, URLs etc. Alerts are signals that result from various threat detection activities. These signals indicate the occurrence of malicious or suspicious events in your environment. Besides the security alert signals, you can also find additional information in the raw logs like device events, user activities, network traffic, etc. 

The best way to approach the question is to start from the alert(s) that are part of the security incident and then explore the related logs to understand the context of the incident. If the security incident table is available to you, first thing to do should be to find all the information about the given incident from the security incident table. 

Other important tables to look at are the alert tables, which contains alerts and other additional information that was generated by the security monitoring tools. Once you find the alerts that are part of the security incident, you can explore the entities that are shared between the alerts to understand the context of the incident. These entities can be further used to find additional information from the logs and even alerts that you might have missed.

Your response should always be a thought-action pair:
Thought: <your reasoning>
Action: <your SQL query>

In Thought, you can analyse and reason about the current situation, 
Action can be one of the following: 
(1) execute[<your sql query>], which executes the SQL query. For example, execute[DESCRIBE table_name].
(2) submit[<your answer>], which is the final answer to the question

You should only give one thought-action per response. The action from your response will be executed and the result will be shown to you.
Follow the format "Thought: ....\nAction: ...." exactly.
"""

class PromptSauceReflexionAgent:
    def __init__(self,
                 config_list,
                 cache_seed=41,
                 max_steps=15,
                 temperature=0,
                 retry_num=10,
                 retry_wait_time=5,
                 ):
        self.config_list = config_list
        self.temperature = temperature
        self.cache_seed = cache_seed
        self.client = OpenAIWrapper(config_list=config_list, cache_seed=cache_seed)
        sys_prompt = BASE_PROMPT
        if "o1" in config_list[0]['model'] or "o3" in config_list[0]['model']:
            sys_prompt = O1_PROMPT
        self.messages = [{"role": "system", "content": sys_prompt}]

        self.max_steps = max_steps
        self.step_count = 0
        self.incident = None
        self.replay_buffer = []
        self.retry_num = retry_num
        self.retry_wait_time = retry_wait_time

    @property
    def name(self):
        return "PromptSauceReflexionAgent"

    def _call_llm(self, messages):
        response = call_llm(
            client=self.client, 
            model=self.config_list[0]['model'],
            messages=messages,
            retry_num=self.retry_num,
            retry_wait_time=self.retry_wait_time,
            temperature=self.temperature
        )
        return response.choices[0].message.content
    
    def reflect(self):
        #first sample from replay buffer, sampling strategy is key for getting useful reflections

        #if no replays return
        if len(self.replay_buffer) == 0:
            print("No replays to reflect on")
            return

        #1. Random 5 samples
        previous_trials_count = 3#random.randint(1, 3)
        if len(self.replay_buffer) <= previous_trials_count:
            replays = self.replay_buffer
        else:
            replays = random.sample(self.replay_buffer, previous_trials_count)
        
        #2. Sample based on question type
        #replays = self.replay_buffer.sample(10, key=lambda x: x["question"] == )
        
        #extract reflective text from replays
        #TODO: Add examples of reflective prompts Here are some examples:
        #{examples}
        #(END OF EXAMPLES)
        REFLECT_PROMPT = f"""You are an advanced reasoning agent that can improve based on self refection. You will be given a previous reasoning trial in which you were given a question to answer. You were unsuccessful in answering the question either because you guessed the wrong answer with submit[<answer>] or there is a phrasing discrepancy with your provided answer and the answer key. In a few sentences, Diagnose a possible reason for failure or phrasing discrepancy and devise a new, concise, high level plan that aims to mitigate the same failure. Use complete sentences.
        Previous trials:
        {[f"Trial {i}, Reward: {replay['reward']}, Transcript: {replay['messages']}" for i,replay in enumerate(replays)]}
        Reflection:
        """
        #print(REFLECT_PROMPT)
        # try:
        #     reflection = self._call_llm(messages=[msging(REFLECT_PROMPT)])
        # except Exception as e:
        #     if "context_length_exceeded" in str(e):
        #         max_length = 127000  # adjust based on your model's token limit
        #         truncated_prompt = REFLECT_PROMPT[:max_length]
        #         reflection = self._call_llm(messages=[msging(truncated_prompt)])
        #     else:
        #         raise e
        
        reflection = self._call_llm(messages=[msging(REFLECT_PROMPT[:120000])])
        return reflection

    def act(self, observation: str):
        self._add_message(observation, role="user")
        response = self._call_llm(messages=self.messages)
        print(response)

        if self.step_count >= self.max_steps-1 and self.submit_summary:
            summary_prompt = "You have reached maximum number of steps. Please summarize your findings of key information, and sumbit them."
            self._add_message(summary_prompt, role="system")

        split_str = "\nAction:"
        if "**Action:**" in response:
            split_str = "\n**Action:**"
        try:
            thought, action = response.strip().split(split_str)
            self._add_message(response.strip(), role="assistant")
        except:
            print("\nRetry Split Action:")
            thought = response.strip()
            action = self._call_llm(self.messages + [msging(f"{thought}\nAction:")])
            print(action)
            action = action.strip()
            if not "Thought" in thought:
                thought = f"Thought: {thought}"
            self._add_message(f"{thought}\nAction:{action}", role="assistant")
        
        print("*"*50)

        self.step_count += 1
        # parse the action
        parsed_action, is_code, submit = sql_parser(action)
        
        # submit = True if "submit" in thought.lower() else False
        return parsed_action, submit
    
    def get_logging(self):
        return {
            "messages": self.messages,
            "usage_summary": self.client.total_usage_summary,
        }
    
    def _add_message(self, msg: str, role: str="user"):
        self.messages.append(msging(msg, role))

    def reset(self, change_seed=True):
        if change_seed:
            self.cache_seed += 1
        self.client = OpenAIWrapper(config_list=self.config_list, cache_seed=self.cache_seed)

        self.step_count = 0
        sys_prompt = BASE_PROMPT
        if "o1" in self.config_list[0]['model'] or "o3" in self.config_list[0]['model'] or "r1" in self.config_list[0]['model']:
            sys_prompt = O1_PROMPT
        self.messages = [{"role": "system", "content": sys_prompt}]
        
        #time to reflect on previous experiences
        reflection = self.reflect()

        #add reflection to messages
        if reflection:
            self._add_message(reflection, role="system")
        
        self.client.clear_usage_summary()


