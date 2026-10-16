# Changelog

All notable changes to Estonian Finance Planner are listed here, newest first. Versions follow [semantic versioning](https://semver.org): the last number is for fixes, the middle one for new features, the first one for changes that break something. Saved data and backups from v1.0.0 on keep loading in every later version.

## [1.3.1] – 2026-10-17

A code cleanup with no changes in how the tool works or what it shows.

- Calculations that were repeated in several places are now worked out once and shared, so they can't drift apart.
- Checks for browser features that every supported browser has were removed, and duplicated style rules were merged.
- Two test checks that a broader check already covers were removed, along with an unused test helper.

## [1.3.0] – 2026-10-17

New: the business account as a tax type, property bought with a loan keeping up with prices, pension funds growing until their payouts start, and pasting numbers with thousands separators. Also a clearer state pension field and fixes from independent reviews.

- **Pensions and investments grow at their own fees.** One average fee was used for both, so an expensive pension fund slowed your ETFs (and a FIRE date that only depends on them), and cheap ETFs sped up your pensions.
- **Paid-off loans count the same everywhere.** Your path and Targets invested a paid-off loan's payment (as your yearly surplus is split), but the Projection and Retirement didn't; now they do. With "Try other numbers" on, your real loans were added on top of the numbers you tried; not any more.
- **After you retire, loan payments come out of your cash.** Loans were paid down with no money leaving, adding net worth from nowhere. A cash target past retirement now says nothing new goes in.
- **No 3rd pillar refund on business account income.** Business account (ettevõtluskonto) is now its own tax type: 20% plus your 2nd pillar rate, and like the Tax and Customs Board says, it allows no deductions, so it no longer gives a 3rd pillar refund. Its 2nd pillar part (2, 4 or 6%) goes into your 2nd pillar fund, as the law says, so it counts as pension savings, not tax. Freelance work and side business start with it.
- **Pension payouts start 5 years before pension age at the earliest.** Retiring at 60 with a pension age of 65 years and 4 months taxed all payouts at 22%; they now start 4 months later, at 10% or tax-free.
- **"+€X/mo would make it" is a flat amount.** With deposit growth on, it was quietly assumed to rise every year, so the amount shown wasn't enough.
- **Property bought with a loan keeps up with prices.** Everything kept its euro value, so in today's money a home lost about half its value over 30 years. Other things you own still keep their euro value.
- **Working pensioners:** the pensioner tax rules start at the general pension age, not at an earlier pension age of your own (for example for raising children); and without your own state pension, the average is used, not an estimate from your pay today.
- Interest is taxed account by account, so a negative rate on one account no longer lowers the tax on another.
- −€2.50 rounds to −€3, like €2.50 to €3 (it showed −€2).
- A switch saved as the text "false" in a backup is off (it was on).
- Inflation off now says prices are taken to stay the same; the 2029 pension age is called planned; the I pillar's "average pay" is called the 2026 figure its formula uses; the 2nd pillar help says contributions end when its payouts start; the Your path note no longer says property shrinks "a little".
- Lists have limits (50 targets and loans, 50 funds per pillar, 100 of most others), so a crafted backup with huge lists can't freeze the page; "+ Add" stops there.
- The loan advice counts the tax on investment gains as an investment account does: only at the end.
- The example's "behind" target has a June deadline, so it stays behind with these changes.
- **Inflation off no longer grows the state pension.** Typing 0% inflation (or turning After inflation off) still grew the state pension with the earlier 2.5% on the Retirement card, overstating it by about €900 a month for someone retiring in 30 years. Off now counts as 0% everywhere, as on the other cards.
- **FIRE health insurance only until pension age.** It was added to every FIRE goal forever, about €81,600 at 4%, even for people already past pension age. It's now counted only while you'd still be below pension age, so reaching FIRE after it needs less, and the card says so. A FIRE target counts as reached only once you could stop working: holding the smaller goal of later isn't enough today.
- **Your own net pay carries through.** With "Enter my own" net pay, Yearly income still showed the estimate from gross; it now uses your net pay, and the breakdown shows the difference. With no gross pay entered, the gross is worked out from your net pay, so the bonus is taxed correctly and the 2nd pillar, the 3rd pillar refund and the state pension estimate follow your pay.
- **No jump on 1 January.** Time until retirement was counted in whole calendar years, so the Retirement figure and target dates jumped overnight on 1 January. It's now counted in months, to the middle of the year you retire. Your age is taken the same way (birthday mid-year), so someone already retired no longer has their pension tax jump on 1 January either.
- **Undo after Reset and Import brings back your data,** not the blank tool, also after a display choice like "30y" in between.
- **A history month in the future is dropped from an imported backup.** It broke "vs last month". Your own data keeps every month, so opening the tool once with a wrong computer clock costs no history.
- Retirement's How it's worked out says pension funds are paid out without further growth (a cautious choice), and the Pensions card says "for retirement" instead of "locked until retirement", as the 2nd and 3rd pillar can be taken out early (taxed).
- Advice on paying a loan early compares its rate with investing's return after fees and the tax on gains.
- Retirement age and payout years take whole numbers only (a half year showed as "2055.5").
- The state pension age's two boxes have names for screen readers; travel allowance is tax-free within its daily limits; the pension age can be a month or two later for people born late in the year (both in the help).
- The example's names switch language with the rest of the tool.
- **A backup that breaks while loading is no longer called "not a backup".** The message said nothing was changed, though the file had already been loaded (Undo brought your data back). Only a file that can't be read is refused now.
- **Pasting numbers:** "12,345.67", "1.234,56" or "€1,500" pasted into a field keeps its value (they became 12.34, 1.23 and 1.50), and the tool's own minus sign "−" counts when pasted.
- **FIRE withdrawal rate:** a FIRE target from the example or an older backup showed an empty rate while using 4%; it shows 4% now, and an emptied field shows a gray 4. It and an own tax rate stay between 0% and 100%; a loan's rate can still go higher.
- With only your net pay entered, the Income summary said €0/mo; it shows the gross worked out from it, and the backup reminder now comes for this too.
- A field's help near the bottom of the screen covered the field; it goes above it now. Links and the help texts you can Tab to show the same focus ring as buttons, and moving a row to the top or bottom with the keyboard keeps the focus on it.
- In Estonian, your own names in tooltips stay as typed ("Gold 2y" became "Gold 2a").
- Wording: "1 year" and "1 month" instead of "1 years"; a loss in the Projection shows as one ("−€63k growth", it said "+€0"); a negative yearly surplus is "short / year", not "unassigned"; a loan with nothing owned no longer says "100% of your assets"; a target you track yourself no longer says "until you retire"; FIRE without spending asks for it instead of an amount.
- Rounding: −2.25% shows as −2.3% (like 2.25% as 2.3%), no "−0.00", no red "−€0" leftover, "≈ 10 months" instead of "10.0" and no "≈ 0.0 months"; fees like 0.145% show as 0.15% (it showed 0.14%); the donut's tooltips use the legend's percentages, and the history chart keeps its €0 label.
- The projection's years are whole numbers, so a 10/20/30/40 button lights up; Undo of a removed row says the list is full instead of bringing back a row that would disappear on the next load.
- **Retiring before pension payouts can start:** your pension funds stay invested until they do (up to 5 years before pension age), so they keep growing, with nothing new going in; Retirement used what they held on the day you retired (less than half as much in one example), while Your path already grew them.
- **A loan still running when you retire** is counted in today's money on the Retirement card (it was in future euros, so "covers X% of your spending" was too low).
- **Notes could be emptied:** an edit that took Goals & notes over their 20,000-character limit put back an empty box, which was then saved. The edit is now just refused.
- **FIRE without any spending entered** asks for it; before, health insurance alone (€81.6k) became the goal and could even show as reached.
- History: this month's snapshot follows your net worth down to €0 (it stayed at the last amount above zero).
- A backup's odd values are made ones the editor can show: a deadline in the year 9999 is cleared, years and ages are whole (a birth year 1990.5 showed "in 2055.5"), a card title left empty gets its name back, and a tiny value no longer shows as "1e-7".
- In Estonian, "weekly", "quarterly" and "yearly" on other income are translated, and so is FIRE's "/yr" for screen readers. The 3rd pillar refund's tooltip and the payout note use your tax rate, not a fixed 22%. The wide layout button works when the browser blocks saving.
- **The state pension field says what it is.** It's now called "State pension (I pillar)" instead of "State pension forecast (optional)". Left empty, it shows the figure the tool uses in gray, and a line under it says where it comes from: estimated from your pay, or the national average when no pay is entered.

## [1.2.2] – 2026-10-16

- **A richer example.** "Show an example" now has a target already reached ("50K invested") and one behind its deadline ("250K net worth", with the extra per month that would make it), next to one on track and FIRE, so every kind of target status can be seen. It also has rental income under Other income, taxed 17.6%. The README screenshots show the new example, and Your path has its own screenshot.

## [1.2.1] – 2026-10-16

Fixes for v1.2.0, and Estonian rules the tool had simplified.

- **State pension age by year of birth.** It was always 65. It's now 65 if you were born in 1961 or earlier, and 65 years and 1, 3 or 4 months if you were born in 1962, 1963 or 1964. After that it follows life expectancy, so 65 years and 4 months is used and the Retirement card says it may be later. You can set your own under Settings › Retirement › Advanced, for example if you retire early for raising children. The tax on pension fund payouts started more than 5 years before pension age follows it too. If the state pension starts less than a year after you retire, it stays in the total and the card says how long the gap is.
- **Working pensioners' pay.** From pension age no unemployment insurance is taken from pay. The €776 tax-free amount goes to the state pension first, and pay only gets what's left of it instead of €700. For example, a €700 pension and €1,000 pay now nets €796.72, as in the Tax and Customs Board's example.
- **Other income starts with its usual tax.** Picking rental income, freelance work, a side business, royalties, dividends, child benefit or travel allowance sets its tax; anything else still starts as taxed like salary.
- **State pension estimated from your pay.** Without your own forecast, the Retirement card used the €860 national average for everyone. It now works the state pension out from your pay the way the Social Insurance Board does: a €399.24 base part plus €10.477 a month for each year's unit, a year at the average pay being 1 unit (0.8 in the II pillar), counted from age 20 until you retire. Without any pay entered it still uses the average. How it's worked out shows the numbers, says you need 15 years of work in Estonia, and explains why the official pension calculator shows lower II and III pillar figures (it counts them as growing only as fast as prices).
- **State pension forecast:** the help now says where to find your official forecast (the Social Insurance Board's pension calculator) and to enter only its I pillar line, because the II and III pillar are worked out from your own numbers. The Retirement card no longer says the state pension starts at 65.
- **Euribor starts at 2.9%** for new users (the 6-month rate in mid-October 2026, was 2.6%). A value you've entered isn't changed.
- One warning instead of two when the pension contribution split doesn't add up to 100%.
- Arrow buttons light up gray on hover instead of red; only delete is red.
- Text sizes tidied: chart labels, editor section titles and a few smaller lines follow the same scale.
- In Estonian, the state pension age is called "Vanaduspensioniiga", so it isn't confused with the retirement age.
- **No more lag with several targets.** In v1.2.0 every target worked out its date and its "+€X/mo" by running a 60-year forecast again and again, so each target made typing and the yearly surplus slider slower; with 8 targets a change took about four times as long, enough to make slower computers lag and their fans spin up. The forecast is now worked out once per change and shared by all targets and Your path, and the extra per month is found without re-running it, so 8 targets cost about as much as in v1.1.7. The slider also redraws at most once per screen frame while you drag, so it can't fall behind. The numbers are the same as before.
- **Wide layout on Progress:** Targets sit on the left with Retirement and Net worth over time stacked on the right, so neither column leaves a big empty space. Your path's chart is taller on wide screens and its list of dates uses as many columns as fit, so a name and its date stay close together.
- **Your path after clearing your data:** the card showed its "Add what you own…" hint but kept the previous list of milestones under it, for example the example's dates after leaving "Show an example". The list and legend now clear too.
- **Retirement card:** after removing your year of birth, the header no longer keeps the old "in 2055 · age 65".
- **At or past your retirement age, no new saving is counted.** The Projection, Targets and Your path now start from what you have today, as the Retirement card already did. Before, someone retiring this year was forecast to keep saving forever, while someone retiring next year stopped after a year. If you still work, raise the retirement age under Settings › Retirement. The notes under each card say this in the same words.
- **Your path:** the hover box lists only the parts you have, like the legend, and How it's worked out mentions property, inflation and paid-off loans only when they apply.
- Leftover styles and code from earlier versions were removed. Nothing you see changes.

Saved data and backups from earlier versions keep working.

## [1.2.0] – 2026-10-15

A new chart on Progress, a calmer, tidier look, and paid-off loans now follow your surplus split.

- **Your path**, a new card at the top of Progress: what your net worth is made of, month by month, from today. Property, pensions, investments and cash are stacked above the line, what you still owe is below it (and, if you spend more than you earn, the cash you'd be short of), and a white line on top is your net worth. It grows the same way as the net worth target: pensions and investments as in the Projection, plus what paid-off loans free up (see below), in today's money when inflation is on.
  - Dots on the line mark when you reach each target, when each loan is paid off and when you retire, with a list of the dates under the chart. Pointing at a dot or a row lights up both.
  - Point at the chart (or touch it on a phone) to see that month's net worth and each part, plus any milestones nearby.
  - Zoom to 5, 10, 20 or 30 years, or to retirement once you've entered your year of birth. Each zoom label (and the Projection's) has the same space around it, the first and last ones too.
  - With nothing entered yet, the card shows a short hint instead of an empty chart.
  - Rename it by clicking its title, like every other card.
- **More realistic forecasts:**
  - **Saving stops when you retire.** Once you've entered your year of birth, deposits from your pay (pension contributions, investing and spare cash) stop in the year you retire, in the Projection, Targets and Your path; what you have keeps growing. Before, they went on forever. The Retirement card already counted up to retirement and doesn't change. When you'd retire before a target's deadline, its extra per month says "until you retire".
  - **Cash earns interest.** In targets and Your path, your cash grows by your accounts' interest after tax: the average rate over all your cash (cash on hand earns nothing).
  - **Deposit growth covers all your saving.** The yearly rise in deposits (Settings › Projection) now also lifts the part of your surplus you keep as cash, not only what you invest. A shortfall doesn't grow.
  - **A loan without a monthly payment stays at today's balance** in targets and Your path, instead of growing with interest. Your path names it and asks for its payment.
  - Your path's How it's worked out says when saving stops, what cash earns, and whether its amounts are before or after tax.
- **Net worth over time moved to the bottom of Progress.** It only becomes useful after a few months of snapshots, so the cards that work from the first day come first: Your path, Targets, Retirement.
- **One row of switches for the whole Progress page:** "After inflation", "After tax" and "Loan payoffs", in the same order as on the Projection. They sit once above the cards instead of on single cards.
  - **After tax is new on Progress.** It's the same switch as the Projection's. Your path, and invested, net worth and FIRE targets, show what you'd keep if you took the money out at that point: pension payouts taxed the way Retirement pays them out, and income tax on investment gains above what you put in. Growth itself is never taxed along the way, since investments are assumed to be in an investment account (investeerimiskonto). Target dates and the extra per month follow the after-tax amounts, and the cards say "after tax".
  - A goal that no amount could reach by its deadline now says "out of reach" instead of a huge amount a month.
  - "Loan payoffs" was "Debts" on the Targets card; it now marks payoff dates on both Targets and Your path.
  - The After tax buttons' hover text now describes the tax correctly. It used to say 10% on pension payouts, while the tool applies the payout tax Retirement uses, which is often 0%.
- **One set of sizes.** Text uses a small, fixed set of sizes, each with one job: notes and labels, body text, card titles, tile figures, each card's key figure (projection, retirement, progress) and the net worth headline. Corners come in three sizes: small buttons, fields and inner boxes, and cards.
- **Clearer layers.** Cards, tiles and editor sections share one faint edge, so they stand apart from the page; things that float (menus, notes, tooltips, the back button) share one shadow.
- **Color where it means something.** Card and editor icons and the editor's section dots are now quiet gray. Color stays for the data: charts, gains and debts, and the blue accent. The retirement figure is white instead of yellow.
- **Paid-off loans follow your surplus split.** Once a loan is paid off, its monthly payment is money you have to spare, so it's now split like your yearly surplus: the share you invest goes to your investments and grows with them, the rest goes to cash. Before, only the net worth target counted it, all as cash. Now cash, invested, net worth and FIRE targets and Your path all use the split:
  - With 0% invested (the default), an emergency fund now gets the freed payment too, so its date can come sooner. Net worth targets stay as they were.
  - With 100% invested, all of it is invested: an emergency fund doesn't get it, while invested, net worth and FIRE targets can come sooner.
  - A loan's last payment is only what's left on it, so the rest of that month's payment is freed too, which can bring a date sooner, by a few months where net worth grows slowly.
  - How it's worked out on Targets says how it's split. The Projection and Retirement show what you invest now and don't count loans ending, as before.
- **The yearly surplus slider** splits sea blue (cash) and pine green (investments).
- **Fixes:**
  - A loan whose payment fits its balance exactly (€1,199.88 at €99.99 a month) showed its payoff one month late, from rounding.
  - A cash target's "+€X/mo would make it" could be too high with inflation on: it only checked the deadline month, though the goal can be easier to reach earlier, before prices rise further. It's now the least that reaches the goal by the deadline, as for the other targets.
  - With a shortfall, How it's worked out on Targets now says that a paid-off loan's payment covers the shortfall first.
- **No zoom on iPhones and iPads.** Fields use 16px text on touch screens, so an iPhone (upright or sideways) or an iPad no longer zooms the page in when you tap one.
- The README screenshots show the new look and the new card.
- Tests check Your path month by month against a separate model (pensions, investments, cash, loans and inflation), that its dates match the Targets card, the zoom buttons, the hover values, Estonian, and phone and wide-screen widths.

Saved data and backups from earlier versions keep working. A backup from this version opened in an older one loads fine; only Your path's renamed title is left out, since that card doesn't exist there.

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

[1.3.1]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.3.1
[1.3.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.3.0
[1.2.2]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.2.2
[1.2.1]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.2.1
[1.2.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.2.0
[1.1.7]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.7
[1.1.6]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.6
[1.1.5]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.5
[1.1.4]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.4
[1.1.3]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.3
[1.1.2]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.2
[1.1.1]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.1
[1.1.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.1.0
[1.0.0]: https://github.com/UnauthenticatedUser/Finance-Planner/releases/tag/v1.0.0
