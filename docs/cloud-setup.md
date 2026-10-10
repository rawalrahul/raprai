# Run RAPR on your own server (cloud mode)

Your AIs keep working 24/7 on a server you own, even when your computer is off.
Telegram and WhatsApp keep answering from the server, and the web app opens from
any browser or phone at an `https://` address. Nothing is published to the public
internet except that address, and the PIN protects it.

**What you need:** a Linux server you can SSH into, with at least 1 GB of memory
and 4 GB of free disk. Ubuntu or Debian are the easiest.

## Option 1: a free Oracle Cloud server (costs nothing)

1. Create a free account at https://www.oracle.com/cloud/free/. Oracle asks for a
   card to verify you; the "Always Free" resources below are not charged.
2. In the Oracle console: **Compute → Instances → Create instance**.
   - Image: **Canonical Ubuntu**.
   - Shape: **VM.Standard.A1.Flex** (Ampere, ARM), e.g. 2 OCPUs and 12 GB.
     Always free up to 4 OCPUs and 24 GB in total, and much roomier than the
     1 GB **VM.Standard.E2.1.Micro**, which also works but is tight. If A1 says
     it's out of capacity, try another availability domain or try again later.
   - Networking: keep the default public subnet and assign a public IP.
   - SSH keys: **Generate a key pair** and **download the private key**. Keep it safe.
3. Once the instance is running, copy its **Public IP address**.
4. You don't need to open any ports: RAPR connects out to Cloudflare, so the
   server accepts no incoming traffic except SSH (which Oracle already allows).

## Option 2: any other Linux server

Hetzner, DigitalOcean, Contabo, a home server or a Raspberry Pi 4 (64-bit) all
work. Pick Ubuntu 22.04 or 24.04, add your SSH key, and note the IP address.

## Deploy from RAPR

1. Open RAPR on your computer → **Settings → Cloud server (run RAPR 24/7)**.
2. **Server address:** the public IP. **SSH user:** `ubuntu` on Oracle and most
   providers (`root` on some). **Private key:** paste the whole key file you
   downloaded (or type the password if you set one).
3. **PIN for the server:** choose one. You'll type it to open RAPR on the server.
4. Tick the settings you want the server to have: your AI keys and your Telegram
   or WhatsApp settings. Only the ticked ones are sent, over your SSH connection,
   and stored on the server with permission 600.
5. Press **Deploy to my server**. The log shows each step. The first deploy takes
   a few minutes because Docker and RAPR are downloaded.
6. When it finishes, the **Open RAPR on your server** link appears. Open it and
   enter your PIN.

## No laptop? Set it up from the server

You don't need RAPR installed anywhere else. Log in to your server (from a
terminal, Oracle's **Cloud Shell** in the browser, or an SSH app on your phone
such as Termius) and paste:

```
curl -fsSL https://raw.githubusercontent.com/rawalrahul/raprai/main/scripts/install-server.sh | bash
```

It installs Docker if needed, asks you to choose a PIN (only its hash is
saved), starts RAPR and prints the address to open. It's the same setup as
**Deploy from RAPR** above. Afterwards the `rapr` command on the server helps:

| Command | What it does |
| --- | --- |
| `rapr url` | Shows the current address (it changes when the server restarts) |
| `rapr status` | Shows whether RAPR is running |
| `rapr logs` | Shows RAPR's recent log |
| `rapr update` | Downloads the newest RAPR and restarts it (also: run the install command again) |
| `rapr restart` | Restarts RAPR |
| `rapr remove` | Removes RAPR and its data from the server |

AI keys and chat-app tokens are then added in the server's own RAPR, under Settings.

## Things to know

- **The address can change.** The free Cloudflare tunnel gives a new
  `https://….trycloudflare.com` address each time the server restarts. RAPR
  shows the current one in Settings. Telegram and WhatsApp don't need the address.
- **WhatsApp must be linked again on the server.** It's a separate linked device.
  Open the server's RAPR → Settings → WhatsApp and scan the QR code.
- **AI logins.** AI tools that sign in with a browser (Claude Code, Codex, Gemini
  CLI) need a one-time sign-in on the server. API keys you copied work straight
  away. Sign-in from the browser on the server is not built yet; until it is,
  use an API key for those AIs in the cloud copy.
- **Keeping it updated.** Settings → Cloud server → **Update** pulls the newest
  RAPR image and restarts it. Your data (chats, playbooks, groups) stays in the
  server's data volume.
- **Removing it.** **Remove from server** stops RAPR and deletes its data on the
  server. It doesn't touch anything else on the server.

## Troubleshooting

| What you see | What to do |
|---|---|
| "could not connect" | Check the IP address and that SSH is allowed. On Oracle, the instance's subnet must allow port 22 (it does by default). |
| "isn't Linux" | RAPR cloud setup only works on Linux servers. |
| "1 GB" memory message | Use a bigger shape, or add swap: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`. |
| download fails the first time | The RAPR image is published when a release is made. Try again after the next release. |
| RAPR doesn't answer its health check | Press **View logs** in Settings. |

The server uses the same RAPR as this computer, with the screen-only parts turned
off (no tray, desktop Kelvin or computer use). Kelvin still reports on Telegram,
WhatsApp and the web app.
