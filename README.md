# Auto Mode Autonomous Smart Contract Creation Coding Workflow

```
git clone https://github.com/Pomu-io/Auto-Mode.git
cd Auto-Mode
```
```
echo "OPENAI_KEY=sk-..." > .env
```
```
docker compose up
```
* Frontend UI: http://localhost:3000/
* Restack UI: http://localhost:5233/

### Usage in Frontend UI
1. Enter your user_prompt and test_conditions.
2. Click "Run Workflow".
3. Wait for your project code to complete!
* 🤖 It will recursively generate code, run the code, and fix the code if needed until it deems that your test case(s) are fulfilled.
