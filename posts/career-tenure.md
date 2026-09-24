---
title: "Career Tenure Over the History of the NHL"
short_title: NHL Career Tenure | Hockey Decoded"
date: "2026-09-24"
image: "/static/images/deep-dives/career-tenure/fig21_senior_share_by_season.png"
tag: "Historical"
summary: An exploration of how team demographic makeups predict winning in the NHL.
description: ""
keywords: "NHL statistics, hockey analytics, demographics, tenure, star players, generational talent, hockey data analysis, sports analytics"
data_source: "NHL API"
published: true
---

Youth or experience? Whether the former, the latter, or some combination of the two is the key to success in the NHL is a constant topic of discussion. Some say the youth come out fast and strong but then fade and succumb to the veterans<sup>(<a href="https://www.facebook.com/watch/?v=1283309993993183" target="_blank" rel="noopener noreferrer">1</a>)</sup> as a game or playoff series drags on. Some say that the youth wins, but they need the veterans to guide them.<sup>(<a href="https://www.nhl.com/news/topic/playoffs/anaheim-ducks-youth-leaning-on-veterans-during-playoff-run" target="_blank" rel="noopener noreferrer">2</a>)</sup> In the NHL, as in life, the answer is rarely black and white. For this deep dive, I’m a bit less interested in just straight age. A lot of ink has been used to explore aging curves in the NHL; analyses to try and understand when a player will peak or to predict their future performance.<sup>(<a href="https://www.sfu.ca/~tswartz/papers/aging.pdf" target="_blank" rel="noopener noreferrer">3, </a></sup><sup><a href="https://sci-hub.ru/10.1515/jqas-2013-0085" target="_blank" rel="noopener noreferrer">4</a>)</sup> I think this is an interesting and worthwhile endeavour, but I am more interested in exploring what this means at the team and league level, and how tenure in the NHL has changed over time.


Therefore, I’m more interested in youth vs. experience as measured by seasons in the NHL. Of course, age and seasons players are pretty highly correlated (r = .83 within team-seasons); if you’re a rookie you’re probably younger. I think years of experience, however, captures what we’re really talking about when we’re pitting veterans against youth. Someone who is 25 could be a veteran if they debuted at 18, or a rookie if they debuted at 24. Of course we need to take into consideration how aging affects the body and one’s athletic ability. Older athletes are going to be slower, have less stamina, etc. But again, when thinking about this at the team and league level, I think there are questions to be answered that are less about predicting the performance of an individual player, and understanding the balance between the vigor of youth and the wisdom of experience. Given that, we’re going to look at how the league has trended over the course of its entire history and how that relates to winning. I have also done some analyses on how individual careers have trended, and whether there are some interesting nuances for the superstars compared to the NHL rank-and-file (spoiler: there are!), but this is getting long so I’m gonna save that for part II.

## Tenure breakdown over the entire history of the NHL 

One thing we can be certain of right now is that the NHL has experienced a mix-shift in its distribution of experience. In particular, the NHL now leans more on experience, and less on rookies, than any other point in its history. This implies, in a way, that the wisdom of crowds thinks that veterans are more important than rookies. Of course, though, it could also just mean that the nutrition and training have advanced to the point of allowing guys to stay in the league longer.

![Career Tenure](/static/images/deep-dives/career-tenure/fig1_experience_mix.png)

The share of straight rookies, players in the first ever NHL season, has declined from 23% in the 1940s and 1950s to just 12% in the 2025-2026 season. Further, the proportion  of the league that is made up of players in their 10th season or later season has also grown to a historic high of 31%. Effectively, the league has never been made up of a greater proportion of veterans.

![Career Tenure](/static/images/deep-dives/career-tenure/fig21_senior_share_by_season.png)

This trend of the league leaning on increasing tenure is interesting because by and large within players, careers are not actually getting longer. The median NHL career has hovered around 5 seasons for the last 70 years. So it’s not really simply that the league is trending older now simply because careers are able to be longer now. It’s also not that entry into the league is skewing younger, allowing for longer careers. The average rookie age has hovered around 22 for almost the entire history of the NHL (interquartile range of 20.5 - 23.5 from 1950 to 2025).

![Career Tenure](/static/images/deep-dives/career-tenure/fig3_career_length_by_cohort.png)

So if careers aren't getting longer, how is the league getting older? Part of the answer is just that the league lets in fewer new players, relative to its size, than it used to. In the 1970s about one in five players each season was a rookie; today it's closer to one in eight. The NHL has more than doubled in size since then, but the number of players debuting each year has grown by only a third, and has barely changed since the 1980s. A league that isn't shrinking has to lose players at roughly the rate it adds them, so fewer players coming in means fewer going out. The ones who stay behind are, on average, further into their careers.

![Career Tenure](/static/images/deep-dives/career-tenure/fig33_flows_vs_league_size.png)

The other part, though, is who is leaving. As you can see below, rookies wash out at about the same rate they always have: roughly one in five doesn't come back for a second season. What has changed is the other end. In the mid-2000s about a quarter of players in their tenth season or later left the league each year; today it's closer to one in six. So we can see that  typical careers haven’t gotten any longer, but the long careers have gotten longer. Veterans are hanging on longer than they have in 20 years, and that's enough to raise the veteran share of the league without moving the median at all.

![Career Tenure](/static/images/deep-dives/career-tenure/fig39_exit_rate_by_tenure.png)

So what we're seeing is a coherent pattern. By at least one reasonable definition, the league is more veteran-heavy than at any point in its history, and getting in has become harder: rookies were a fifth of the NHL in the 1970s and are about an eighth now. The typical career isn't longer, but the players who do establish themselves are sticking around longer than they have in a generation.

## So, is experience the move to win then?

At first blush, it does appear like having a more tenured team leads to more success. Looking at a simple regression of win rate by tenure from 2010 to 2026, we see that every year of extra experience a team has is associated with a 2.3 percentage point bump in win probability. That is, a team that is on average 3 years younger (in terms of tenure) than its opponent has roughly a 40% chance of winning against its 3-years-older opponent’s 60%.

![Career Tenure](/static/images/deep-dives/career-tenure/fig19_win_rate_by_experience_gap.png)

Now, you wouldn’t want to go make bets on this (I looked - betting on tenure alone over the last 15 years wins 53.6% of the time, compared to just simply betting on the team that had a better record at the time of the matchup winning 59.5% of the time). But tenure does seem to have a small effect. As you can see above, if there is a mismatch in the regular season, the more tenured team will win a bit more often. But what about cups? Turns out, not really. 

![Career Tenure](/static/images/deep-dives/career-tenure/fig37_finals_winner_vs_loser.png)

Once you get into the playoffs, and make it to the Stanley cup final, tenure doesn’t really have an effect. The more tenured squad only won the cup 57% of the time. So better than a coin toss, but nothing crazy. Of course, the obvious thing to look at is just making the playoffs from the hop. Maybe the more tenured teams in the league overall are the ones making it to the end so it’s masking the effect of tenure. And, as it turns out, there is some truth to that.

![Career Tenure](/static/images/deep-dives/career-tenure/fig36_experience_by_postseason_outcome.png)

Experience relative to the league average doesn’t really help you win or make it to the finals (the top two dots), but it does help you make the playoffs to begin with. As you can see looking at the bottom dot, teams who missed the playoffs were, on average, less experienced than the league as a whole. Looking since 1991, the average tenure of teams who missed the playoffs was about half a season lower than those who made the playoffs, and almost a whole season lower than the teams who won the whole thing.

## So what?

So where does that leave us? The NHL has never leaned harder on experience. Nearly a third of the league is in its tenth season or later, and barely one in eight is a rookie. But almost none of that is about the players. Rookies aren't arriving younger. Careers aren't longer, on the whole, than they were in 1960. But we do see that the long careers are getting longer; players in their tenth-plus season are leaving the league at a lower rate than previous generations. 

And experience does look like it matters, to a degree. More tenured teams win more games. They make the playoffs more often: teams that missed the playoffs were half a season less experienced than the teams that made them, and nearly a full season behind the eventual champion, in terms of experience. But, once you get to the final, and we’re seeing more tenured teams make it there more, the actual outcome is somewhat of a coin flip.

There are some interesting patterns with the length of careers for stars vs the typical player, and how production increases and then drops off as careers go on for these different groups. This post has gotten unwieldy though, so that will be for the next one! 

<div style="text-align:center; margin-top: 2rem;">
  <button class="card-button">
    <a href="/static/rendered/career_tenure.html" target="_blank" rel="noopener noreferrer">
      View Code, Data, & Extra Analysis
    </a>
  </button>
</div>
