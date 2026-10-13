# Security

Estonian Finance Planner runs entirely in your browser. It has no server, no account and no database; the numbers you enter are saved only in your own browser. Even so, a bug could expose them, for example by letting a crafted backup file run code. Reports like that are very welcome.

## Supported versions

Only the [latest release](https://github.com/UnauthenticatedUser/Finance-Planner/releases/latest) and the [online version](https://unauthenticateduser.github.io/Finance-Planner/) get fixes. If you use an older downloaded copy, please update before reporting.

## Reporting a problem

Please report security problems **privately**, not in a public issue:

1. Go to the repository's [Security tab](https://github.com/UnauthenticatedUser/Finance-Planner/security).
2. Click **Report a vulnerability**.
3. Describe what you found, how to reproduce it (a sample backup file helps), and what an attacker could do with it.

Please don't include your own real financial numbers; made-up ones are enough.

You'll get a reply as soon as I can, usually within a week. Once a fix is released, the problem is described in [CHANGELOG.md](CHANGELOG.md), and you're credited if you'd like to be.

## What counts

Examples of what's in scope:

- Code or HTML from a backup file, a name or a note being run or shown as markup (cross-site scripting)
- Any way for your numbers to leave the browser without you doing it
- The page being usable inside another website (clickjacking)
- Saved data being lost or corrupted by a crafted file

Out of scope: problems that need someone who already controls your computer or browser (for example a malicious browser extension), and the fact that saved data isn't encrypted (see the README).
