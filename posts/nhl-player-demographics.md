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
some characteristics changing drastically, and some remaining surprisingly steady. In this
post I'm going to conduct a deep dive into player demographic data for every single
NHL roster from the 1917-1918 season to the 2024-2025 season.

We'll look at the trends in nationality, age, height, weight across a comprehensive
dataset of every single NHL player on every single NHL roster since 1917. That is,
8,595 unique players rostered 55,567 times total across 107 season rosters. 

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
with 40% of the NHL being Canadian and 31% being American. One plausible explanation is
simply a decline in Canadian youth hockey infrastructure, coupled with an increase
in American youth hockey infrastructure. While it is not huge, Under-18 participation
in hockey in Canada has declined 17% from 2009 to 2023, while in the US it has risen
14%.<sup>(<a href="https://apnews.com/article/us-hockey-growth-8e4aacaf752684bcf1e88b2596986973" target="_blank" rel="noopener noreferrer">3</a>)</sup> 
This data of course does not go all the way back to the 1970s, where the decline
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
25% of the league coming from Scandanavia, the Former USSR, and Central Europe more
broadly.

## Age: Fluctuations Tied to the Structure of the League

Since 1917, age has followed a relatively flat, but somewhat interesting trend.
Truthfully, there seem to be a number of interesting things depending on the time
frame you look at.

First, there seems to be a sort of odd sinusoidal trend where, regardless of position,
players hovered around 28 years old in 1917, got progressively younger until about
1950, got older until the mid 1960s, got younger again until the late 1980s, and then
finally have gotten older again and now sort of plateaud. It's worth noting that these 
changes aren't seismic, really ranging only from about 24 to 28 years of age. 

![NHL Player Nationality Trends](/static/images/deep-dives/nhl-player-demographics/nhl_age_by_position.png)

I think one possible reason for this cycle is simply how the league expanded and 
changed over the years. The general trend seems to be "expansion = age decline." Interestingly, the shifts in trend seem to track quite closely
with the "eras" of the league.<sup>(<a href="https://en.wikipedia.org/wiki/Timeline_of_the_National_Hockey_League" target="_blank" rel="noopener noreferrer">4</a>)</sup> 
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
the mid 1980s by Patrick Roy.<sup>(<a href="https://en.wikipedia.org/wiki/Butterfly_style" target="_blank" rel="noopener noreferrer">5</a>)</sup>
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
allows players to be more effective while being lighter. There are a number of possible shifts that all seem
plausible. One big change is likely that development and nutrition have changed. Players are starting younger,
training more effectively, eating better. As a result, the league is getting faster and faster.<sup>(<a href="https://www.nhl.com/news/sunday-long-read-nhl-players-adapting-to-faster-league-with-weight-los-304065402" rel="noopener noreferrer">6</a>)</sup>


Young guys are coming in faster, older guys have to shed some kilos to match the speed and pace, and the league
shrinks. There has also been some suggestion, like in other areas of the player demographics, that a shifting of
the rules of the game have had an effect.<sup>(<a href="https://rezztek.com/blogs/news/evolution-of-hockey-bodies?srsltid=AfmBOopLfh-8o2FBwWkhoUhOCWmAdozKYtwiLfXBq2wEeRqOE2ukrd_l" rel="noopener noreferrer">7</a>)</sup> 

Specifically, there was a large swath of rule changes in the 2005-2006 season, right at the peak of the NHLs size, that
were designed to encourage faster, more aggressive offensive play.<sup>(<a href="https://records.nhl.com/history/historical-rule-changes" rel="noopener noreferrer">8</a>)</sup> 
For example, the league eliminated the two-line pass rule making it such that players could pass from
their defensive zone across the red line, allowing for longer stretch passes, quick transitions, and breakaways.
Additionally, the league reinstated the "tag-up" rule for offides, allowing an offensive player to
simply pop one skate out of the zone and re-enter. This, as opposed to having to fully exit the zone,
come to a stop, and re-enter, allows the game to maintain a faster more aggressive pace.

## Conclusion and New Questions

Over the last hundred-odd years, the league has become more globalized, gotten taller,
gotten lighter, and fluctuated in age. There are a number of plausible reasons for each of these shifts,
ranging from just general population changes, to advancements in nutrition and training, to
simple NHL rule changes that reward different styles of play.

I think this simple analysis of historical trends opens up a lot of interesting analytic windows.
Here, I have simply chronicled these changes in a way that many have before. Moving forward, I think
it would be important to understand the affects of these demographics. The NHL changed the rules to
reward faster more aggressive play; do lighter, younger teams fare better? Goalie pads and playstyles
have changed; do heavier, taller goalies _actually_ perform better? I noted that demographic shifts
happen to coincide with leage expansions; do rosters actually turnover more (i.e., more retiring players,
more new incoming players) in eras of expansion?

There are a ton of open questions that I will continue to explore in these deep dives.


<!--ADD LINES TO THE AGE GRAPH FOR ERAS-->

<!--NEW GRAPH TEST HYPOTHESIS THAT ROSTER TURNOVER IS HIGHER WHEN AGE IS DECLINING,-->
<!--AND THEN ROSTERS STAGNATE, THE AGE SLOWLY RISES WITH THE PLAYERS, THEN PEOPLE START-->
<!--TO RETIRE AND YOUNGER FOLKS COME IN UNDERNEATH, REPEAT CYCLE.-->







