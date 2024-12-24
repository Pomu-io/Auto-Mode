# ./backend/src/prompts.py

# Default prompt text for generate_code
default_generate_code_prompt = """You are an autonomous coding agent.

The user prompt: {user_prompt}
The test conditions: {test_conditions}

You must produce a Docker environment and code that meets the user's test conditions.

**Additional Requirements**:
- Start by creating a `readme.md` file as your first file in the files array. This `readme.md` should begin with `#./readme.md` and contain:
  - A brief summary of the user's prompt.
  - A brief step-by-step plan of what you intend to do to meet the test conditions.
- Use a stable base Docker image: `FROM python:3.10-slim`.
- Install any necessary dependencies in the Dockerfile.
- Generate any configuration files (like `pyproject.toml` or `requirements.txt`) before the main Python files, if needed.
- Each file must start with `#./<filename>` on the first line. For example:
  `#./main.py`
  `print('hello world')`
- The Dockerfile should define an ENTRYPOINT that runs the main script or commands automatically so that running the container (e.g. `docker run ...`) immediately produces the final output required by the test conditions.
- Ensure the output visible on stdout fulfills the test conditions without further intervention.

**Return JSON strictly matching this schema**:
{
  "dockerfile": "<string>",
  "files": [
    {
      "filename": "<string>",
      "content": "<string>"
    },
    ...
  ]
}

**Order of files**:
1. `readme.md` (with reasoning and plan)
2. Any configuration files (like `pyproject.toml` or `requirements.txt`)
3. Your main Python application files
"""

# Default prompt text for validate_output
default_validate_output_prompt = """The test conditions: {test_conditions}

dockerfile:
{dockerfile}

files:
{files_str}

output:
{output}

If all test conditions are met, return exactly:
{ "result": true, "dockerfile": null, "files": null }

Otherwise (if you need to fix or add files, modify the dockerfile, etc.), return exactly:
{
  "result": false,
  "dockerfile": "FROM python:3.10-slim\\n...",
  "files": [
    {
      "filename": "filename.ext",
      "content": "#./filename.ext\\n..."
    }
  ]
}

You may add, remove, or modify multiple files as needed when returning false. Just ensure you follow the same schema and format strictly. Do not add extra commentary or keys.
If returning null for dockerfile or files, use JSON null, not a string.
"""

# Current prompts in memory
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

def build_system_message(env_vars: dict) -> str:
    """
    Builds the system prompt that includes environment variable instructions
    if any environment variables have non-empty values.
    """
    # Check if we have at least one non-empty value
    non_empty_pairs = {k: v for k, v in env_vars.items() if v}
    if not non_empty_pairs:
        # No environment variables to handle
        return (
            "You are an autonomous coding agent. "
            "Generate Docker + code as JSON. No environment variables to incorporate."
        )
    
    # If we do have some variables, list them out
    instructions = "Additional environment variables provided:\n"
    for key, val in non_empty_pairs.items():
        # For security, you might choose to mask val or only show partial
        instructions += f"{key} = {val}\n"
    
    instructions += (
        "Please ensure the Dockerfile and generated code incorporate these variables. "
        "For example, you might:\n"
        " - COPY the .env file into the container\n"
        " - Use ENV or ARG instructions in Docker\n"
        " - And/or read them in your Python code via os.environ.\n"
        "If the user prompt or instructions require usage of these variables, do so accordingly."
    )
    
    return (
        "You are an autonomous coding agent. "
        "Generate Docker + code as JSON following the schema. "
        + instructions
    )
