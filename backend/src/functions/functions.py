# Copyright (C) 2024 Harrison E. Muchnic
# This program is licensed under the Affero General Public License (AGPL).
# See the LICENSE file for details.

# ./backend/src/functions/functions.py

import os
import openai
import json
import tempfile
import subprocess

from dataclasses import dataclass
from typing import List, Optional

from pydantic import BaseModel

from restack_ai.function import function, log

# Import our prompt templates and helper from src/prompts.py
from src.prompts import (
    current_generate_code_prompt,
    current_validate_output_prompt,
    build_system_message
)

########################
# OPENAI CONFIGURATION #
########################
openai.api_key = os.environ.get("OPENAI_KEY")

# Using the structured output parsing interface
from openai import OpenAI
client = OpenAI(api_key=openai.api_key)

###########################
# SCHEMAS (FILE-BASED)    #
###########################
class FileItem(BaseModel):
    filename: str
    content: str

    class Config:
        extra = "forbid"
        schema_extra = {
            "type": "object",
            "properties": {
                "filename": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["filename", "content"],
            "additionalProperties": False
        }

class GenerateCodeSchema(BaseModel):
    dockerfile: str
    files: List[FileItem]
    
    class Config:
        extra = "forbid"
        schema_extra = {
            "type": "object",
            "properties": {
                "dockerfile": {"type": "string"},
                "files": {
                    "type": "array",
                    "items": {"$ref": "#/$defs/FileItem"}
                }
            },
            "required": ["dockerfile", "files"],
            "additionalProperties": False,
            "$defs": {
                "FileItem": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["filename", "content"],
                    "additionalProperties": False
                }
            }
        }

class ValidateOutputSchema(BaseModel):
    result: bool
    dockerfile: Optional[str] = None
    files: Optional[List[FileItem]] = None
    
    class Config:
        extra = "forbid"
        schema_extra = {
            "type": "object",
            "properties": {
                "result": {"type": "boolean"},
                "dockerfile": {
                    "anyOf": [
                        {"type": "string"},
                        {"type": "null"}
                    ]
                },
                "files": {
                    "anyOf": [
                        {
                            "type": "array",
                            "items": {"$ref": "#/$defs/FileItem"}
                        },
                        {"type": "null"}
                    ]
                }
            },
            "required": ["result", "dockerfile", "files"],
            "additionalProperties": False,
            "$defs": {
                "FileItem": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string"},
                        "content": {"type": "string"}
                    },
                    "required": ["filename", "content"],
                    "additionalProperties": False
                }
            }
        }

############################
# DATA CLASSES            #
############################
@dataclass
class GenerateCodeInput:
    user_prompt: str
    test_conditions: str

@dataclass
class GenerateCodeOutput:
    dockerfile: str
    files: list

@dataclass
class RunCodeInput:
    dockerfile: str
    files: list  # list of {"filename", "content"}

@dataclass
class RunCodeOutput:
    output: str

@dataclass
class ValidateOutputInput:
    dockerfile: str
    files: list
    output: str
    test_conditions: str

@dataclass
class ValidateOutputOutput:
    result: bool
    dockerfile: Optional[str] = None
    files: Optional[list] = None

############################
# 1) GENERATE CODE         #
############################
@function.defn()
async def generate_code(input: GenerateCodeInput) -> GenerateCodeOutput:
    """
    Generates code (Dockerfile + multiple files) by calling the LLM.
    We gather environment variables behind the scenes and pass them to
    the LLM in the system prompt.
    """
    log.info("generate_code started", input=input)

    # 1) Gather environment variables behind the scenes
    env_vars = {
        "WALLET_PRIVATE_KEY": os.environ.get("WALLET_PRIVATE_KEY", ""),
        "WALLET_ADDRESS": os.environ.get("WALLET_ADDRESS", ""),
        "MODE_NETWORK": os.environ.get("MODE_NETWORK", ""),
        "CROSSMINT_API_KEY": os.environ.get("CROSSMINT_API_KEY", "")
    }
    
    # 2) Build a system prompt that tells the LLM about these variables
    system_message = build_system_message(env_vars)

    # 3) Combine the user prompt with our default instructions
    prompt = current_generate_code_prompt.format(
        user_prompt=input.user_prompt,
        test_conditions=input.test_conditions
    )

    # 4) Call the LLM with structured output
    completion = client.beta.chat.completions.parse(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        response_format=GenerateCodeSchema
    )

    result = completion.choices[0].message
    if result.refusal:
        raise RuntimeError("Model refused to generate code.")
    data = result.parsed

    # 5) Convert the returned list of FileItems into a plain list of dict
    files_list = [{"filename": f.filename, "content": f.content} for f in data.files]

    return GenerateCodeOutput(dockerfile=data.dockerfile, files=files_list)

############################
# 2) RUN LOCALLY           #
############################
@function.defn()
async def run_locally(input: RunCodeInput) -> RunCodeOutput:
    """
    Builds and runs the Docker container. If environment variables
    are provided, writes them to a .env file that can be copied
    by the generated Dockerfile (if it does so).
    """
    log.info("run_locally started", input=input)

    # We'll gather the same environment variables. If they're non-empty,
    # we create .env so the Dockerfile can pick it up (assuming it COPY .env).
    env_vars = {}
    #     "WALLET_PRIVATE_KEY": os.environ.get("WALLET_PRIVATE_KEY", ""),
    #     "WALLET_ADDRESS": os.environ.get("WALLET_ADDRESS", ""),
    #     "MODE_NETWORK": os.environ.get("MODE_NETWORK", ""),
    #     "CROSSMINT_API_KEY": os.environ.get("CROSSMINT_API_KEY", "")
    

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1) Write out the Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as df:
            df.write(input.dockerfile)

        # 2) Write each file
        for file_item in input.files:
            file_path = os.path.join(temp_dir, file_item["filename"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as ff:
                ff.write(file_item["content"])

        # 3) If any non-empty env_vars, write .env
        non_empty_vars = {k: v for k, v in env_vars.items() if v}
        if non_empty_vars:
            env_file_path = os.path.join(temp_dir, ".env")
            with open(env_file_path, "w", encoding="utf-8") as ef:
                for key, val in non_empty_vars.items():
                    ef.write(f"{key}={val}\n")

        # 4) Docker build
        build_cmd = ["docker", "build", "-t", "myapp", temp_dir]
        build_process = subprocess.run(build_cmd, capture_output=True, text=True)
        if build_process.returncode != 0:
            return RunCodeOutput(output=build_process.stderr or build_process.stdout)
        
        # 5) Docker run
        run_cmd = ["docker", "run", "--rm", "myapp"]
        run_process = subprocess.run(run_cmd, capture_output=True, text=True)
        if run_process.returncode != 0:
            return RunCodeOutput(output=run_process.stderr or run_process.stdout)
        
        return RunCodeOutput(output=run_process.stdout)

################################
# 3) VALIDATE OUTPUT           #
################################
@function.defn()
async def validate_output(input: ValidateOutputInput) -> ValidateOutputOutput:
    """
    Calls the LLM to validate whether the generated code meets
    the test conditions. If not, the LLM can provide updated
    dockerfile/files.
    """
    log.info("validate_output started", input=input)

    files_str = json.dumps(input.files, indent=2)

    # For validation, we generally don't need environment vars in the prompt,
    # but you could also incorporate them if your logic demands.
    validation_prompt = current_validate_output_prompt.format(
        test_conditions=input.test_conditions,
        dockerfile=input.dockerfile,
        files_str=files_str,
        output=input.output
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an autonomous coding assistant agent. "
                    "If you change any files, provide complete file content replacements."
                )
            },
            {"role": "user", "content": validation_prompt}
        ],
        response_format=ValidateOutputSchema
    )

    result = completion.choices[0].message
    if result.refusal:
        # Model refused or did not provide a result
        return ValidateOutputOutput(result=False)

    data = result.parsed
    updated_files = (
        [{"filename": f.filename, "content": f.content} for f in data.files]
        if data.files is not None
        else None
    )

    return ValidateOutputOutput(
        result=data.result,
        dockerfile=data.dockerfile,
        files=updated_files
    )
