# Copyright (C) 2024 Harrison E. Muchnic
# This program is licensed under the Affero General Public License (AGPL).
# See the LICENSE file for details.

# ./backend/src/workflows/workflow.py

from restack_ai.workflow import workflow, import_functions, log
from dataclasses import dataclass
from datetime import timedelta

with import_functions():
    from src.functions.functions import (
        generate_code, run_locally, validate_output,
        GenerateCodeInput, RunCodeInput, ValidateOutputInput
    )

@dataclass
class WorkflowInputParams:
    user_prompt: str
    test_conditions: str

@workflow.defn()
class AutonomousCodingWorkflow:
    @workflow.run
    async def run(self, input: WorkflowInputParams):
        log.info("AutonomousCodingWorkflow started", input=input)

        # Step 1: Generate the code (first pass)
        gen_output = await workflow.step(
            generate_code,
            GenerateCodeInput(
                user_prompt=input.user_prompt,
                test_conditions=input.test_conditions
            ),
            start_to_close_timeout=timedelta(seconds=300)
        )

        # Store each field
        dockerfile = gen_output.dockerfile
        readme_md = gen_output.readme_md
        my_contract_sol = gen_output.my_contract_sol
        my_contract_test_js = gen_output.my_contract_test_js
        deploy_js = gen_output.deploy_js
        hardhat_config_js = gen_output.hardhat_config_js
        iterations_log = gen_output.iterations_log
        package_json = gen_output.package_json
        package_lock_json = gen_output.package_lock_json

        iteration_count = 0
        max_iterations = 20

        while iteration_count < max_iterations:
            iteration_count += 1
            log.info(f"Iteration {iteration_count} start")

            # Step 2: Run code
            run_output = await workflow.step(
                run_locally,
                RunCodeInput(
                    dockerfile=dockerfile,
                    readme_md=readme_md,
                    my_contract_sol=my_contract_sol,
                    my_contract_test_js=my_contract_test_js,
                    deploy_js=deploy_js,
                    hardhat_config_js=hardhat_config_js,
                    iterations_log=iterations_log,
                    package_json=package_json,
                    package_lock_json=package_lock_json
                ),
                start_to_close_timeout=timedelta(seconds=300)
            )

            # Step 3: Validate output
            val_output = await workflow.step(
                validate_output,
                ValidateOutputInput(
                    dockerfile=dockerfile,
                    readme_md=readme_md,
                    my_contract_sol=my_contract_sol,
                    my_contract_test_js=my_contract_test_js,
                    deploy_js=deploy_js,
                    hardhat_config_js=hardhat_config_js,
                    iterations_log=iterations_log,
                    package_json=package_json,
                    package_lock_json=package_lock_json,
                    output=run_output.output,
                    test_conditions=input.test_conditions
                ),
                start_to_close_timeout=timedelta(seconds=300)
            )

            if val_output.result:
                # On success, return the final JSON so the user sees all files
                return {
                    "success": True,
                    "dockerfile": dockerfile,
                    "readme_md": readme_md,
                    "my_contract_sol": my_contract_sol,
                    "my_contract_test_js": my_contract_test_js,
                    "deploy_js": deploy_js,
                    "hardhat_config_js": hardhat_config_js,
                    "iterations_log": iterations_log,
                    "package_json": package_json,
                    "package_lock_json": package_lock_json
                }

            # Otherwise, update any fields that are not null
            if val_output.dockerfile is not None:
                dockerfile = val_output.dockerfile
            if val_output.readme_md is not None:
                readme_md = val_output.readme_md
            if val_output.my_contract_sol is not None:
                my_contract_sol = val_output.my_contract_sol
            if val_output.my_contract_test_js is not None:
                my_contract_test_js = val_output.my_contract_test_js
            if val_output.deploy_js is not None:
                deploy_js = val_output.deploy_js
            if val_output.hardhat_config_js is not None:
                hardhat_config_js = val_output.hardhat_config_js
            if val_output.iterations_log is not None:
                iterations_log = val_output.iterations_log
            if val_output.package_json is not None:
                package_json = val_output.package_json
            if val_output.package_lock_json is not None:
                package_lock_json = val_output.package_lock_json

        # If we exhaust max_iterations, return the final data anyway, but mark success = False
        return {
            "success": False,
            "dockerfile": dockerfile,
            "readme_md": readme_md,
            "my_contract_sol": my_contract_sol,
            "my_contract_test_js": my_contract_test_js,
            "deploy_js": deploy_js,
            "hardhat_config_js": hardhat_config_js,
            "iterations_log": iterations_log,
            "package_json": package_json,
            "package_lock_json": package_lock_json
        }
