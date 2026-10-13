# Changelog

All notable changes to Estonian Finance Planner are listed here, newest first. Versions follow [semantic versioning](https://semver.org): the last number is for fixes, the middle one for new features, the first one for changes that break something. Saved data and backups from v1.0.0 on keep loading in every later version.

## [1.1.0] – 2026-10-13

- **Health insurance in FIRE targets.** Stop working before pension age and you pay for your own health insurance (€272 a month in 2026, from the Health Insurance Fund). New FIRE targets add it to the yearly spending, and it can be switched off per target. FIRE targets you already had keep their numbers until you switch it on.
- **Clearer pension rules.** Retirement's "How it's worked out" now says when pension funds can be paid out (up to 5 years before pension age), that earlier withdrawals are taxed 22%, and the 3rd pillar's 5-year rule. Retiring before 65 shows a reminder about health insurance.
- **Stricter security rule.** The page now only runs its own scripts, identified by their SHA-256 fingerprints, so a script that got into the page some other way is blocked. `tools/update_csp.py` updates the fingerprints after a script changes.
- **Accessibility.** A "Skip to content" link for keyboard users, a label for the goals and notes box, and a new test that checks names, contrast and visible focus.
- **Tests in more browsers.** The tests now also run in Firefox and WebKit (Safari's engine). GitHub Actions are pinned to exact versions, and Dependabot proposes updates.
- Sources for the new figures are in the README.

Saved data and backups from v1.0.0 keep working.

## [1.0.0] – 2026-10-13

First public release.

- Overview: net worth, savings rate, invested per month, cash buffer and yearly surplus; yearly income with a full tax breakdown; projection of pensions and investments after inflation, fees and tax, with a range; portfolio allocation; monthly budget; cash and savings, pensions (II and III pillar), ETFs with a target split and rebalancing suggestion, other investments, physical assets and debts with payoff dates.
- Spending as one total or by category, with yearly costs like car tax spread over the months and a link to the official car tax calculator.
- Progress: net worth over time with amounts on the chart, targets with deadlines (emergency fund, net worth, invested total, FIRE, your own goal), and retirement income per month after tax.
- Tax and pension rules for Estonia 2026, with sources listed in the README. Every rule and assumption can be changed in the editor.
- English and Estonian.
- Show an example: look around with made-up numbers that are never saved.
- Your data stays in your browser: Export and Import for backups, Undo after Reset or Import, and Delete all my data.
- Privacy and security: the page makes no network requests and blocks them with a Content-Security-Policy; it refuses to show inside another website; backup files are checked and cleaned before loading.
- Works on phones and wide screens, and offline as a single downloaded file.
- Automated tests check the calculations against independent models on every change, and the online version is only published when they all pass.

[1.1.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.0
[1.0.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.0.0
