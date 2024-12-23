import React from 'react';
import { Card } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";

interface WorkflowFormProps {
  userPrompt: string;
  setUserPrompt: (value: string) => void;
  testConditions: string;
  setTestConditions: (value: string) => void;
  advancedMode: boolean;
  setAdvancedMode: (value: boolean) => void;
  generateCodePrompt: string;
  setGenerateCodePrompt: (value: string) => void;
  validateOutputPrompt: string;
  setValidateOutputPrompt: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
}

const WorkflowForm = ({
  userPrompt,
  setUserPrompt,
  testConditions,
  setTestConditions,
  advancedMode,
  setAdvancedMode,
  generateCodePrompt,
  setGenerateCodePrompt,
  validateOutputPrompt,
  setValidateOutputPrompt,
  onSubmit,
  isLoading
}: WorkflowFormProps) => {
  return (
    <Card className="p-6 card-glow">
      <form onSubmit={onSubmit} className="space-y-6">
        <div className="flex justify-between items-center mb-6">
          <div className="flex items-center space-x-2">
            <Switch
              checked={advancedMode}
              onCheckedChange={setAdvancedMode}
              id="advanced-mode"
            />
            <Label htmlFor="advanced-mode">Advanced Mode</Label>
          </div>
        </div>

        <div className="space-y-4">
          <div>
            <Label htmlFor="user-prompt">User Prompt</Label>
            <Textarea
              id="user-prompt"
              value={userPrompt}
              onChange={(e) => setUserPrompt(e.target.value)}
              className="h-32 mt-2 textarea-code"
              placeholder="Build an ERC-721 NFT contract that uses Crossmint to automatically mint an NFT when the user pays. Deploy to Mode Testnet using WALLET_PRIVATE_KEY."

            />
          </div>

          <div>
            <Label htmlFor="test-conditions">Test Conditions</Label>
            <Textarea
              id="test-conditions"
              value={testConditions}
              onChange={(e) => setTestConditions(e.target.value)}
              className="h-32 mt-2 textarea-code"
              placeholder="1. The contract is a valid ERC-721 NFT contract.
2. The contract integrates Crossmint’s API so that whenever a user calls a “mint” function and pays the required amount, Crossmint is invoked to automate the minting process.
3. The contract is deployed successfully to Mode Testnet at chain ID 919. 
   - Use `process.env.WALLET_PRIVATE_KEY` for signing transactions in the deploy script.
4. A Hardhat test script confirms:
   - The contract compiles successfully (no compilation errors).
   - At least one test transaction is performed on Mode Testnet to confirm deployment. 
   - If the user wants a more thorough test, check that `balanceOf(minter)` increments by 1 after the mint function.
5. If Crossmint has any relevant environment variables like `CROSSMINT_API_KEY`, ensure they are read from `process.env`.
6. The Docker container must exit with code 0 only if:
   - The contract compiles.
   - The Hardhat tests pass.
   - The contract is deployed on Mode Testnet without errors.
7. Print the final deployed contract address (on Mode Testnet) to stdout or logs.
"
            />
          </div>

          {advancedMode && (
            <div className="space-y-4 animate-fade-in">
              <div>
                <Label htmlFor="generate-code-prompt">Generate Code Prompt</Label>
                <Textarea
                  id="generate-code-prompt"
                  value={generateCodePrompt}
                  onChange={(e) => setGenerateCodePrompt(e.target.value)}
                  className="h-48 mt-2 textarea-code"
                />
              </div>

              <div>
                <Label htmlFor="validate-output-prompt">Validate Output Prompt</Label>
                <Textarea
                  id="validate-output-prompt"
                  value={validateOutputPrompt}
                  onChange={(e) => setValidateOutputPrompt(e.target.value)}
                  className="h-48 mt-2 textarea-code"
                />
              </div>
            </div>
          )}
        </div>

        <Button 
          type="submit" 
          className="w-full"
          disabled={isLoading}
        >
          {isLoading ? "Processing..." : "Run Workflow"}
        </Button>
      </form>
    </Card>
  );
};

export default WorkflowForm;
