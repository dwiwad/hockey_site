import pandas as pd
import s3fs

s3 = s3fs.S3FileSystem(anon=False)
df = pd.read_parquet('s3://hockey-decoded/depth_scores/depth_scores.parquet', filesystem=s3)

print(df.columns.tolist())
print(f"Total rows: {len(df)}")

season_prefix = "202502"  # 2025-26 regular season
df_season = df[df['game_id'].astype(str).str.startswith(season_prefix)].copy()

print(f"Rows: {len(df_season)}")
print(f"Games: {df_season['game_id'].nunique()}")
df_season.head(4)


season_prefix = "202502"
df_season = df[df['game_id'].astype(str).str.startswith(season_prefix)].copy()

# Calculate GSAx (goals saved above expected) for each team
df_season['gsax'] = df_season['opponent_total_xg'] - df_season['opponent_goals']

# For each game, we need to pair teams to get opponent's TDI and GSAx
game_data = []

for game_id in df_season['game_id'].unique():
    game = df_season[df_season['game_id'] == game_id]
    if len(game) != 2:
        continue

    for _, row in game.iterrows():
        opp = game[game['team_abbrev'] != row['team_abbrev']].iloc[0]

        game_data.append({
            'game_id': game_id,
            'game_date': row['game_date'],
            'team_abbrev': row['team_abbrev'],
            'opponent_abbrev': row['opponent_abbrev'],
            'depth_adv': row['tdi'] - opp['tdi'],
            'goalie_adv': row['gsax'] - opp['gsax']
        })

df_walks = pd.DataFrame(game_data)
# Sort by team and date first
df_walks = df_walks.sort_values(['team_abbrev', 'game_date'])

# Add game number per team
df_walks['game_num'] = df_walks.groupby('team_abbrev').cumcount() + 1

# Cumulative average (expanding mean)
df_walks['depth_adv_cum'] = df_walks.groupby('team_abbrev')['depth_adv'].expanding().mean().reset_index(level=0, drop=True)
df_walks['goalie_adv_cum'] = df_walks.groupby('team_abbrev')['goalie_adv'].expanding().mean().reset_index(level=0, drop=True)

df_walks.head(10)

import plotly.graph_objects as go

TEAM_COLORS = {
      'ANA': '#D9614B',
      'ARI': '#945057',
      'BOS': '#E6C760',
      'BUF': '#3A4F73',
      'CGY': '#CF5D65',
      'CAR': '#3D3D3D',
      'CHI': '#D05160',
      'COL': '#9A5161',
      'CBJ': '#3A4B6F',
      'DAL': '#3D7A6C',
      'DET': '#D54E54',
      'EDM': '#E76F2B',
      'FLA': '#C59F40',
      'LAK': '#B5BDC0',
      'MTL': '#B55560',
      'MIN': '#3D735E',
      'NSH': '#E6C560',
      'NYR': '#4378B0',
      'NYI': '#3D68A3',
      'NJD': '#CF5D65',
      'OTT': '#D2546A',
      'PHI': '#E08363',
      'PIT': '#E6BD50',
      'SJS': '#3D8896',
      'STL': '#3D7ABD',
      'TBL': '#3D5C8C',
      'TOR': '#3D5B88',
      'VAN': '#3A567E',
      'WSH': '#C14E5C',
      'WPG': '#3A4F73',
      'VGK': '#9A8968',
      'SEA': '#A1DBDB',
      'UTA': '#8AB9E8'
  }

# Get all teams
teams = sorted(df_walks['team_abbrev'].unique())

fig = go.Figure()

# Add a trace for each team (only first one visible initially)
for i, team in enumerate(teams):
    team_walk = df_walks[df_walks['team_abbrev'] == team]
    team_color = TEAM_COLORS.get(team, '#E76F2B')
    last_point = team_walk.iloc[[-1]]
    
    fig.add_trace(go.Scatter(
        x=team_walk['depth_adv_cum'],
        y=team_walk['goalie_adv_cum'],
        mode='lines+markers',
        marker=dict(size=8, 
                    color=team_walk['game_num'],
                    colorscale=[[0, '#3B4B64'], [1, team_color]], 
                    showscale=(i==0)),
        line=dict(width=1, color='gray'),
        text=team_walk['game_num'],
        hovertemplate='Game %{text}<br>Depth: %{x:.3f}<br>Goalie: %{y:.3f}<extra></extra>',
        visible=(i == 0),  # Only first team visible
        name=team
    ))
    
    fig.add_trace(go.Scatter(
         x=last_point['depth_adv_cum'],
         y=last_point['goalie_adv_cum'],
         mode='markers',
         marker=dict(size=10, color='#2ECC71', line=dict(width=2, color='white')),
         hovertemplate=f'{team} Current<br>Depth: %{{x:.3f}}<br>Goalie: %{{y:.3f}}<extra></extra>',
         visible=(i == 0),
         showlegend=False
     ))

# Quadrant lines
fig.add_hline(y=0, line_dash="dash", line_width=1, line_color="black")
fig.add_vline(x=0, line_dash="dash", line_width=1, line_color="black")

# Create dropdown buttons
buttons = []
for i, team in enumerate(teams):
    visibility = [False] * (len(teams) * 2)  # 2 traces per team
    visibility[i * 2] = True      # Walk line
    visibility[i * 2 + 1] = True  # Current dot
    buttons.append(dict(
        label=team,
        method='update',
        args=[{'visible': visibility}]
    ))    

fig.update_layout(
    title=dict(
        text="Team Season Walk: Depth vs Goaltending (2025-26)",
        font=dict(
            family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
            size=24,
            color="#041E42"
        ),
        x=0.05,
        xanchor='left'
    ),
    xaxis=dict(
        title="Cumulative Depth Advantage",
        title_font=dict(size=16),
        range=[-3, 3],
        showgrid=True,
        gridcolor='#e0e0e0',
        zeroline=False,
        tickfont=dict(
            family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
            size=12,
            color="#041E42"
        )
    ),
    yaxis=dict(
        title="Cumulative Goalie Advantage",
        title_font=dict(size=16),
        range=[-2, 2],
        showgrid=True,
        gridcolor='#e0e0e0',
        zeroline=False,
        tickfont=dict(
            family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
            size=12,
            color="#041E42"
        )
    ),
    updatemenus=[dict(
        active=0,
        buttons=buttons,
        x=0.98,
        xanchor='right',
        y=1.15,
        yanchor='top',
        bgcolor='white',
        bordercolor='#041E42'
    )],
    height=600,
    width=800,
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(
        family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
        color="#041E42"
    )
)

fig.write_html("/Users/dwiwad/desktop/team_walk.html")
