---
title: "How have player demographics changed over the history of the league?"
short_title: "Player Demographics | Hockey Decoded"
date: "2025-07-14"
image: ""
data_source: "NHL API"
---

The shape of the NHL has changed quite drastically over the last 100 years. When
the league first started in 1917 forward passing was not allowed, the top players
played almost sixty minutes a game, and goalies were not allowed to drop to the
ice to save a puck. Even more: goalies served their own penalties, forcing their
team to defend an empty net!<sup>(<a href="https://www.nytimes.com/2017/12/15/sports/hockey/nhl-centennial-goalie-rules.html" target="_blank" rel="noopener noreferrer">1</a>)</sup> 


With these changes to the game there has also been changes to the players, with
some things changing drastically, and some remaining surprisingly steady. In this
post I'm going to conduct a deep dive into player demographic data for every single
NHL roster from the 1917-1918 season to the 2024-2025 season.

We'll look at the trends in nationality, age, height, weight across a comprehensive
dataset of every single NHL player on every single NHL roster since 1917. That is,
X,XXX unique players rostered YY,YYY times total across ZZZZ rosters. 

## Nationality: From pure Canada to North American Mix

It makes sense that Canada once dominated the player base of the NHL. After all,
the NHL sprung into existence in 1917 after the dissolution of the "National Hockey
Association of Canada" (NHA) which was centered entirely in Ontario and Quebec.<sup>(<a href="https://www.nhl.com/history/a-brief-history-of-the-league" target="_blank" rel="noopener noreferrer">2</a>)</sup> As 
the NHA became the NHL, All five original teams were based in Ontario and Quebec. 
It was only in the 1920s to 1940s that the league expanded into the United States, 
forming what are now known as the "Original Six:" The Boston Bruins, Chicago Blackhawks, Detroit Red Wings,
Montreal Canadiens, New York Rangers, and Toronto Maple Leafs.

As you can see below, Canada once dominated the composition of the NHL with, at
some points, over 95% of players being Canadian. Now, there is an almost even split
with XX% of the NHL being Canadian and YY% being American. One plausible explanation 
simply a decline in Canadian youth hockey infrastructure, coupled with an increase
in American youth hockey infrastructure. While it is not huge, Under-18 participation
in hockey in Canada has declined 17% from 2009 to 2023, while in the US it has risen
14%. This data of course does not go all the way back to the 1970s, where the decline
in Canadian domination began.

![NHL Player Nationality Trends](/static/images/deep-dives/nhl-player-demographics/nhl_player_nationalities_trend.png)

The 1970s, though, is when the NHL experienced its largest expansion, going
from 12 teams (2 Canadian, 10 American) in the 1969-1970 season to 21 teams (6 Canadian, 15 American)
in the 1979-1980 season with the addition of 4 Canadian teams and 5 American. This
steady increase in American teams is one very likely explanation for this mix-shift
in Nationality. The league went from 100% Canadian teams in 1917 to 22% in 2024.
The NHL has just continually expanded without really adding Canadian franchises.

I would also be remiss if I didn't touch on the more international expansion. The
numbers are relatively low for non-North American countries, but still notable with
ZZ% of the league coming from Scandanavia, the Former USSR, and Central Europe more
broadly.

## Age: Fluctuations Tied to the Structure of the League

Since 1917, age has followed a relatively flat, but somewhat interesting trend.
Truthfully, there seem to be a number of interesting things depending on the time
frame you look at.

First, there seems to be a sort of odd sinusoidal trend where, regardless of position,
players hovered around 28 years old in 1917, got progressively younger until about
1950, got older until the mid 1960s, got younger again until the late 1908s, and then
finally have gotten older again and now sort of plateaud. It's worth noting that these 
changes aren't seismic, really ranging only from about24 to 28 years of age. 

![NHL Player Nationality Trends](/static/images/deep-dives/nhl-player-demographics/nhl_age_by_position.png)

I think one possible reason for this cycle is simply how the league expanded and 
changed over the years. The general trend seems to be "expansion = age decline." Interestingly, the shifts in trend seem to track quite closely
with the "eras" of the league.<sup>(<a href="https://en.wikipedia.org/wiki/Timeline_of_the_National_Hockey_League" target="_blank" rel="noopener noreferrer">3</a>)</sup> 
Up until 1942, in the early era, the league fluctuated growing from four to ten teams,
then back down to seven. In this era, the size of the league fluctuated between XX and YY
players; again, more players, lower age.

Following this, 1942 to 1967 the team stayed at 6 teams, the "original six" era. As you
can see, in this era the league slowly aged. No expansion, no injection of new players,
less roster turnover. The league simply aged in place. Then, from 1967 to 1991 the NHL
experienced it's largest expansion era, growing 250% from 6 to 21 teams. In this era,
the league again got younger and younger. From 1991 to 2017 the league again expanded,
but only 30%. Less need for new young players, more static rosters, the league ages again.
Finally, from 2017 until now the league has only added one team, and age has stagnated.

ADD LINES TO THE AGE GRAPH FOR ERAS

NEW GRAPH TEST HYPOTHESIS THAT ROSTER TURNOVER IS HIGHER WHEN AGE IS DECLINING,
AND THEN ROSTERS STAGNATE, THE AGE SLOWLY RISES WITH THE PLAYERS, THEN PEOPLE START
TO RETIRE AND YOUNGER FOLKS COME IN UNDERNEATH, REPEAT CYCLE.

Secondly, the long term trend is that goalies have remained static around 28 years
old while forwards and defencemen have declined from 28 to about 26 years old. I suspect
this long term age change simply reflects the speed and demands of modern athletics.
Goalies can afford to be a hair older, while skaters must deal with the increasing 
demands of the sport and cannot afford to be older. This is a trend we have seen
in numerous sports. Cycling grand tour winners used to be mature in their career,
around 27-28 years old and are now falling more in their mid to early 20s. Athletes are
starting earlier, developing faster, winner sooner, and then retiring around previous
peak ages.

## Height: A Steady Increase and Biological Stagnation

There are again some interesting trends when it comes to how height has changed over the years.
By and large, players have gotten taller, which is not entirely surprising. The average height
of a Canadian man in 1920 was ~171cm. By 2014, this had grown to be ~178cm. This raw 7cm, or 4%,
increase roughly tracks the NHL change of 176 to 187cm, a 6% increase, over the same time period.

So it's not really that the league is getting taller, it's simply most likely that people were
getting taller over the same time period, and the NHL kept up, maybe outpacing the general population
slightly. Naturally, the athletes are a bit taller than the general population overall.

![NHL Player Nationality Trends](/static/images/deep-dives/nhl-player-demographics/nhl_height_by_position.png)

I think what is the most interesting here, though, is the change in positional heights. For almost
the entire history of the NHL, goalies were the smallest position by height (and weight, but more
on that below). However, come the late 1980s and early 1990s this began to shift and goalies' saw
a dramatic rise in their overall height, eventually becoming the tallest players around 2010.

While there are many plausible reasons for this, one that I think rises to the top is implementation
of helmets for goalies with the the shift towards the butterfly, or "profly" style popularized in
the mid 1980s by Patrick Roy.<sup>(<a href="https://en.wikipedia.org/wiki/Butterfly_style" target="_blank" rel="noopener noreferrer">3</a>)</sup>
Goalies were first required to wear masks in 1979-1980, followed quickly by some equipment changes
that made it feasible for a goalie to drop to his knees (masks and more heavily armored chest and arm pads).

Now, instead of relying on their gloves, with an unprotected face, goalies could drop to their knees and
use their whole body to stop the puck. As Patrick Roy came along in the mid 1980s and popularized the style,
it was now the reality that a goalie could be both large AND agile AND use their whole body. Thus, it was
much more effective now to be a large goalie, possibly kicking off the slow and steady height trend we see now.

## Weight: Slow and Steady Rise to an Eventual Decline

There are a few interesting trends with the average weight of NHL players. Overall, there
has been a steady increase from ~175lbs average to a peak of near 205lbs, with now a drop to
slightly below 200lbs average. This trend mirrors the height changes, at least until weight begins to
decline: as players get taller, they get heavier.

![NHL Player Nationality Trends](/static/images/deep-dives/nhl-player-demographics/nhl_weight_by_position.png)

But, similar to the changes in goalie height, there may have been a shift in the last 15 to 20 years that
allows players to be more effective while being lighter.

Interpretation: The bulking era may have crested; teams may now prioritize pace and endurance.

Data Note: Suggestive of shifting fitness norms or training philosophies post-2010s.


Optional Transition Paragraph: What’s Missing or Evolving
Opportunity to Set Up Next Sections:

How do these physical/demographic traits relate to performance or style of play?

Have top lines changed more than bottom six?

Do older, heavier teams fare better in playoffs?

## Conclusion and New Questions

Recap the Big Picture: The NHL has globalized and modernized, but its players’ core age profile hasn’t changed. Height has increased, weight surged then steadied, and Canada’s dominance has waned.

Forward-Looking Thought: As player development evolves and AI/data tools impact scouting, the next frontier may not be physical—it may be cognitive, tactical, or even psychological.