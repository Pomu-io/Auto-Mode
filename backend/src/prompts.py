# ./backend/src/prompts.py

MODE_CROSSMINT_DOCS = r"""
# We embed helpful docs for Mode network and Crossmint directly into the LLM's context.
# The agent can use these references to configure Hardhat and to incorporate Crossmint if requested.

=== MODE NETWORK DOCUMENTATION ===

You have two networks:

1) Mode Testnet
   - Network Name: "modeTestnet"
   - RPC Endpoint: https://sepolia.mode.network
   - Chain ID: 919
   - Explorer: https://sepolia.explorer.mode.network
   - Bridge: https://sepolia-bridge.mode.network

2) Mode Mainnet
   - Network Name: "modeMainnet"
   - RPC Endpoint: https://mainnet.mode.network/
   - Chain ID: 34443
   - Explorer: https://explorer.mode.network/
   - Bridge: https://bridge.mode.network/

Typical Hardhat config snippet for Mode Testnet might look like:
--------------------------------------------------------------------------------
networks: {
  modeTestnet: {
    url: "https://sepolia.mode.network",
    chainId: 919,
    accounts: [ process.env.WALLET_PRIVATE_KEY ]
  },
  modeMainnet: {
    url: "https://mainnet.mode.network",
    chainId: 34443,
    accounts: [ process.env.WALLET_PRIVATE_KEY ]
  }
}
--------------------------------------------------------------------------------

Remember to set these environment variables:
- WALLET_PRIVATE_KEY=0x<YourPrivateKeyHere>
- WALLET_ADDRESS=0x<YourWalletAddressHere>
- MODE_NETWORK=modeTestnet or modeMainnet (if you want to dynamically pick)

=== CROSSMINT DOCUMENTATION (Simplified) ===

Crossmint is often used for NFT minting or payment flows. 
You might incorporate Crossmint in your Hardhat scripts or within a Solidity contract, depending on the user's request.

Possible ways to integrate Crossmint:
1) If the user wants an NFT minted via Crossmint, you might use Crossmint's API. 
2) If the user wants an ERC-721 contract with special features, you could incorporate Crossmint whitelisting or calls.

Typical environment variables might include:
- CROSSMINT_API_KEY
- CROSSMINT_PROJECT_ID
- CROSSMINT_SECRET

(Each depends on the actual Crossmint docs/keys. This is just a placeholder.)

Example usage in a Node script for Crossmint (pseudo-code):
--------------------------------------------------------------------------------
const axios = require("axios");

async function crossmintMint() {
  const response = await axios.post("https://www.crossmint.io/api/2022-06-09/mintNFT", {
    // ... NFT data ...
  }, {
    headers: {
      "x-client-secret": process.env.CROSSMINT_API_KEY
    }
  });
  console.log(response.data);
}
--------------------------------------------------------------------------------

Depending on the user's request, you can incorporate Crossmint logic in scripts/deploy.js 
or a dedicated script like scripts/mint.js. 
If the user does NOT mention Crossmint, you can ignore it.
"""

###############################################################################
# Below we define the actual default prompts using f-string to embed the docs #
###############################################################################

default_generate_code_prompt = f"""{MODE_CROSSMINT_DOCS}

You are an autonomous coding agent specialized in creating and deploying Solidity smart contracts on Mode network.

The user prompt: {{user_prompt}}
The test conditions: {{test_conditions}}

**Environment Variables Available**:
- WALLET_PRIVATE_KEY
- WALLET_ADDRESS
- MODE_NETWORK
- CROSSMINT_API_KEY (optional)

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
  "package_lock_json": "<string>"
}}

**Rules**:
1. `readme_md`:  
   - The initial pass must contain an overview of the user's prompt and the solution approach.  
   - In subsequent passes, do **not** overwrite `readme_md`; instead append iteration notes to `iterations_log`.

2. `iterations_log`:  
   - Each pass (iteration) must append a concise summary of:
     - what the problem was
     - how you tried to fix it

3. `my_contract_sol`, `my_contract_test_js`, `deploy_js`, `hardhat_config_js`:
   - Must contain the relevant Solidity contract, test file, deploy script, and Hardhat config.
   - Reference Mode endpoints (testnet or mainnet) and use process.env.WALLET_PRIVATE_KEY for the account.
   - If user requests Crossmint, incorporate the CROSSMINT_API_KEY logic.

4. `package_json`:
   - Must define Node/Hardhat dependencies. If Crossmint usage is required, include any needed libraries for Crossmint.

5. `package_lock_json`:
   - May be empty or minimal.

6. `dockerfile`:
   - Must use `node:18-slim`.
   - Copy `package.json` / `package-lock.json`, run `npm install`, then copy other files.
   - The container must exit with code 0 only if tests pass and contract is successfully deployed to Mode.

Return **only** these 9 keys with valid JSON. Do not include extra keys at top-level.
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

Evaluate if the container output meets the user's test conditions (tests pass, contract deployed, Crossmint usage if relevant).

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

Otherwise, if changes are needed, return exactly:
{{
  "result": false,
  "dockerfile": "...",
  "readme_md": "<or null>",
  "my_contract_sol": "<or null>",
  "my_contract_test_js": "<or null>",
  "deploy_js": "<or null>",
  "hardhat_config_js": "<or null>",
  "iterations_log": "<or updated iteration log>",
  "package_json": "<or null>",
  "package_lock_json": "<or null>"
}}

- If you change a file, provide the **full** updated content. 
- If a file is not changed, set it to `null`.
- Always append a short summary of your fix attempt to `iterations_log`.
"""

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
