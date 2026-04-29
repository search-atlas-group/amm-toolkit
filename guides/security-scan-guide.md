# Security Scanning — Plain English Guide

> For developers, marketers, and anyone who runs code they found online.

---

## The Problem This Solves

When someone says "install this library" or "clone this repo," they're asking you to run code written by someone you've never met. Most of the time that's fine. But occasionally, that code is designed to:

- **Steal your passwords or API keys** stored on your computer
- **Mine cryptocurrency** silently in the background (using your electricity and slowing your machine)
- **Create a backdoor** that lets a stranger control your computer remotely
- **Send your files** to someone else's server

This tool checks for all of that before you run anything.

---

## What You Need

**Nothing special.** The scan works immediately with just Claude Code, which you already have.

Optional tools make the scan more thorough (takes 2 minutes to install, Claude will do it for you if you want).

---

## How To Use It

Open Claude Code, type this, and press Enter:

```
/security-scan https://github.com/owner/repo-name
```

Replace the URL with whatever repo you want to check.

That's it. Claude will do the rest and give you a plain-English answer.

---

## What the Verdict Means

### ✅ SAFE TO USE
No meaningful risks found. You can proceed normally.

### ⚠️ USE WITH CARE
Some minor concerns — like an outdated library or a minor code smell. Claude will explain exactly what it found. Usually fine to proceed, but read the details first.

### 🔶 DO NOT RUN YET
Real concerns. Don't install this until someone technical has reviewed it. Claude will tell you specifically what's wrong and who to contact.

### ❌ DO NOT INSTALL
Confirmed threat. Delete any copy of this immediately. If you already ran it, take the steps Claude recommends (usually: change passwords, revoke any API keys you used recently).

---

## How the Scanning Works

The scan runs in layers, from fastest to most thorough:

### Layer 1 — Before touching any code
Claude checks the repo's public profile: How old is it? How many people use it? Does it have a history? A brand-new repo with zero users claiming to be a popular tool is an immediate red flag.

### Layer 2 — Reading the code
Claude reads the code like a security analyst would. It looks for:
- Code that connects to outside servers during installation
- Code that reads your SSH keys, passwords, or saved credentials
- Code that's been intentionally scrambled to look harmless
- Programs hidden inside what should be text files
- Instructions that run automatically when you install the package

### Layer 3 — Automated security tools (optional)
If you've installed the security tools (or said yes when Claude offered), it also:
- Checks against a database of known security vulnerabilities
- Scans the entire history of the repo (not just current code) for leaked passwords
- Runs professional-grade code analysis used by enterprise security teams

### Layer 4 — Sandbox test (optional)
This is the most powerful check. It runs the code inside a completely sealed-off virtual zone on your Mac. The zone has no internet access and can't touch your real files. Claude watches what the code tries to do and reports anything unusual.

**You don't need Docker for this.** Your Mac has a built-in security feature that creates this zone — nothing extra to install.

---

## Frequently Asked Questions

**"I'm not technical. Can I still use this?"**
Yes. Claude will explain everything in plain English. You don't need to understand what "SAST" or "CVE" means — Claude will translate.

**"Does this slow down my computer?"**
No. The scan runs on code that hasn't been installed yet, so there's nothing active on your machine.

**"Does the scan require internet access?"**
Yes, to download the repo and check public databases. But the *sandbox test* works with internet blocked — that's the whole point.

**"What if the repo is private?"**
The surface check (Layer 1) won't work for private repos. But Layers 2–4 still work once you have a local copy. Run `/security-scan /path/to/your/folder` instead.

**"Can I scan a repo I already cloned?"**
Yes. Run `/security-scan /full/path/to/the/folder`.

**"What if Claude says it can't check something?"**
That's honest — it means a specific check wasn't possible (maybe a tool isn't installed, or the repo requires authentication). The verdict will reflect what was actually checked. Claude will tell you what it couldn't verify.

**"How long does a scan take?"**
- AI-only: 1–2 minutes
- With tools installed: 3–5 minutes
- With sandbox: 5–8 minutes

**"Should I scan every repo I use?"**
Reasonable rule: scan anything from a source you don't know personally, haven't used before, or that someone sent you unexpectedly. You don't need to scan major open-source projects like React or Django — but you should scan any small utility, plugin, or tool shared in a Discord, Slack, or email.

---

## Installing the Security Tools (Optional)

If you want the most thorough scans, install the security tools once:

1. Open Terminal (press `Cmd + Space`, type "Terminal", press Enter)
2. Copy and paste this line, press Enter:

```bash
bash /path/to/your/agentic-mastermind/scripts/install-security-tools.sh
```

Or just ask Claude — it will offer to install them the first time you run `/security-scan`.

**What gets installed:**
- **Trivy** — checks your dependencies against a database of known hacks (like a virus scanner for your code libraries)
- **Gitleaks** — scans for accidentally committed passwords or API keys
- **TruffleHog** — digs through the entire history of the repo looking for secrets that were deleted but might still be recoverable
- **Semgrep** — reads the code looking for patterns that security researchers know are dangerous

None of these tools send your code anywhere. They all run locally on your machine.

---

## Sharing a Scan Report With Your Team

After every scan, Claude saves a report to `Security/scans/` in your workspace.

You can share it directly, or ask Claude to send it:

```
/security-scan https://github.com/owner/repo --share
```

This will post the report to your Slack channel after the scan completes.

---

## If You Find Something Dangerous

1. **Don't panic.** Finding it before running it means it didn't do anything yet.
2. **Don't install it.** Close the terminal window / folder.
3. **Report it** using the "Report repository" button on GitHub (flag icon on the repo page).
4. **Tell your team** — if this was shared in a work channel, others might have already installed it.
5. **If you already ran it**: change any API keys or passwords you've used in the last 24 hours. Claude will give you a specific list of what to revoke.

---

*This guide is part of the Agentic Marketing Mastermind toolkit. For questions, use `/help` in Claude Code.*
