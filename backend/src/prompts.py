# ./backend/src/prompts.py

default_generate_code_prompt = """
You are an autonomous coding agent. The user wants some code generated.

The user prompt: {user_prompt}
The test conditions: {test_conditions}

**INSTRUCTIONS**:
1. Return a single JSON object with at least these fields:
   {
     "dockerfile": "<string>",
     "iterations_log": "<string>"
   }
2. You may optionally include other fields if you want (e.g. "readme_md", "my_contract_sol"), 
   but do not add any top-level keys unrelated to the code generation. 
3. The content must be valid JSON. 
4. No markdown code fences, no commentary outside the JSON.

Example minimal valid JSON:
{
  "dockerfile": "FROM node:18-slim\\n...",
  "iterations_log": "Initial pass: created Dockerfile"
}
"""

default_validate_output_prompt = """
The test conditions: {test_conditions}
The container output:
{output}

If the container output meets the test conditions, return exactly:
{
  "result": true
}

Otherwise, return exactly:
{
  "result": false,
  "dockerfile": "FROM node:18-slim\\n...",
  "iterations_log": "..."
}

Only return those keys if you need to fix something. 
Again, no extra commentary outside the JSON.
"""

# We just store in memory for now
current_generate_code_prompt = default_generate_code_prompt
current_validate_output_prompt = default_validate_output_prompt

def get_prompts():
    return {
        "generate_code_prompt": current_generate_code_prompt,
        "validate_output_prompt": current_validate_output_prompt
    }

def set_prompts(generate_code_prompt: str, validate_output_prompt: str):
    global current_generate_code_prompt, current_validate_output_prompt
    current_generate_code_prompt = generate_code_prompt
    current_validate_output_prompt = validate_output_prompt
