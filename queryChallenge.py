import os
import google.generativeai as genai

# Load environment variables from a .env file
from dotenv import load_dotenv
load_dotenv()

# Create a new instance of the GoogleGenerativeAI class
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Get the generative model
model = genai.GenerativeModel("gemini-1.5-pro")

# Define the prompt
prompt = """
---
**Prompt:**

Generate a coding challenge based on the following topics: [encryption, robotics, arrays]. Provide the output in the following format: 

{
  "challenge_title": "Caesar Cipher Encryption",
  "problem_description": {
    "description": "Implement a function to encrypt a given text using the Caesar cipher algorithm.",
    "input_format": "A string `text` representing the plaintext to be encrypted. An integer `shift` indicating the number of positions to shift the letters.",
    "output_format": "A string representing the encrypted ciphertext.",
    "constraints": "The shift value will be in the range 0 to 25."
  },
  "skeleton_code": {
    "language": "python",
    "code": "def caesar_cipher(text, shift):\n  # Your code here\n  return"
  },
  "hints": [
    "Hint 1: Remember that if the shift takes the letter beyond 'z', you should wrap around to 'a'.",
    "Hint 2: You may want to use the modulo operator to manage the wrapping of the characters."
  ],
  "test_cases": [
    {
      "input": {
        "text": "hello world",
        "shift": 3
      },
      "expected_output": "khoor zruog"
    },
    {
      "input": {
        "text": "abcxyz",
        "shift": 2
      },
      "expected_output": "cdezab"
    }
  ]
}

Ensure the output follows this structure exactly, providing an appropriate coding challenge, a skeleton code, and test cases based on the provided topic. Avoid unnecessary explanations and stick to this format strictly.
"""

# Generate content using the model
result = model.generate_content(prompt)

# Print the result
print(result.text)
