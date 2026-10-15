# Changelog

All notable changes to Estonian Finance Planner are listed here, newest first. Versions follow [semantic versioning](https://semver.org): the last number is for fixes, the middle one for new features, the first one for changes that break something. Saved data and backups from v1.0.0 on keep loading in every later version.

## [1.1.7] – 2026-10-15

- **Choose how much of your yearly surplus to invest.** The on/off switch "Also invest my yearly surplus" is now a percentage, so you can invest part of it and keep the rest as cash, for example to keep growing an emergency fund. A slider splits it between Cash and Investments. Under each end you can type that side's share (the other side and the slider follow) and see its euros a year. While you drag, every number and the projection chart update at once, with a short glow, so the feedback keeps up; typing anywhere else still rolls the numbers as before. The rest grows your cash buffer, and the Projection, Retirement and Targets use the split.
- **The setting moved** from Settings › Projection to its own place at the top of Savings & investments › Yearly surplus, next to the money it's about. Settings keeps the assumptions, such as return, inflation and taxes.
- **The Annual surplus tile shows the split:** "60% invested / year", and when you open it, how many euros go to your investments and how many stay as cash, with a Change link to the setting. The emergency fund's "your surplus is invested" link opens the new place too.
- **Back to top on phones and tablets.** Once you scroll down into the editor, a "Back to top" button appears at the bottom and takes you up. After a card's ✎ the same button still says "Back to dashboard" and takes you back to that card.
- **Number fields only take numbers.** Euro amounts take 2 decimals, rates 3 (Euribor and fund fees are quoted that way), the surplus share 1 and the year of birth none; typing or pasting more digits doesn't add them. A minus sign only goes at the start, and only where the value can be negative, and a second decimal point is ignored, so strings like "-.,-,-." can't pile up. A field left with only a sign shows empty again. Values already saved are kept as they are.
- **Fixes from v1.1.6:** on phones, the "Back to dashboard" button now moves up above the Undo note instead of sitting under it. In Cash & savings, an account with a long name keeps its rate and interest together on the line under the name, instead of breaking them across two lines.
- Tests cover the split in the projection, retirement and target dates, the tile, both links, the slider, older data, Back to top and both fixes, and check that decimals work with a comma or a dot and stop at each field's limit.

Saved data and backups from earlier versions keep working: if you had the surplus switch on, it becomes 100%; off becomes 0%. A backup from this version opened in an older one counts any share above 0% as all of it.

## [1.1.6] – 2026-10-14

- **Calmer cards.** Investments, Cash & savings, Debts and Targets show less small gray text:
  - Investments: one line per fund (name, €/month and share, with the amount on the right). The target share is in the bar's hover text.
  - Cash & savings: each account's rate and yearly interest sit beside its name, so the amounts line up on the right. Interest shows what you keep after tax; the before-tax amount is in its hover text.
  - Debts: two lines per loan (rate and payment; payoff date and interest still to pay), plus the Euribor ±1% range for Euribor loans. The margin and equity are in the hover text on the loan's name.
  - Targets: the share reached sits beside the name, and one line under the bar gives the expected date and, with a deadline, whether you're on track or what extra per month would make it. What counts toward a goal is in the hover text on its name.
- **One rule for amounts.** Exact below €10,000, then €24.6k, €1.02M, €1.5B: in card rows, card headers, legends and the editor's section summaries. Headline numbers, monthly amounts and the yearly breakdown stay exact, and hover texts always show the exact amount.
- **Emergency fund and invested surplus.** When "Also invest my yearly surplus" is on, a cash target says "your surplus is invested", with a link to that setting, so a missing date doesn't look like a fault.
- **Shorter help in the editor.** Five long explanations are now one line each; the full text is in their hover text, and Tab or a screen reader reaches it too.
- **Estonian months** are written out ("5 kuud"), so they aren't mistaken for thousands.
- Switches show a focus ring when you reach them with the keyboard.
- On phones, the "Back to dashboard" button now matches the rest of the look, and it goes away once you scroll back up to the card yourself.
- **Better Estonian.** A full read-through made the Estonian more natural and fixed real mistakes: the loan advice now gives its two dates the right way round, "kinnipidamised" replaces the wrong tax term "mahaarvamised", the 3rd pillar refund no longer reads as "a year ago", and about 40 phrases use plainer, more common words.
- **Edge cases:** amounts in millions round correctly (€1,005,000 is €1.01M), negative rates and margins show a real minus, an account with a negative rate shows it, the Euribor ±1% line is hidden when it would show the same date twice, funds without any target share show no 0%, and a number no longer keeps its glow after a quick edit.
- Tests check the new card rows, the amount rule, the surplus link, the back button and the Estonian texts.

Saved data and backups from earlier versions keep working.

## [1.1.5] – 2026-10-14

- **Clearer import messages.** When a file can't be imported (it isn't a backup from this tool, or it's over 5 MB), the reason now shows in the tool's own note at the top of the screen, next to Import, instead of a browser popup. Screen readers announce it right away.

Saved data and backups from earlier versions keep working.

## [1.1.4] – 2026-10-14

- **Wide layout on big screens.** At most four columns of cards: on bigger screens the cards get wider instead of leaving empty columns on the right. Progress shows Targets and Retirement side by side, each half the width, instead of two narrow cards.
- **Projection chart drawn at its real size.** Like the net worth chart, it's now drawn for the space it has instead of a small drawing stretched to fit, so its labels and lines stay the same size on a phone, a laptop or a very wide screen.
- **No flash on reload.** Reloading on Progress, or in the wide layout, no longer shows Overview or the standard layout for a moment first.

Saved data and backups from earlier versions keep working.

## [1.1.3] – 2026-10-14

- **3rd pillar refund limit shown.** When your 3rd pillar contributions go over the tax refund limit (15% of your income or €6,000 a year, whichever is lower), the editor shows a note with how much gets the refund and how much doesn't, and the Pensions card says so in one line. Before, this was only in a tooltip.
- **Easier to find.** The page now has a short description for search engines, in English and Estonian.
- **Issue forms** on GitHub for a wrong number and for an out-of-date tax or pension rule. Both remind you that issues are public, so you never post your real numbers or backup file. Security problems are pointed to the private report.

Saved data and backups from earlier versions keep working.

## [1.1.2] – 2026-10-14

- **Import size limit.** A file over 5 MB is refused with a message before it's read. A real backup is a few kilobytes; a huge file could freeze the page.
- **Every browser must pass.** The site now updates only when the tests pass in Chromium, Firefox and WebKit (Safari's engine), not just Chromium.
- The tests use Playwright 1.63.
- `tools/update_csp.py` finds the page's scripts with Python's HTML parser instead of a pattern, as GitHub's code scanning recommends, so letter case, attributes and comments can't trip it up.

Saved data and backups from earlier versions keep working.

## [1.1.1] – 2026-10-13

Fixes found in a full review of the calculations:

- **Retiring before pension age.** The state pension now starts at 65, so retiring earlier no longer counts it from day one; Retirement says so and shows it as "from 65". Pension fund payouts that start more than 5 years before pension age are taxed as income (22%), as the law says.
- **Pension payout tax.** Payouts count as tax-free only when spread over at least your remaining life expectancy, 19.3 years at 65, so 19 years is now taxed 10%. The after-tax projection now taxes pension funds the same way as Retirement, instead of always taking off 10%.
- **2nd pillar on your bonus.** The 2nd pillar part of a bonus or yearly salary, and the state's top-up on it, now go into the projection, targets, retirement and the fund fee average. The yearly breakdown shows these rows even when the 2nd pillar comes only from a bonus.
- **Cash targets.** The "+€X/mo would make it" suggestion was too low when you spend more than you earn each month. Cash now grows by your yearly surplus, the same as in the net worth target.
- **Retirement spending** only counts loan payments still running at retirement.
- **Loan advice** compares a loan's rate with your expected return after fund fees.
- **Amounts just under €1M** show as €1M instead of €1000k.
- **Settings** shows the same projection timeframe as the chart.
- The language switch has an Estonian name for screen readers.
- Tests: a shared model for growth and pension tax, checks for each fix above, and less overlap between tests.
- The automated checks on GitHub use the current versions of their GitHub Actions, which run on Node 24.

Saved data and backups from earlier versions keep working.

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

[1.1.7]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.7
[1.1.6]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.6
[1.1.5]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.5
[1.1.4]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.4
[1.1.3]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.3
[1.1.2]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.2
[1.1.1]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.1
[1.1.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.0
[1.0.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.0.0
