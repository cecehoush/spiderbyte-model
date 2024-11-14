import json
import os
import time
import requests
import google.generativeai as genai
import llm_manager
import re
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

# Configure the generative AI model
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Initialize the server API URL
url = os.getenv("SERVER_API_URL")

def fetch_challenges():
    response = requests.get("http://localhost:5000/api/challenges")
    if response.status_code == 200:
        return response.json()
    else:
        print("Failed to fetch challenges.")
        return []

def find_matching_challenges(user_tags, challenges):
    matching_challenge_names = []
    for challenge in challenges:
        challenge_tags = challenge.get("content_tags", [])
        if any(tag in user_tags for tag in challenge_tags):
            matching_challenge_names.append(challenge["challenge_title"])
    return matching_challenge_names

def generate_prompt(subject_tags, content_tags, difficulty, matching_challenge_names, challenge_titles):
    prompt = f"""
    ---
    **Prompt:**

    Generate a coding challenge based on the following topics: {', '.join(content_tags)}. It needs to be a part of these Subject: {subject_tags}. 
    It should be a difficulty {difficulty} out of 10.
    Provide the output in the following format: 
    Add a short concise story no longer than 4 sentences to help explain the challenge to the reader. Assign a relative difficulty from 1-10 DO NOT EXCEED 10 DO NOT GO BELOW 1. Provide a list of hints to help guide the reader to the solution. Include a skeleton code snippet in PYTHON ONLY. Finally, provide a list of test cases to validate the solution.
    {{
      "challenge_title": "Caesar Cipher Encryption",
      "challenge_description": {{
        "description": "Implement a function to encrypt a given text using the Caesar cipher algorithm.",
        "input_format": "A string `text` representing the plaintext to be encrypted. An integer `shift` indicating the number of positions to shift the letters.",
        "output_format": "A string representing the encrypted ciphertext.",
        "constraints": "The shift value will be in the range 0 to 25."
      }},
      "challenge_difficulty": 1,
      "language_supported": ["python"],
      "content_tags": ["data structures", "algorithms", "arrays"],
      "skeleton_code": {{
        "language": "python",
        "code": "def caesar_cipher(text, shift):\\n  # Your code here\\n  return"
      }},
      "hints": [
        "Hint 1: Remember that if the shift takes the letter beyond 'z', you should wrap around to 'a'.",
        "Hint 2: You may want to use the modulo operator to manage the wrapping of the characters."
      ],
      "test_cases": [
        {{
          "inputs": ["hello", 3],
          "expected_output": "khoor"
        }},
        {{
          "inputs": ["abc", 1],
          "expected_output": "bcd"
        }},
        {{
          "inputs": ["xyz", 2],
          "expected_output": "zab"
        }}
      ]
    }}

    Ensure the output follows this structure exactly, providing an appropriate coding challenge, a skeleton code, and test cases based on the provided topic. Avoid unnecessary explanations and stick to this format strictly.

    DO NOT GENERATE ANY OPEN STRINGS. ALWAYS MAKE SURE THE OPEN STRING IS CLOSED. ALWAYS MAKE SURE THE OPEN QUOATION MARK IS CLOSED.
    DO NOT GENERATE THE SAME CHALLENGE TWICE. IF YOU NEED TO REGENERATE, CHANGE THE TOPICS OR THE CHALLENGE TITLE.
    DO NOT GENEREATE ANY CHALLENGES THAT ARE SIMILAR TO THE NAMES OF THESE CODING CHALLENGES:
    {','.join(matching_challenge_names + challenge_titles)}
    """
    return prompt

def generate_challenge(prompt):
    model = genai.GenerativeModel("gemini-1.5-pro")
    result = model.generate_content(prompt)
    return result.text

def parse_generated_challenge(result_text):
    lines = result_text.splitlines()
    trimmed_text = "\n".join(lines[1:-1])
    try:
        parsed_result = json.loads(trimmed_text)
        print('Passed parsed result')
        return parsed_result
    except json.JSONDecodeError as e:
        print(f"JSON decoding failed: {e}")
        print(f"Trimmed response text causing issue:\n{trimmed_text}")
        return None

def compute_similarity(challenge_title, challenge_description, challenges):
    return llm_manager.compute_similarity(challenge_title, challenge_description, challenges)

def validate_and_post_challenge(parsed_result, similarity_score, url):
    if not similarity_score:
        print("No challenges to compare to.")
    elif isinstance(similarity_score, list) and all(isinstance(i, list) for i in similarity_score):
        if similarity_score[0][1] > 0.65:
            print("Challenge is similar to existing challenges.")
            return -1
        else:
            print("Challenge is not similar to existing challenges.")
            postResponse = requests.post(url + "/challenges", json=parsed_result)
            print(f"Post Response Status Code: {postResponse.status_code}")
    else:
        print("Invalid similarity score format.")

def generate_solution(challenge_title, challenge_description):
    newPrompt = f"""
    ---
    ---
    **Prompt:**

    Design an efficient algorithm to {challenge_title}. With this description: {challenge_description} The algorithm should:
    - [Specify input and output formats]
    - [Define performance constraints, if any]

    The solution should be concise and well-structured, adhering to these guidelines:
    - Use fundamental programming concepts.
    - Avoid unnecessary complexity and redundancy.
    - Optimize for time and space efficiency.

    Return the solution as a Python function.

    Return the solution in this format:
    def function_name(parameters):
        # Your code here
        return
    """
    model = genai.GenerativeModel("gemini-1.5-pro")
    time.sleep(5)
    aisolution = model.generate_content(newPrompt)
    return aisolution.text

def validate_solution(aisolution, parsed_result, challenge_title):
    lines = aisolution.splitlines()
    if len(lines) > 2:
        trimmed_ai_response = "\n".join(lines[1:-1])
    else:
        trimmed_ai_response = aisolution

    match = re.search(r'def\s+(\w+)\s*\(([^)]*)\)', trimmed_ai_response)
    if not match:
        print("No valid function found in user code.")
        return None
    else:
        function_name = match.group(1)
        function_params = match.group(2)
        param_count = len([param for param in function_params.split(",") if param.strip()])
        input_params = ", ".join([f"input{i + 1}" for i in range(param_count)])
        code_with_function_call = f"{trimmed_ai_response}\n\nresult = {function_name}({input_params})"

        try:
            postResponse = requests.post(
                url + "/submissions",
                json={
                    "userid": -1,
                    "challenge_name": challenge_title,
                    "usercode": code_with_function_call,
                    "test_cases": parsed_result.get("test_cases", []),
                    "code": aisolution,
                    "language": 'Python'
                },
                timeout=10
            )
            postResponse.raise_for_status()
            print(f"Post Response Status Code: {postResponse.status_code}")
            print(f"Post Response Content: {postResponse.content}")
        except requests.exceptions.Timeout:
            print("Request timed out.")
        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")

def check_submission_status(challenge_title):
    try:
        status_response = requests.get(f"{url}/submissions", params={"challenge_title": challenge_title}, timeout=10)
        print(f"Fetched submission response: {status_response.status_code}")
        print(f"Response content: {status_response.content}")

        if status_response.status_code == 200:
            status_data = status_response.json()
            for submission in status_data:
                if submission.get("valid_solution"):
                    print("Valid solution found.")
                    return True
            print("No valid solution found.")
        else:
            print(f"Unexpected status code: {status_response.status_code}")
    except requests.exceptions.Timeout:
        print("Request timed out while fetching submission status.")
    except requests.exceptions.RequestException as e:
        print(f"Error during status check: {e}")
    return False

def main():
    user_id = "user_id"
    content_tags = []
    subject_tags = ["Data Structures"]
    difficulty = 1
    challenges = fetch_challenges()
    matching_challenge_names = find_matching_challenges(content_tags, challenges)
    print("matching challenge names:", matching_challenge_names)

    challenge_titles = [challenge["challenge_title"] for challenge in challenges]
    additional_challenges = [
        "Implement a Stack", "Implement a Queue", "Implement a Binary Search Tree",
        "Implement a Hash Table", "Implement a Trie", "Implement a Graph",
        "Implement a Linked List", "Implement a Doubly Linked List",
        "Implement a Circular Linked List", "Implement a Priority Queue",
        "Implement a Heap", "Implement a Binary Search", "Implement a Breadth-First Search",
        "Implement a Depth-First Search", "Implement Dijkstra's Algorithm",
        "Implement Bellman-Ford Algorithm", "Implement Floyd-Warshall Algorithm",
        "Implement Prim's Algorithm", "Implement Kruskal's Algorithm",
        "Implement Topological Sort", "Implement a Segment Tree",
        "Implement a Fenwick Tree", "Implement an AVL Tree",
        "Implement a Red-Black Tree", "Implement a B-Tree", "Implement a B+ Tree",
        "Implement a Skip List", "Implement a Bloom Filter",
        "Implement an LRU Cache", "Implement an LFU Cache",
        "Implement a MinHeap", "Implement a MaxHeap", "Implement a MinStack",
        "Implement a MaxStack", "Implement a MinQueue", "Implement a MaxQueue",
        "Implement a MinPriorityQueue", "Implement a MaxPriorityQueue"
    ]
    challenge_titles.extend(additional_challenges)
    challenge_titles = list(set(challenge_titles))

    prompt = generate_prompt(subject_tags, content_tags, difficulty, matching_challenge_names, challenge_titles)
    result_text = generate_challenge(prompt)
    parsed_result = parse_generated_challenge(result_text)

    if parsed_result:
        challenge_title = parsed_result["challenge_title"]
        challenge_description = parsed_result["challenge_description"]["description"]
        similarity_score = compute_similarity(challenge_title, challenge_description, challenges)
        if validate_and_post_challenge(parsed_result, similarity_score, url) == -1:
            return

        aisolution = generate_solution(challenge_title, challenge_description)
        validate_solution(aisolution, parsed_result, challenge_title)

        time.sleep(2)
        if check_submission_status(challenge_title):
            subjects = subject_tags
            jsonPut = {
                "subjects": subjects,
                "challenge_title": challenge_title
            }
            print(f"JSON {jsonPut}")
            postResponse = requests.post("http://localhost:5000/api/challenges", json=parsed_result, timeout=10)
            print(f"Challenge posted successfully with valid solution {postResponse}")

            assign_response = requests.put("http://localhost:5000/api/subjects/assignQuestionToSubjects", json=jsonPut, timeout=10)
            print(f"Assign Response Status Code: {assign_response.status_code}")
            print(f"Assign Response Content: {assign_response.content}")
          


if __name__ == "__main__":
    main()
