# What the 2026-27 travel numbers actually say

Companion to the eight figures in `figures/`. Every number here comes out of
`3_figures.py`; nothing is quoted from memory.

---

## The story in one paragraph

Measured the way travel is usually measured — total miles — the 2026-27 schedule
looks close to fair. The Gini coefficient across the 32 teams is **0.076**, which
on any normal reading of that statistic means "essentially equal." That reading
is wrong, and it is wrong for a specific reason: mileage has a floor. The
least-travelled team in the league still flies 50,801 km, and Gini is built to
measure quantities that can approach zero. It flatters anything with a high
floor. Once you look at the parts of the schedule that *don't* have a floor —
back-to-backs that require changing cities, three-games-in-four-nights,
arriving to face a rested opponent — the inequality is two to three times
larger. And here is the twist: those burdens fall **hardest on the teams that
fly the least**. Pittsburgh flies fewer kilometres than any team in the league
and draws the most rested opponents of any team in the league. The schedule
appears to trade miles against calendar cruelty, which means a mileage-only
table doesn't just understate the inequality — it points at the wrong teams.

---

## How to talk about the Travel Burden Index

The index is in standard deviations, which is precise and completely
unintuitive. Three ways to make +0.83 and −0.67 mean something.

### 1. Translate the gap into things a person can picture

Utah (+0.83, 1st) against Montreal (−0.67, 32nd) over the same 84 games:

| | Utah | Montreal | Utah's extra |
|---|---:|---:|---:|
| Kilometres flown | 76,975 | 63,477 | **+13,498 km** |
| Time-zone hours crossed | 47 | 24 | **+23 h** |
| Of those, eastward (the hard direction) | 24 | 12 | **+12 h** |
| Three-games-in-four-nights | 15 | 8 | **+7** |
| Back-to-backs needing a new city | 10 | 6 | **+4** |
| Longest single road trip | 14 days | 8 days | **+6 days** |
| Days on the road | 66 | 67 | −1 |
| Games facing a rested opponent | 22 | 22 | 0 |

The usable lines:

> Utah flies **13,498 km more than Montreal** — four extra one-way
> Toronto-to-Vancouver flights, on top of everything Montreal already does.

> Utah crosses **almost exactly twice** Montreal's time-zone hours: 47 to 24.

> Utah spends roughly **20 more hours in the air** — two and a half working
> days, seat-belt on. *(Rough: distance ÷ 750 km/h cruise, plus 36 min per
> flight for taxi, climb and descent.)*

> They are on the road the same number of days. Utah's are just harder days.

That last line is the one worth keeping. The two teams are away from home for
the same amount of time — 66 nights against 67. Everything separating them is
about *what happens* during those nights.

### 2. Frame the index as "how many ways did your schedule hurt you?"

The index averages five pillars: distance, days away, time zones, tight games,
rest deficit. Counting how many a team is worse than league average on:

- **Utah is worse than average on all five** — one of only three teams in the
  league that are (with San Jose and Anaheim).
- **Montreal is worse than average on one** (rest deficit, and barely).
- **Detroit, 31st, is worse than average on none of them.**

So: "+0.83 means Utah drew a losing hand in every one of the five ways an NHL
schedule can be hard — only two other teams did. −0.67 means Montreal drew a
winning hand in four of them."

Worth keeping straight: being worse than average on all five is not the same as
being *badly* hurt on all five. Utah's five pillar ranks are 6th, 3rd, 3rd,
16th and 8th — punishing on distance, days away and time zones, unremarkable on
tight games. That distinction is what `fig4` is for.

### 3. Give the unit a scale

One full point of the index is one standard deviation. The whole league fits in
a range of 1.5 points, from +0.83 to −0.67 — so **a tenth of a point is roughly
two places in the standings** of 32. Utah and Montreal are 1.51 points apart,
which is the entire width of the league.

**A caution worth stating out loud:** the index weights all five pillars
equally. That is a choice, not a discovery, and it is the choice that puts
Buffalo 11th and Pittsburgh 12th despite them ranking 31st and 32nd in
distance. A reader who thinks miles matter more than back-to-backs will
reasonably rank the league differently. That is why `fig4` exists.

---

## Figure by figure

### fig1 — the Travel Burden Index ranking

**Utah, San Jose and Los Angeles draw the hardest travel; Montreal, Detroit and
Carolina the easiest.**

The colour coding does most of the argument: the top ten is eight Pacific and
Central teams, the bottom ten is almost entirely Atlantic and Metropolitan. But
two bars break the pattern and they are the interesting ones — **Buffalo (11th)
and Pittsburgh (12th)**, who fly less than anyone in the league. They are there
entirely on calendar burden. Point at them; they are the thread the rest of the
piece pulls.

Use the Utah/Montreal table above here.

### fig2 — total distance flown

**Vegas 82,086 km; Pittsburgh 50,801 km. The longest schedule flies 62% farther
than the shortest.**

Anchors:

> Vegas flies **twice around the equator** (2.05×) over one regular season.
> Pittsburgh manages 1.27 times around.

> The gap between them, 31,285 km, is **78% of the way around the Earth** —
> about 40 extra hours in the air.

> Per game: Vegas averages **977 km of travel per game**, Pittsburgh 605.

Note the shape of the bars: no cliff, no outliers, a smooth ramp. That smooth
ramp is exactly why the Gini comes out low, and it is why the next figure
matters.

### fig3 — the Lorenz curve

**Gini = 0.076.** The curve is nearly the diagonal.

> The lightest-travelling half of the league flies **44% of the league's total
> distance**. If travel were split perfectly evenly it would be 50%.

For scale: a Gini of 0.076 is far below any national income distribution ever
measured. Read literally, this figure says NHL travel is one of the most
equally distributed quantities you will encounter.

**Do not let it say that.** This is the figure to argue *with*, and the "Gini
problem" section below is the argument. Present it as the finding a reasonable
analyst would stop at — and then keep going.

### fig4 — the five pillars, taken apart

**No team draws the worst of everything.** This is the load-bearing figure.

The extremes on each pillar barely overlap:

| Pillar | Hardest three | Easiest three |
|---|---|---|
| Distance | VGK, COL, WPG | PIT, BUF, PHI |
| Days away | TOR, CGY, UTA | NYR, BOS, NJD |
| Time zones | VGK, COL, UTA | OTT, PIT, MTL |
| Tight games | SEA, BUF, PIT | MTL, VAN, CGY |
| Rest deficit | PIT, NYR, BUF | TBL, CGY, TOR |

Individual rows tell the story better than any summary:

- **Vegas** is 1st in distance and 1st in time zones — and 29th in tight games,
  27th in rest deficit. The league flies them everywhere and then gives them
  time to recover.
- **Pittsburgh** is the exact inverse: **32nd in distance, 31st in time zones,
  but 3rd in tight games and 1st in rest deficit.** Nobody flies less;
  nobody more often shows up to face a fresher opponent.
- **Tampa Bay** is 8th in distance and 5th in tight games but **32nd — dead
  last — in rest deficit**, which is why the composite drops them to 28th.
- **Detroit** is between 20th and 27th on all five. Their schedule is
  aggressively unremarkable.
- **San Jose** ranks 2nd overall without leading a single category. Their worst
  pillar rank is 12th; they are the most *evenly* burdened team in the league,
  and no team has all five ranks inside the top 12.

The takeaway sentence: **the schedule does not hand out hardship in a bundle.
It hands out different hardships to different teams, which is exactly why a
single-number ranking of "who travels most" misleads.**

### fig5 — within-team lumpiness

**The Islanders' travel is the most concentrated; Winnipeg's the most evenly
spread.**

This ranking measures *variance*, not burden, and it runs almost backwards to
distance (Spearman −0.62). The mechanism is not mysterious:

| | NYI | WPG |
|---|---:|---:|
| Weekly Gini | 0.521 | 0.256 |
| Weeks under 500 km | 6 of 28 | 1 of 28 |
| Median week | 1,157 km | 2,787 km |
| Busiest week | 8,218 km | 6,878 km |
| Season total | 59,207 km | 80,015 km |

> The Islanders' typical week is a bus ride. Then once or twice a season the
> floor drops out and they fly 8,000 km in seven days. Winnipeg never has an
> easy week and never has a catastrophic one.

Whether concentrated travel is worse than evenly-spread travel is a real
sports-science question and this analysis does not answer it. Present it as a
different axis, not a second opinion on the same one — otherwise a reader will
see the Islanders at #1 here and #24 on the burden index and conclude one of
the two is broken.

### fig6 — cumulative travel through the season

**The three heaviest and three lightest schedules separate by week three and
never cross again.**

But do not over-read it. Across all 32 teams, early-season position is a weak
predictor of where a team finishes:

| Cumulative km at… | correlation with season total |
|---|---:|
| Week 2 | 0.58 |
| Week 4 | 0.65 |
| Week 6 | 0.47 |
| Week 12 | 0.79 |
| Week 20 | 0.93 |

The average team moves **6.2 places** between its week-4 ranking and its final
one. Carolina goes 12th → 28th; Dallas goes 21st → 5th. The extremes declare
themselves immediately; the middle 26 teams are a coin flip until Christmas.

### fig7 — how much is just geography

**η² = 0.64. Division explains 64% of the variance in distance flown**
(F(3,28) = 16.6, p = 2×10⁻⁶).

> Western teams fly **23% farther** than Eastern ones on average — 74,591 km
> against 60,792.

> **Every single Pacific team flies farther than every single Metropolitan
> team.** Not on average. Every one, without exception.

This is the figure that reframes the whole exercise. Most of what looks like
scheduling inequality was decided when the franchises were placed on the map.
It is not something the league can schedule its way out of, and it is not
evidence of anyone being treated unfairly — it is evidence that Anaheim is a
long way from Boston.

Which makes the remaining 36% the interesting part, and the next figure is
where it lives.

### fig8 — tight turnarounds against rest

**Buffalo and Pittsburgh fly the least and still get the worst of the
calendar.**

League average is 10.1 travel back-to-backs and 20.8 games against a
better-rested opponent. Splitting the league on both:

- **Worse than average on both:** BOS, BUF, NJD, NYI, OTT, PIT, SEA — average
  distance rank **25th**.
- **Better than average on both:** CGY, CHI, COL, EDM, MIN, TOR, VGK — average
  distance rank **11th**.

That is the whole argument in two lines. **The teams handed the worst calendar
are, on average, the teams that fly the least — and vice versa.** The
correlation between calendar burden and distance is **−0.42**.

Pittsburgh is the extreme case: last in the league in distance, and **29 of
their 84 games** are started against an opponent who has had more rest. Vegas,
who fly farther than anyone, face that in only 18.

---

## The Gini problem — the actual finding

This is the part worth writing up carefully, because it is where the obvious
answer and the correct answer diverge.

### Gini is the wrong tool for a quantity with a floor

Gini measures how unequally a total is *shared*. It was built for income, where
the bottom of the distribution can approach zero and the top can run away. NHL
travel has neither property. Every team must play 42 road games; the minimum
possible season is not far below what Pittsburgh actually flies. When the floor
is 62% of the ceiling, Gini is compressed toward zero by construction, and it
will report "equality" for almost any schedule the league could plausibly write.

One way to see the size of the effect: recompute the Gini on each team's
distance **above the least-travelled team's** — i.e. on the part of the
schedule that was actually variable rather than mandatory.

| | Gini as measured | Gini of the excess above the floor |
|---|---:|---:|
| Distance flown | 0.076 | **0.305** |
| Days on the road | 0.037 | **0.283** |
| Flights taken | 0.053 | **0.319** |
| Time-zone hours | 0.163 | **0.389** |

Four times larger. *(This is an illustration, not a standard estimator —
subtracting the sample minimum forces the lightest team to exactly zero. It
shows what the headline Gini is hiding; it is not a replacement for it.)*

### Compare metrics instead of trusting the level

The more defensible move is to stop asking "is 0.076 big?" and start asking
"which parts of the schedule are *more* unequal than others?" On that
comparison the ordering is unambiguous, and distance is at the bottom of it:

| Metric | Gini | CV | Max ÷ min |
|---|---:|---:|---:|
| Days on the road | 0.037 | 0.065 | 1.32× |
| Flights taken | 0.053 | 0.094 | 1.43× |
| **Distance flown** | **0.076** | **0.133** | **1.62×** |
| Rest-deficit games | 0.085 | 0.157 | 2.42× |
| Back-to-backs with travel | 0.111 | 0.202 | 2.80× |
| Three-games-in-four | 0.113 | 0.200 | 2.50× |
| Time-zone hours | 0.163 | 0.291 | 2.90× |

**Distance — the one thing everybody measures — is among the most equally
distributed things about an NHL schedule.** The burdens that vary most are the
ones nobody puts in a headline: one team crosses 2.9× the time-zone hours of
another, plays 2.8× as many travel back-to-backs, and starts 2.4× as many games
against a rested opponent.

### And the two are negatively correlated

If distance inequality and calendar inequality lined up, a mileage table would
still rank the league correctly, just with the wrong spacing. They don't line
up. They point in opposite directions (r = −0.42). So a mileage table is not
merely imprecise — **it identifies the wrong victims.**

There are two honest readings of that negative correlation and the piece should
offer both:

1. **Deliberate compensation.** The schedule-maker knows Vegas and Colorado are
   flying enormous distances and protects them with fewer tight turnarounds.
   Under this reading the schedule is *fairer* than the mileage table suggests,
   and the system is working.
2. **A burden that got moved, not removed.** The East's compact geography means
   its teams *can* be given games on consecutive nights in different cities,
   so they are. Under this reading nobody chose to compensate anyone; density
   is simply what inequality looks like when distance isn't available.

The data here cannot separate these — it would take several seasons and some
knowledge of how the schedule is actually built. Say so.

---

## Caveats to keep visible

- **The trans-Atlantic games are excluded.** Including them moves Seattle from
  13th in distance to 1st and from 8th on the index to 1st. That is a defensible
  choice for ranking a normal season, but it is a choice, and Seattle really
  does have to make that flight.
- **The composite's weights are arbitrary.** Five pillars, equal weight. Report
  the pillar ranks (`fig4`) alongside any composite claim.
- **Rest deficit is relative, not absolute.** A team can face rested opponents
  often while being well rested itself. It measures matchup disadvantage.
- **Distance is great-circle, airport to airport.** Real routings are longer,
  charters sometimes use different fields, and no model of who sleeps where is
  going to be right in every case. The return-home rules are documented in
  `README.md` and they are assumptions, not observations.
- **This is schedule structure only.** Nothing here measures whether any of it
  costs teams points. That is a much harder question and a different post.

---

# The maps

Three geographic figures, added after the eight statistical ones. Same data,
same itinerary model — these draw what the bar charts only assert.

## A note on how they're drawn

There is no mapping library in this environment: no cartopy, no geopandas, no
basemap, no shapely, no pyproj. None turned out to be needed. What makes a map
look real is the resolution and layering of the reference data, not the library
that renders it, so `geo.py` pulls Natural Earth's **50m** land, state and
province borders, and lakes — the Great Lakes matter enormously on a map of the
NHL — projects them through a hand-rolled **Albers Equal Area Conic** (29.5°N /
45.5°N standard parallels, the parameters every North America atlas uses), and
draws them with plain matplotlib. The files are cached to `data/` on first run,
exactly like the airport coordinates.

**The curved routes are stylistic, and deliberately so.** A great circle really
does bow north of the straight chord, but Albers is built to flatten precisely
that, so over the continental United States the true curve renders almost
straight. `flight_arc()` keeps the real shape and exaggerates it: the great
circle's own perpendicular deviation is multiplied, with a small half-sine
added so short hops curve visibly too. Endpoints stay exact.

Worth being clear about: **no distance in this project comes from that
function.** Every kilometre quoted anywhere is the exact haversine great-circle
distance in `legs.parquet`, verified to 0.0000% against the interpolated path.
The curve only draws.

## map1-3 — the anatomy of a road trip

Three trips drawn leg by leg, with a timeline strip underneath giving opponent,
distance, rest days and back-to-backs.

**Ottawa, October 27 to November 4, is the worst road trip of the season** —
and that is a measured claim, not a chosen one. Across all 206 trips of three
or more games, standardising distance, kilometres per day, zone-hours, eastward
hours, games per day, back-to-backs and rest-deficit games, Ottawa's ranks
**first, at the 99.5th percentile.** The check runs on every execution of
`4_maps.py` and fails loudly if the data ever stops supporting the title.

| | Value | Percentile among 206 trips |
|---|---:|---:|
| Total distance | 8,402 km | 98.5% |
| Zone-hours | 6 (tied league maximum) | 97.6% |
| Kilometres per day | 934 | 91.3% |
| Eastward hours | 3 | 85.4% |
| Rest-deficit games | 2 | 66.5% |

It is not the longest trip in the league — Los Angeles fly 9,370 km in November
and Toronto 9,090 over Christmas. But both spread that over eleven and thirteen
days. **Ottawa covers 8,402 km in nine**, with a back-to-back Los Angeles does
not have, and finishes by flying Anaheim to Buffalo: 3,531 km and three time
zones east, to play a game, without going home first.

> Vegas, Los Angeles, San Jose, Anaheim, Buffalo. Three zones out, four games
> down the coast in six days, then the whole continent back east in one hop.

The other two are there for contrast rather than as rivals: **Toronto's**
Christmas trip is the longest and crosses the continent twice, but at 699 km a
day it is the gentlest of the three; **Tampa's** March stretch is the most
concentrated in the league at 1,169 km a day, but it is four games, not five,
and one time zone gentler.

## map4 — the three heaviest and three lightest seasons

**Vegas, Colorado and Winnipeg against Philadelphia, Buffalo and Pittsburgh.**
Six panels on one projection and scale.

The picture is the argument: three orange webs spanning a continent, three blue
clusters hugging the northeast. But the numbers underneath say something the
picture alone does not.

| | Heaviest 3 | Lightest 3 | Ratio |
|---|---:|---:|---:|
| Distance flown | 81,031 km | 53,235 km | **1.52×** |
| Flights taken | 50.0 | 45.0 | 1.11× |
| Mean flight length | 1,561 km | 1,103 km | **1.41×** |
| Time-zone hours | 50.3 | 23.3 | **2.16×** |
| Days on the road | 64 | 68 | **0.94×** |

Three things fall out of that table, and they are the useful lines:

> The heavy teams do not fly *more often*. They fly 11% more flights — and 52%
> farther. The difference is leg length, not leg count.

> **They are on the road fewer days than the teams that fly least.** Sixty-four
> against sixty-eight. Vegas is not away from home more than Pittsburgh; Vegas
> covers half again the distance in less time.

> The gap widens the further you get from raw mileage. Distance 1.5×,
> time-zone hours 2.2×.

Individual panels worth pointing at: **Vegas takes the fewest flights of the
six (42) and still flies the farthest**, because almost every one is long.
**Winnipeg** is the odd one out in the top row — its web reaches everywhere, but
its 37 zone-hours are barely more than half of Vegas's 58, because Winnipeg's
distance is mostly north-south and east-west *within* fewer zones.

## map5 — the league's air network

**All 1,535 flights over 400 km, aggregated to city pairs, weighted by how
often each is flown.**

- 31 airports, so **465 possible pairs. 392 of them are actually flown — 84%.**
  The league is very close to a complete graph; almost every city reaches almost
  every other city directly at some point in the season.
- **97 pairs are flown exactly once** all year (25% of them).
- The top 10% of pairs carry **31% of all flights**.
- Busiest routes: **San Jose–Anaheim 24, Vancouver–Calgary 24**, LA–San Jose 20,
  Dallas–St. Louis 18, Denver–Las Vegas 17, Detroit–Newark 17.

The shape tells the story better than the counts. The northeast is a dense
knot — short thick strands between Toronto, Montreal, Ottawa, Buffalo, Boston,
Newark and Philadelphia. The west is long thin filaments. And Florida hangs off
the bottom on a fan of very long single-use routes, which is exactly why Tampa
and Florida rank 8th and 7th in distance despite being Eastern Conference
teams — geography, not scheduling.

Note the two busiest pairs are both *short* ones. The routes flown most often
are the ones that barely count as travel.

## map7 — jet lag as a waveform

**The clock at each night's venue, across the whole season.** Six teams — the
three that cross the most time-zone hours and the three that cross the fewest —
with each team's own zone shaded.

This is the figure for the finding that time-zone hours are the most unequal
thing in the schedule: Gini 0.163 and a 2.9× spread, against 0.076 and 1.6× for
distance.

The six are picked off `tz_crossings`, not by hand. The top three are clean.
The bottom is Ottawa 20, Pittsburgh 22, and then a **five-way tie at 24** —
broken on how many flights actually move the clock, which is what the figure
draws: Montreal 15, Florida 15, Buffalo 16, Philadelphia 17, Carolina 18.
Montreal takes the third slot on the shorter season of the two on 15.

| | Zone-hours | Eastward | Flights that move the clock |
|---|---:|---:|---|
| **Vegas** | 58 | 29 | 31 of 42 — **74%** |
| **Colorado** | 56 | 28 | 44 of 56 — 79% |
| **Utah** | 47 | 24 | 37 of 54 — 69% |
| **Ottawa** | 20 | 10 | 13 of 46 — **28%** |
| **Pittsburgh** | 22 | 11 | 16 of 44 — 36% |
| **Montreal** | 24 | 12 | 15 of 51 — 29% |

> **Three-quarters of Vegas's flights change what time it is. For Ottawa it is
> barely a quarter.**

The two halves of the figure are different *kinds* of picture, and that is the
whole point:

- The top three are **square waves**. Vegas never settles: out to Eastern and
  back to Pacific over and over, all season. Colorado is worse in one respect —
  44 of its 56 flights move the clock, the highest share in the six — because
  Denver sits in Mountain time and nearly everywhere is a change.
- The bottom three are **flat lines with occasional dips**. Ottawa spends the
  season pinned to Eastern with one dramatic plunge to Pacific in late October
  and a second in February. Montreal is flatter still, with stretches of weeks
  where the clock never moves at all.

Utah is the interesting middle case, and worth a sentence on its own: **fewer
total zone-hours than Vegas (47 vs 58) but more zone-changing flights (37 vs
31).** Sitting in the middle of the continent means smaller moves, more often.
Whether many one-hour shifts are easier to absorb than fewer three-hour ones is
a real sports-science question this analysis does not answer — but the two teams
are plainly doing different jobs, and a single zone-hours number hides it.

---

# Part 2 — Calendar burden, and the trade-off

Part 1 measures what the map imposes on a team: distance, time zones, nights
away. This measures what the schedule *chooses* — when the games fall, and who
the team meets when it gets there — and then asks whether the two are related.

They are, strongly and negatively. But the obvious reading of that does not
survive testing, and the figures are built to say so.

## What holds and what doesn't

| Claim | Result | |
|---|---|---|
| Travel and calendar burden trade off | r = −0.587, permutation p = 0.0004 | **holds** |
| The trade-off cancels variance | sd 0.32 observed vs 0.50 if unrelated | **58% cancelled** |
| "The East has a worse calendar" | East +0.22 vs West −0.22, t = 1.70, p = 0.099 | **not significant** |
| Calendar burden is a division effect | η² = 0.14, F = 1.49, **p = 0.24** | **not significant** |
| It's really the Metropolitan division | +0.44 vs Atlantic −0.00, t = 2.02, p = 0.053 | suggestive only |
| The compensation is complete | Combined still West-tilted, p = 0.006 | **incomplete** |

**So this is a team-level trade-off that does not map onto the conference
map, and only partly undoes the geography.** That is a more interesting finding
than the clean east-west story, and it is the one the data supports.

## p2_01 — the calendar burden ranking

**Pittsburgh draws the league's hardest calendar** (+1.61), then Buffalo (+1.35)
and Boston (+0.94). Easiest: Calgary (−1.48), Montreal (−1.27), Toronto (−1.25).

Note the colours refuse to sort. Seattle is 4th hardest and San Jose 7th — both
Pacific. Vegas and Calgary are 29th and 32nd — also Pacific. Unlike the travel
ranking, this one has no geographic pattern to read, which is the point.

## p2_02 — what the calendar burden is made of

Same construction as `fig9`, and the same warning applies: **segments straddle
zero, so the drawn bar is wider than the score.** The dot is the score.

**Pittsburgh is worse than league average on all three components at once** —
back-to-backs in two cities, three-in-fours, and facing a rested opponent. That
is asserted in code, not eyeballed. Most teams are mixed; being uniformly bad on
the calendar is unusual.

## p2_03 — the three components as ranks

The components do not travel together. Seattle is 1st on three-in-fours and 14th
on rest deficit. Vancouver is 32nd on back-to-backs-in-two-cities and 5th on
rest deficit. A single calendar number hides genuinely different schedules,
exactly as the travel pillars did in Part 1.

## p2_04 — calendar burden across the season

The `fig10` construction, and cleaner here: all three components are counts tied
to specific games, so unlike trip length they decompose into weekly increments
exactly. **The curves land precisely on the season score** — asserted.

Zero is league-average pace. Pittsburgh is above it almost from the first week.

## p2_05 — the trade-off itself

**r = −0.587, p = 0.0004**, on the two composites. This is the stronger companion
to `fig11`, which uses raw kilometres and gets r = −0.42. Use whichever matches
the axis you are showing; do not quote one alongside the other's figure.

## p2_06 — the variance cancellation

**The single most important figure in Part 2**, because it is the strongest
statement the data supports.

If two burdens were handed out independently, the variance of their average
would be the average of their variances. It isn't. Observed sd is **0.32**;
independent would be **0.50**. The negative covariance **cancels 58% of the
variance**.

> Travel burden ranges over 2.44 standardised units. Calendar burden ranges over
> 3.09. Average the two and the range collapses — **the combined distribution is
> tighter than either burden that went into it.**

One deliberate choice: this plots the **mean** of the two, not the sum. Both
composites are already means of z-scores, so their mean is on the same scale and
the three strips are honestly comparable. Plotting the sum makes the combined row
look no tighter than its parts even though it is.

## p2_07 — is it a coincidence?

Calendar burdens reshuffled at random across the 32 teams, 20,000 times, against
what the real schedule produced. **p = 0.0004**, fixed seed so the figure
reproduces. With n = 32 this matters: the parametric p-value alone would be
easy to distrust.

## p2_08 — geography, three ways

The figure that carries both the argument and its limits, in one image.

| | η² by division | |
|---|---:|---|
| Travel burden | **0.66** | p < .001 |
| Calendar burden | **0.14** | **p = 0.24, n.s.** |
| Both combined | **0.23** | p = 0.059 |

> **Where a team plays decides its travel. It does not decide its calendar.**

The middle panel is the honest one. There is a visible tilt — Metropolitan +0.44,
Pacific −0.28 — but with eight teams per division it does not clear
significance, and the figure says `n.s.` on its face rather than letting a
reader infer a pattern that isn't there.

## p2_09 — who has it worst once both count

**The trade-off narrows the gap but does not close it.** Combined burden: West
+0.15, East −0.15, **t = −2.99, p = 0.006**. The compensation is real and
incomplete.

Important: this combined score is **not** the Travel Burden Index from Part 1.
It weights travel and calendar evenly; the TBI is 3:2 across its pillars and
also counts trip length. They correlate at Spearman 0.886 and differ by a mean
of 3.4 places — Vancouver moves 10. Say which one you are quoting.

## p2_10 — which parts of the calendar drive it

| Component | vs distance | |
|---|---:|---|
| All back-to-backs | **r = −0.54** | p = 0.001 |
| Back-to-backs in two cities | **r = −0.40** | p = 0.022 |
| Facing a rested opponent | r = −0.28 | n.s. |
| Three games in four nights | r = −0.24 | n.s. |

**Back-to-backs are the mechanism.** The other two components point the same way
but neither is significant alone. This also suggests the plainest reading of the
whole trade-off: Eastern cities are close enough together that games on
consecutive nights in different cities are *physically possible* for them, so
they get them. Western teams can't be scheduled that way.

Which is worth saying plainly, because it changes the moral. The pattern may not
be the league compensating anyone. It may just be what inequality looks like
when the geography won't allow the other kind.
