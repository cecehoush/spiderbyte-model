from sentence_transformers import SentenceTransformer, util
import json

# Define a preprocessing function
def preprocess(text):
    return text.lower().strip()

def compute_similarity(input_title, input_description, challenges):
    # Combine input title and description
    input_text = preprocess(input_title + " " + input_description)
    
    if(challenges == None):
        return -1

    # Combine titles and descriptions for all challenges
    texts = [preprocess(challenge["challenge_title"] + " " + " ".join(challenge["challenge_description"].values())) for challenge in challenges]
    
    # Load the pre-trained model
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    # Encode the input text and the challenges
    input_embedding = model.encode(input_text, convert_to_tensor=True)
    embeddings = model.encode(texts, convert_to_tensor=True)
    
    # Compute similarity scores between the input challenge and each of the others
    similarity_scores = []
    for idx in range(len(embeddings)):
        score = util.cos_sim(input_embedding, embeddings[idx]).item()
        similarity_scores.append((idx, score))
    
    # Sort the scores in descending order
    similarity_scores.sort(key=lambda x: x[1], reverse=True)
    
    # Print the similarity scores
    print("Similarity scores between the input challenge and each of the challenges in the JSON file:")
    for idx, score in similarity_scores:
        challenge_title = challenges[idx]["challenge_title"]
        print(f"Challenge {idx + 1}: {challenge_title} - Similarity Score: {score:.4f}")

'''
# Load the challenges from the JSON file
with open('challenges.json', 'r', encoding='utf-8') as f:
    challenges = json.load(f)

# Input challenge title and description
input_title = "Two Sum"
input_description = """Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.
            You may assume that each input would have exactly one solution, and you may not use the same element twice.
            The solution should be returned in any order, and the input array may contain both positive and negative integers.
            If no such pair exists, return an empty array. The time complexity should be considered when designing your solution."""
        

# Compute similarity
compute_similarity(input_title, input_description, challenges)
'''
