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

# Import prompt templates and environment variable instructions
from src.prompts import (
    current_generate_code_prompt,
    current_validate_output_prompt,
    build_system_message
)

########################
# OPENAI CONFIGURATION #
########################
openai.api_key = os.environ.get("OPENAI_KEY")
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
    files: list  # list of {"filename": <str>, "content": <str>}

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
    Calls the LLM to produce a Dockerfile + multiple files.
    Includes environment variables in the system message if non-empty.
    """
    log.info("generate_code started", input=input)

    # 1) Gather environment variables behind the scenes
    env_vars = {}
        # "WALLET_PRIVATE_KEY": os.environ.get("WALLET_PRIVATE_KEY", ""),
        # "WALLET_ADDRESS": os.environ.get("WALLET_ADDRESS", ""),
        # "MODE_NETWORK": os.environ.get("MODE_NETWORK", ""),
        # "CROSSMINT_API_KEY": os.environ.get("CROSSMINT_API_KEY", "")

    # 2) Build a system prompt that tells the LLM about these variables
    system_message = build_system_message(env_vars)

    # 3) Merge the user prompt with our default instructions
    user_prompt_text = current_generate_code_prompt.format(
        user_prompt=input.user_prompt,
        test_conditions=input.test_conditions
    )

    # 4) Request structured output from GPT
    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt_text}
        ],
        response_format=GenerateCodeSchema
    )

    # 5) Check results
    result = completion.choices[0].message
    if result.refusal:
        raise RuntimeError("Model refused to generate code.")

    # 6) Convert to final data structures
    data = result.parsed
    files_list = [{"filename": f.filename, "content": f.content} for f in data.files]

    return GenerateCodeOutput(dockerfile=data.dockerfile, files=files_list)

############################
# 2) RUN LOCALLY           #
############################
@function.defn()
async def run_locally(input: RunCodeInput) -> RunCodeOutput:
    """
    Builds and runs the Docker container in a temp directory. 
    If environment variables are present, we write them to .env.
    The LLM-coded Dockerfile is expected to COPY or reference .env if needed.
    """
    log.info("run_locally started", input=input)

    # If you want to pass environment variables into the container:
    env_vars = {}
        # "WALLET_PRIVATE_KEY": os.environ.get("WALLET_PRIVATE_KEY", ""),
        # "WALLET_ADDRESS": os.environ.get("WALLET_ADDRESS", ""),
        # "MODE_NETWORK": os.environ.get("MODE_NETWORK", ""),
        # "CROSSMINT_API_KEY": os.environ.get("CROSSMINT_API_KEY", "")

    with tempfile.TemporaryDirectory() as temp_dir:
        # 1) Write Dockerfile
        dockerfile_path = os.path.join(temp_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as df:
            df.write(input.dockerfile)

        # 2) Write each file
        for file_item in input.files:
            file_path = os.path.join(temp_dir, file_item["filename"])
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as ff:
                ff.write(file_item["content"])

        # 3) If any environment variables are non-empty, write .env
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
    Calls the LLM to validate whether the generated code meets test conditions.
    If not, it may provide updated dockerfile/files.
    """
    log.info("validate_output started", input=input)

    # Convert files array to JSON string for the prompt
    files_str = json.dumps(input.files, indent=2)

    validation_prompt = current_validate_output_prompt.format(
        test_conditions=input.test_conditions,
        dockerfile=input.dockerfile,
        files_str=files_str,
        output=input.output
    )

    completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
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
        # Model refused or gave no valid answer
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
