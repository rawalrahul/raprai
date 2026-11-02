# RAPR Bridge

Lets [RAPR AI](https://github.com/rawalrahul/raprai), running on this computer, ask GitHub Copilot
questions through **your VS Code sign-in**, so you don't need to install or sign in to the Copilot CLI.

- Uses VS Code's own language model API (`vscode.lm`), the same one Copilot Chat uses. VS Code asks
  you once whether RAPR Bridge may use Copilot's models: run **RAPR: Connect Copilot** and press Allow.
- Serves only this computer: it listens on `127.0.0.1` and answers only requests carrying a random
  key it writes to `~/.config/rapr/vscode-bridge.json`, readable only by you. Nothing is reachable
  from your network.
- Works while VS Code is open. Each request counts against your Copilot plan, like a Copilot Chat one.
- Answers questions; it doesn't edit files.

RAPR installs it for you (ask your AI to "connect Copilot through RAPR", or run
`code --install-extension <path>`); see RAPR's guide.
