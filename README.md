# Hockey Analytics Website

This project is a personal hockey data website built using primarily Python, HTML, and CSS.

Homepage site preview:

![Site preview](static/images/homepage4.png)

## Goals

- 📊 Static blog-style analysis of NHL teams, players, games, and historical trends
- 🖥  Live game dashboards using the NHL API that track the "shape of the game" with my novel metrics of Depth, Physicality, Defensive Success, etc.
- 📁 Separate pages for:
	- Blog Posts (static analyses)
	- Live Dashboards
	- Team and player stat lookups
	- About me

## Status

As of 08/17/2026 this project is in very early development. I have the bare bones structure stood up for my deep dive posts. I'm beginning to play around with bringing in live data from the NHL api for my dashboarding. Would like to continue writing the deep dives I have planned, but then also starting the dashboarding build out.

I'm beginning to think about database management. Right now there is no database structure in place but I'm going to need to have this--what happens if someone wants to look at yesterdays games? Or games from earlier in the season? So I'm going to need a place to store all this json so people can see static snapshots of previous games. I did not expect this project to start simply with data science, morph into learning front and back end web development, and then start to touch on data engineering lol.

## Tech Stack (Planned)

- Python for backend code and data analysis. Maybe some R if it plays nicely together  (FastAPI for backend)
- HTML/CSS/JS for front end (Jinja2).

## To-Do and Working History

Website launch. Right now (July 1, 2025) I'm thinking I will launch and make live when I have:
- [ ] Five blog posts:
    - [ ] Demographics over time
    - [ ] Total Depth Index (TDI)
    - [ ] Career tenure over time?
    - [ ] Quantifying generational talent vs everyone else?
    - [ ] TBD
- [ ] Two Dashboards
    - [ ] Live in game TDI
    - [ ] Historical player level shot heatmap explorer
	
### Sept. 22, 2025 - Turn the dashboards live
- [ ] Change functions from static and historical to live

### July 31, 2025 - Standup some content
- [ ] Optimize backend for scalability
	- [X] Break up main.py into separate routing files
	- [X] Create a single generic deep dive router
	- [ ] Add in meta for Google Analytics
	- [ ] Add in meta tags for later searching
	- [X] Add level 1 folder called data (e.g., /data/deep_dive_1/data.csv)
	- [X] Add level 1 folder called scripts (e.g., /scripts/deep_dive_1/1.Pull_data.py)
- [ ] Fix Front end for recurring new static analyses
	- [X] Build a deep dive html template
	- [X] Get markdown rolling for content writing that knits to custom styled html
	- [ ] Generalize style.css
- [ ] Add links to about page with icons 
	- Github, personal site, linkedin, google scholar
- [ ] Stylize Today's Games with cards
	
### July 1, 2025 - Standup some content
- [X] Happy Canada Day!
- [ ] Build one static blog post in the blog page
	- [ ] My historical analysis weight, height, age, and country composition
- [X] Connect it to the NHL API for live dashboarding
	- [X] This will be just a test, but pull a schedule with a list of the days games

### June 27, 2025 - Design Work

- [X] Build the button for the landing cards
- [X] Build the button for the blog cards
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
	- [X] Blog page
	- [X] Dashboard page
- [X] Add placeholder HTML frontend pages
    - [X] Landing page
	- [X] About page
	- [X] Blog page
	- [X] Dashboard page

## Author

Dylan Wiwad
