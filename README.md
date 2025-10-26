# Hockey Decoded

This project is a personal hockey data website built using primarily Python, R, HTML, and CSS.

## Site Homepage as of October 2025

![Site preview](static/images/homepage4.png)

## Goals

- 📊 Static deep dive-style analysis of NHL teams, players, games, and historical trends
- 🖥  Live game dashboards using the NHL API that track the "shape of the game" with my novel metrics of Depth, Physicality, Defensive Success, etc.
- 📁 Separate pages for:
	- Deep Dive Posts (static analyses)
	- Live Dashboards
	- Team and player stat lookups
	- About me

## Status

10/14/25; New goal - let's try to have the site live, and the TDI paper under review, by the end of the year!

10/03/2025; Everything is actually pretty far along now. It's really close to what I would consider publishable. I have done a ton of work stylistically and also to have a few blog posts and dashboards stood up. I am currently working on the Total Depth Index. I think once I have a full draft of a whitepaper, and then figure out how to stand up a live in game version of the TDI, it will be ready to launch. At the end of October every team (I think) will have 10 regular season games, which is enough to start calculating a rolling 10 game depth index for dashboard priors. xG will be challenging. But I feel like this has come a LONG way since I stood up an empty website in June.

08/17/2025; This project is in very early development. I have the bare bones structure stood up for my deep dive posts. I'm beginning to play around with bringing in live data from the NHL api for my dashboarding. Would like to continue writing the deep dives I have planned, but then also starting the dashboarding build out.

I'm beginning to think about database management. Right now there is no database structure in place but I'm going to need to have this--what happens if someone wants to look at yesterdays games? Or games from earlier in the season? So I'm going to need a place to store all this json so people can see static snapshots of previous games. I did not expect this project to start simply with data science, morph into learning front and back end web development, and then start to touch on data engineering lol.

## Tech Stack

- Python for backend code and data analysis. Some R for static stuff, but not actual live analysis or dashboarding. I prefer R over python for stats, sue me.
	- Backend is FastAPI
- HTML/CSS/JS for front end (Jinja2).
- Figma for design work

## To-Do

Tech Debt
	- [ ] Clean up style.css; Maybe migrate to separate files.
	- [ ] Generalize depth functions

Website launch. Right now (July 1, 2025) I'm thinking I will launch and make live when I have:
- [ ] Five deep dive posts:
    - [X] Demographics over time
    - [ ] Total Depth Index (TDI)
    - [ ] Career tenure over time
	- [ ] Distances flown by team by season - inequality?
    - [ ] Quantifying generational talent vs everyone else?
    - [ ] TBD
- [ ] Shape of the Game Dashboard
	- [X] Scoreboard
		- [X] Bring in boxscore, clean up router and naming conventions
    - [ ] Live in game TDI 
		- [X] Wire up shot depth
		- [X] Wire up CF depth
		- [X] Wire up TOI depth
		- [X] Wire up xG depth
		- [X] Create the game level table of 10 game depth rolling ave for priors
		- [X] Wire up the live depth table for display - the sem model
			- [X] I'm thinking a dataset for the game that mirrors my analyses dataset, but checks, computes changes, and appends every 15-30 seconds
		- [X] Add new info to the hovers. For shots, X shots from Y players, X CF from Y players, X xG from Y players
		- [ ] Add total depth minute by minute beside the bars on the detail page, a second card. This I can do once the data are stored.
	- [X] Add weighted average decay to fix starting points
	- [X] Fix to pull TOI from the boxscore endpoint, not the shift chart end point!
	- [X] Add priors and weighted decay to the individual depth bars
	- [X] Add small cards to the depth explainer, four side by side like the note, one for each depth metric
- [X] Data Storage - Migrate to S3; this is fine for now.
	- [X] How do I store previous games so people can look at history?
	- [X] S3 migration; reading and writing to s3 instead of locally
		- [X] get_todays_games.py
		- [X] service.py

### Oct. 6, 2025 - More tasks I'm thinking of
- [ ] Look into DuckDB
- [X] Write a shot depth function once rosters are in and replace shot share figure
- [X] Check the math on the depth.py
- [X] Add primary and secondary team colors to css or a python dict
- [ ] For the shape of the game would it be better to have a running line? like moneypuck. I'm finding myself wanting to see how depth balance has evolved over the game...
	- [ ] Like 4 side by side moving line figures. One for each element of depth or each shape of the game element
- [X] Change the shot share/depth bar plot to be away and home team primary colors
- [ ] Start looking into hosting on AWS
- [X] Localize timezone
- [ ] TDI
	- [ ] Start scoping the deep dive
	- [ ] Stand up an empty post for it
- [ ] Season shape once I have more metrics than depth
	- [ ] Add Card under detailed Dashboards header
	- [ ] Add new Page for "Shape of the Season"
	- [ ] Add depth plotly to that page
		- [X] Update plotly hover state
		- [X] Set plotly to auto scale 
- [ ] Get all the old team logos

## Working History - DONE

### Sept. 6, 2025 - Keep on keepin on
- [X] Write the demographics deep dive notebook file
- [X] Total Depth Index
	- [X] Do the ground exploration and analysis to define TDI in last season; Need this for the blog post and dash
	- [X] Pull the data for 2010 to 2025
	- [X] Analyze - Big data is big 😬
- [ ] Find the right icons for about page that are thin in each case
- [X] Live dashboarding
	- [X] Learn how to bring in the live data
	- [X] Bring in a Cache for the main dashboard so it doesn't take so long to load the days games
	- [X] Debug the shot counter for the interim sog dash; tampa gave giving boston game counts for march 13, 2025 test day
		- Damn that was annoying. Turns out I thought I was duplicating a game but just by chance the shot counts for two games were the same
		because I included shootout shots, and didn't line up with the box score because nhl doesn't count shootouts. Just had to filter that out.
	- [X] Start fleshing out the dash page
	- [X] A shot depth balance bar
	- [X] Add Yesterdays games page + date selector; this might require rewriting my game fetcher and router
		- [X] Stylize the date selector
	- [X] Add javascripting to auto-refresh the clock every 5 seconds, builds the base for depth to do the same. (nhl.com updates every 10s)
	- [X] Add javascripting to update goals if the data updates

### Sept. 22, 2025 - Turn the dashboards live
- [X] Change functions from static and historical to live
- [X] Add a meta-tag in the markdown for raw analysis that links to a notebook

### July 31, 2025 - Standup some content
- [X] Optimize backend for scalability
	- [X] Break up main.py into separate routing files
	- [X] Create a single generic deep dive router
	- [X] Add in meta for Google Analytics
	- [X] Add in meta tags for later searching
	- [X] Add level 1 folder called data (e.g., /data/deep_dive_1/data.csv)
	- [X] Add level 1 folder called scripts (e.g., /scripts/deep_dive_1/1.Pull_data.py)
- [X] Fix Front end for recurring new static analyses
	- [X] Build a deep dive html template
	- [X] Get markdown rolling for content writing that knits to custom styled html
- [X] Add links to about page with icons 
	- [X] Github, personal site, linkedin, google scholar
- [X] Stylize Today's Games with cards
 - [X] Cards
 - [X] Team logo images
 - [X] Buttons
 - [X] Do the design on Figma
	
### July 1, 2025 - Standup some content
- [X] Happy Canada Day!
- [X] Build one static deep dive post in the deep dive page
	- [X] My historical analysis weight, height, age, and country composition
- [X] Connect it to the NHL API for live dashboarding
	- [X] This will be just a test, but pull a schedule with a list of the days games

### June 27, 2025 - Design Work

- [X] Build the button for the landing cards
- [X] Build the button for the deep dive cards
- [X] Choose and implement a font
    - Went with Charter for everything for now
- [X] Write and implement the about me page
    - [X] Writing
    - [X] Circular masked photo
- [X] Make it so the nav site title points home

### June 26, 2025 - build the MVP

- [X] Set up the basic website structure backend
    - [X] Landing page
	- [X] About page
	- [X] deep dive page
	- [X] Dashboard page
- [X] Add placeholder HTML frontend pages
    - [X] Landing page
	- [X] About page
	- [X] deep dive page
	- [X] Dashboard page

## Author

Dylan Wiwad
