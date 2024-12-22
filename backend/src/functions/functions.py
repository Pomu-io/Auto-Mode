# Copyright (C) 2024 Harrison E. Muchnic
# This program is licensed under the Affero General Public License (AGPL).
# See the LICENSE file for details.

# ./backend/src/functions/functions.py

from restack_ai.function import function, log
from dataclasses import dataclass
import os
import openai
import json
import tempfile
import subprocess

from pydantic import BaseModel
from typing import Optional

from src.prompts import current_generate_code_prompt, current_validate_output_prompt

openai.api_key = os.environ.get("OPENAI_KEY")
from openai import OpenAI
client = OpenAI(api_key=openai.api_key)

#
# 1) GENERATE CODE SCHEMA
#
class GenerateCodeSchema(BaseModel):
    """
    Now only "dockerfile" is truly required for parsing;
    all other fields are optional.
    """
    dockerfile: str
    readme_md: Optional[str] = None
    my_contract_sol: Optional[str] = None
    my_contract_test_js: Optional[str] = None
    deploy_js: Optional[str] = None
    hardhat_config_js: Optional[str] = None
    iterations_log: Optional[str] = None
    package_json: Optional[str] = None
    package_lock_json: Optional[str] = None

    class Config:
        extra = "forbid"
        schema_extra = {
            "type": "object",
            "properties": {
                "dockerfile": {"type": "string"},
                "readme_md": {"type": "string"},
                "my_contract_sol": {"type": "string"},
                "my_contract_test_js": {"type": "string"},
                "deploy_js": {"type": "string"},
                "hardhat_config_js": {"type": "string"},
                "iterations_log": {"type": "string"},
                "package_json": {"type": "string"},
                "package_lock_json": {"type": "string"}
            },
            "required": ["dockerfile"],  # Only 'dockerfile' is required
            "additionalProperties": False
        }

#
# 2) VALIDATE OUTPUT SCHEMA
#
class ValidateOutputSchema(BaseModel):
    """
    'result' and 'dockerfile' remain required.
    All others can be omitted or null.
    """
    result: bool
    dockerfile: Optional[str] = None
    readme_md: Optional[str] = None
    my_contract_sol: Optional[str] = None
    my_contract_test_js: Optional[str] = None
    deploy_js: Optional[str] = None
    hardhat_config_js: Optional[str] = None
    iterations_log: Optional[str] = None
    package_json: Optional[str] = None
    package_lock_json: Optional[str] = None

    class Config:
        extra = "forbid"
        schema_extra = {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
                "dockerfile": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "readme_md": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "my_contract_sol": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "my_contract_test_js": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "deploy_js": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "hardhat_config_js": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "iterations_log": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "package_json": {"anyOf":[{"type":"string"},{"type":"null"}]},
                "package_lock_json": {"anyOf":[{"type":"string"},{"type":"null"}]}
            },
            "required": [
                "result",
                "dockerfile"  # We keep these 2 required in validation
            ],
            "additionalProperties": False
        }

@dataclass
class GenerateCodeInput:
    user_prompt: str
    test_conditions: str

@dataclass
class GenerateCodeOutput:
    """
    We store the final strings, or empty if missing.
    """
    dockerfile: str
    readme_md: str
    my_contract_sol: str
    my_contract_test_js: str
    deploy_js: str
    hardhat_config_js: str
    iterations_log: str
    package_json: str
    package_lock_json: str

@function.defn()
async def generate_code(input: GenerateCodeInput) -> GenerateCodeOutput:
    log.info("generate_code started", input=input)

    prompt = current_generate_code_prompt.format(
        user_prompt=input.user_prompt,
        test_conditions=input.test_conditions
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are the initial of an autonomous coding assistant agent. "
                    "Generate code according to the user's instructions. "
                    "Return valid JSON only."
                )
            },
            {"role": "user", "content": prompt}
        ],
        response_format=GenerateCodeSchema
    )

    result = completion.choices[0].message
    if result.refusal:
        raise RuntimeError("Model refused to generate code.")

    data = result.parsed

    # For any field that is None, store an empty string.
    return GenerateCodeOutput(
        dockerfile=data.dockerfile,
        readme_md=data.readme_md or "",
        my_contract_sol=data.my_contract_sol or "",
        my_contract_test_js=data.my_contract_test_js or "",
        deploy_js=data.deploy_js or "",
        hardhat_config_js=data.hardhat_config_js or "",
        iterations_log=data.iterations_log or "",
        package_json=data.package_json or "",
        package_lock_json=data.package_lock_json or ""
    )

#
#  RUN LOCALLY
#
@dataclass
class RunCodeInput:
    dockerfile: str
    readme_md: str
    my_contract_sol: str
    my_contract_test_js: str
    deploy_js: str
    hardhat_config_js: str
    iterations_log: str
    package_json: str
    package_lock_json: str

@dataclass
class RunCodeOutput:
    output: str

@function.defn()
async def run_locally(input: RunCodeInput) -> RunCodeOutput:
    log.info("run_locally started", input=input)
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1) Dockerfile is guaranteed non-empty
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as df:
            df.write(input.dockerfile)

        # 2) readme.md (could be empty)
        with open(os.path.join(temp_dir, "readme.md"), "w", encoding="utf-8") as f:
            f.write(input.readme_md)

        # 3) contracts/MyContract.sol (could be empty)
        contracts_dir = os.path.join(temp_dir, "contracts")
        os.makedirs(contracts_dir, exist_ok=True)
        with open(os.path.join(contracts_dir, "MyContract.sol"), "w", encoding="utf-8") as f:
            f.write(input.my_contract_sol)

        # 4) test/my_contract_test.js (could be empty)
        test_dir = os.path.join(temp_dir, "test")
        os.makedirs(test_dir, exist_ok=True)
        with open(os.path.join(test_dir, "my_contract_test.js"), "w", encoding="utf-8") as f:
            f.write(input.my_contract_test_js)

        # 5) scripts/deploy.js (could be empty)
        scripts_dir = os.path.join(temp_dir, "scripts")
        os.makedirs(scripts_dir, exist_ok=True)
        with open(os.path.join(scripts_dir, "deploy.js"), "w", encoding="utf-8") as f:
            f.write(input.deploy_js)

        # 6) hardhat.config.js (could be empty)
        with open(os.path.join(temp_dir, "hardhat.config.js"), "w", encoding="utf-8") as f:
            f.write(input.hardhat_config_js)

        # 7) iterations.log (could be empty)
        with open(os.path.join(temp_dir, "iterations.log"), "w", encoding="utf-8") as f:
            f.write(input.iterations_log)

        # 8) package.json (could be empty)
        with open(os.path.join(temp_dir, "package.json"), "w", encoding="utf-8") as f:
            f.write(input.package_json)

        # 9) package-lock.json (could be empty)
        with open(os.path.join(temp_dir, "package-lock.json"), "w", encoding="utf-8") as f:
            f.write(input.package_lock_json)

        # Build the Docker image
        build_cmd = ["docker", "build", "-t", "myapp", temp_dir]
        build_process = subprocess.run(build_cmd, capture_output=True, text=True)
        if build_process.returncode != 0:
            return RunCodeOutput(output=build_process.stderr or build_process.stdout)
        
        # Pass environment variables to the container if needed
        env_vars = {
            "WALLET_PRIVATE_KEY": os.environ.get("WALLET_PRIVATE_KEY", ""),
            "WALLET_ADDRESS": os.environ.get("WALLET_ADDRESS", ""),
            "MODE_NETWORK": os.environ.get("MODE_NETWORK", ""),
            "CROSSMINT_API_KEY": os.environ.get("CROSSMINT_API_KEY", "")
        }
        
        env_args = []
        for key, val in env_vars.items():
            if val:
                env_args.extend(["-e", f"{key}={val}"])
        
        # Run the Docker container
        run_cmd = ["docker", "run", "--rm"] + env_args + ["myapp"]
        run_process = subprocess.run(run_cmd, capture_output=True, text=True)
        if run_process.returncode != 0:
            return RunCodeOutput(output=run_process.stderr or run_process.stdout)
        
        return RunCodeOutput(output=run_process.stdout)

#
# VALIDATE OUTPUT
#
@dataclass
class ValidateOutputInput:
    dockerfile: str
    readme_md: str
    my_contract_sol: str
    my_contract_test_js: str
    deploy_js: str
    hardhat_config_js: str
    iterations_log: str
    package_json: str
    package_lock_json: str
    output: str
    test_conditions: str

@dataclass
class ValidateOutputOutput:
    result: bool
    dockerfile: Optional[str] = None
    readme_md: Optional[str] = None
    my_contract_sol: Optional[str] = None
    my_contract_test_js: Optional[str] = None
    deploy_js: Optional[str] = None
    hardhat_config_js: Optional[str] = None
    iterations_log: Optional[str] = None
    package_json: Optional[str] = None
    package_lock_json: Optional[str] = None

@function.defn()
async def validate_output(input: ValidateOutputInput) -> ValidateOutputOutput:
    log.info("validate_output started", input=input)

    validation_prompt = current_validate_output_prompt.format(
        test_conditions=input.test_conditions,
        dockerfile=input.dockerfile,
        readme_md=input.readme_md,
        my_contract_sol=input.my_contract_sol,
        my_contract_test_js=input.my_contract_test_js,
        deploy_js=input.deploy_js,
        hardhat_config_js=input.hardhat_config_js,
        iterations_log=input.iterations_log,
        package_json=input.package_json,
        package_lock_json=input.package_lock_json,
        output=input.output
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an iteration of an autonomous coding assistant agent. "
                    "If you change any fields, provide the complete updated content. "
                    "Always append a brief summary of your fix attempt to iterations_log."
                )
            },
            {"role": "user", "content": validation_prompt}
        ],
        response_format=ValidateOutputSchema
    )

    result = completion.choices[0].message
    if result.refusal:
        # If the model refused or didn't provide a result
        return ValidateOutputOutput(result=False)

    parsed = result.parsed
    
    return ValidateOutputOutput(
        result=parsed.result,
        dockerfile=parsed.dockerfile,
        readme_md=parsed.readme_md,
        my_contract_sol=parsed.my_contract_sol,
        my_contract_test_js=parsed.my_contract_test_js,
        deploy_js=parsed.deploy_js,
        hardhat_config_js=parsed.hardhat_config_js,
        iterations_log=parsed.iterations_log,
        package_json=parsed.package_json,
        package_lock_json=parsed.package_lock_json
    )
