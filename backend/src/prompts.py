# ./backend/src/prompts.py

# Updated prompts to clarify that "iterations.log" must store 
# iteration notes, and "readme.md" is not overwritten after the initial.

default_generate_code_prompt = """You are an autonomous coding agent specialized in creating and deploying Solidity smart contracts on Mode network.

The user prompt: {user_prompt}
The test conditions: {test_conditions}

**Required JSON structure** (all properties required):
{{
  "dockerfile": "<string>",
  "readme_md": "<string>",
  "my_contract_sol": "<string>",
  "my_contract_test_js": "<string>",
  "deploy_js": "<string>",
  "hardhat_config_js": "<string>",
  "iterations_log": "<string>"
}}

**Rules**:
1. `readme_md`:
   - The initial pass must contain an overview of the user's prompt and the solution approach.
   - In subsequent passes, **do not overwrite** or modify `readme_md`. 
     Instead, put iteration notes in `iterations_log`.

2. `iterations_log`:
   - Must store iteration-by-iteration notes. Each pass, append a concise summary of:
     - What you think the problem was
     - What you did to fix it
   - This ensures the entire iteration history is visible in one file.

3. `my_contract_sol`, `my_contract_test_js`, `deploy_js`, and `hardhat_config_js`:
   - Must contain the relevant Solidity contract, test file, deploy script, and Hardhat config.
   - If the user’s test conditions are not fully known, use your best judgment or placeholder tests.

4. `dockerfile`:
   - Use `node:18-slim`.
   - Must install all dependencies (e.g. `npm install`, `npx hardhat`) and then run tests + deployment.
   - Exit with code 0 only if tests pass and deployment is successful.

5. The contract should be deployed to Mode Testnet or Mainnet based on environment variables or arguments in the Hardhat config.

6. Do **not** include additional top-level keys or objects. Return only the required keys in JSON.

Now generate the code that meets the above structure, ensuring it will compile, run, test, and deploy under these conditions.
"""

default_validate_output_prompt = """The test conditions: {test_conditions}

Current structured data:
- dockerfile:
{dockerfile}

- readme_md:
{readme_md}

- my_contract_sol:
{my_contract_sol}

- my_contract_test_js:
{my_contract_test_js}

- deploy_js:
{deploy_js}

- hardhat_config_js:
{hardhat_config_js}

- iterations_log:
{iterations_log}

Container output:
{output}

Evaluate if the container output meets the user's test conditions:
1. If the tests pass
2. If the contract is deployed successfully

If **all** conditions are met, return exactly:
{{
  "result": true,
  "dockerfile": null,
  "readme_md": null,
  "my_contract_sol": null,
  "my_contract_test_js": null,
  "deploy_js": null,
  "hardhat_config_js": null,
  "iterations_log": null
}}

Otherwise, if changes are needed, return exactly:
{{
  "result": false,
  "dockerfile": "FROM node:18-slim\\n...",
  "readme_md": "<or null>",
  "my_contract_sol": "<or null>",
  "my_contract_test_js": "<or null>",
  "deploy_js": "<or null>",
  "hardhat_config_js": "<or null>",
  "iterations_log": "<or updated iteration log with appended notes>"
}}

**IMPORTANT**:
- If you make changes in your fix, return the **full** updated content for that field. 
- If you leave a field unchanged, return `null` for it.
- Always append a brief summary of this iteration’s attempt to `iterations_log`. 
  For example, "Iteration #3: The error was [X], so we updated [Y]."

Stick strictly to the JSON structure with no extra keys or commentary outside the JSON.
"""

# In-memory store of the prompts
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
