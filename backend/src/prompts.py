# ./backend/src/prompts.py

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
  "iterations_log": "<string>",
  "package_json": "<string>",
  "package_lock_json": "<string>"  # this can be empty or null if desired
}}

**Rules**:
1. `readme_md`: 
   - Provide an overview of the user's prompt and solution approach on the first iteration.
   - Do not overwrite after the first iteration. Instead, append iteration changes to `iterations_log`.

2. `iterations_log`:
   - Must store iteration-by-iteration notes about what was tried or fixed. Each pass, append a concise summary.

3. `my_contract_sol`, `my_contract_test_js`, `deploy_js`, `hardhat_config_js`:
   - Standard Hardhat code: a contract, test file, deploy script, config.

4. `package_json`:
   - Must define the needed dependencies (e.g. "hardhat", "@nomicfoundation/hardhat-toolbox", "openzeppelin", etc.).
   - Optionally specify scripts for `test` or `deploy`.

5. `package_lock_json`:
   - Could be empty, `null`, or an actual lock file. If non-empty, the Dockerfile should copy it.

6. `dockerfile`:
   - Must use `node:18-slim`.
   - Must `COPY package.json` (and `package-lock.json` if present) into the container, then `RUN npm install`, then copy everything else, then compile/test/deploy.
   - The container should exit with code 0 only if tests pass and the contract is deployed (if required).

7. Return only the specified top-level JSON keys with exact names—no extras.

Now generate the code meeting these requirements.
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

- package_json:
{package_json}

- package_lock_json:
{package_lock_json}

Container output:
{output}

Evaluate if the container output meets the user's test conditions:
1) Tests pass
2) Contract is deployed successfully (if required by user)
3) Any other conditions specified

If **all** conditions are met, return exactly:
{{
  "result": true,
  "dockerfile": null,
  "readme_md": null,
  "my_contract_sol": null,
  "my_contract_test_js": null,
  "deploy_js": null,
  "hardhat_config_js": null,
  "iterations_log": null,
  "package_json": null,
  "package_lock_json": null
}}

Otherwise, if you need changes, return exactly:
{{
  "result": false,
  "dockerfile": "FROM node:18-slim\\n...",
  "readme_md": "<string or null>",
  "my_contract_sol": "<string or null>",
  "my_contract_test_js": "<string or null>",
  "deploy_js": "<string or null>",
  "hardhat_config_js": "<string or null>",
  "iterations_log": "<string>",
  "package_json": "<string or null>",
  "package_lock_json": "<string or null>"
}}

Rules:
- If a field is unchanged, set it to `null`.
- If changed, return the **full** updated content.
- Always append a short iteration summary to `iterations_log`.

Stick strictly to the JSON structure—no extra commentary outside it.
"""

# We store them in memory for simplicity:
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
