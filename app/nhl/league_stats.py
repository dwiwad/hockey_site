import pandas as pd
import s3fs
import plotly.graph_objects as go
import logging
from app.core.config import get_current_season
from app.core.config import S3_BUCKET

logger = logging.getLogger(__name__)

def get_league_depth_data(season=get_current_season()):
    """
    Get rolling 10-game depth averages for all teams.
    
    Args:
        season: Season in format YYYYZZZZ (e.g., 20242025)
    
    Returns:
        DataFrame with columns: team_abbrev, game_number, weighted_depth_rolling
    """
    # Step 1: Read the master parquet file from S3 and get its metadata
    s3 = s3fs.S3FileSystem(anon=False)
    file_path = f'{S3_BUCKET}/depth_scores/depth_scores.parquet'

    # Get file info (includes last modified time)
    file_info = s3.info(file_path)
    last_modified = file_info['LastModified']  # datetime object

    s3 = s3fs.S3FileSystem(anon=False)
    df = pd.read_parquet(f's3://{file_path}', filesystem=s3)

    # Step 2: Filter to just this season's regular season games
    season_prefix = f"{season}02"
    df_season = df[df['game_id'].astype(str).str.startswith(season_prefix)]

    # Step 3: Sort by team and date so games are in chronological order
    df_season = df_season.sort_values(['team_abbrev', 'game_date'])

    # Step 4: Add game number for each team (1, 2, 3... up to 82)
    df_season['game_number'] = df_season.groupby('team_abbrev').cumcount() + 1

    # Step 5: Calculate 10-game rolling average of weighted_depth
    df_season['weighted_depth_rolling'] = (
        df_season.groupby('team_abbrev')['weighted_depth']
        .transform(lambda x: x.rolling(window=10, min_periods=1).mean()) # Kept at 1 so we can get it for every game, but will stabilize closer to 10
    )

    # Step 6: Keep only rows where we have the rolling average (Which is starting at 1 in this case)
    df_rolling = df_season[df_season['game_number'] >= 1].copy()

    return df_rolling, last_modified

def save_current_rolling_averages(season=get_current_season()):
    """
    Calculate and save current 10-game rolling averages to S3.
    Stores both weighted depth AND the 4 underlying Gini coefficients.
    
    Returns:
        dict: {team_abbrev: {weighted_depth, shot_gini, cf_gini, xg_gini, toi_gini}}
    """
    import s3fs
    import json
    from datetime import datetime

    # Get the rolling averages data
    df_rolling, _ = get_league_depth_data(season=season)

    # Calculate Gini coefficients from depth values
    # Remember: gini = 1 - depth
    df_rolling['shot_gini'] = 1 - df_rolling['sog_depth']
    df_rolling['cf_gini'] = 1 - df_rolling['cf_depth']
    df_rolling['xg_gini'] = 1 - df_rolling['xg_depth']
    df_rolling['toi_gini'] = 1 - df_rolling['toi_depth']

    # Calculate 10-game rolling averages for each Gini
    for col in ['shot_gini', 'cf_gini', 'xg_gini', 'toi_gini']:
        df_rolling[f'{col}_rolling'] = (
            df_rolling.groupby('team_abbrev')[col]
            .transform(lambda x: x.rolling(window=10, min_periods=1).mean())
        )

    # Get most recent values for each team
    latest = df_rolling.groupby('team_abbrev').last()

    # Build the nested dictionary structure
    rolling_dict = {
        "data": {
            team: {
                "weighted_depth": float(row['weighted_depth_rolling']),
                "shot_gini": float(row['shot_gini_rolling']),
                "cf_gini": float(row['cf_gini_rolling']),
                "xg_gini": float(row['xg_gini_rolling']),
                "toi_gini": float(row['toi_gini_rolling'])
            }
            for team, row in latest.iterrows()
        },
        "updated_at": datetime.utcnow().isoformat(),
        "season": season
    }

    # Save to S3
    s3 = s3fs.S3FileSystem(anon=False)
    file_path = f'{S3_BUCKET}/depth_scores/rolling_averages.json'

    with s3.open(file_path, 'w') as f:
        json.dump(rolling_dict, f, indent=2)
        
    return rolling_dict

def get_current_rolling_averages(season=get_current_season()):
    """
    Read cached rolling averages from S3.
    
    Returns:
        dict: {team_abbrev: weighted_depth_rolling} or None if file doesn't exist
    """
    import s3fs
    import json

    try:
        s3 = s3fs.S3FileSystem(anon=False)
        file_path = f'{S3_BUCKET}/depth_scores/rolling_averages.json'

        with s3.open(file_path, 'r') as f:
            rolling_dict = json.load(f)

        return rolling_dict['data']
    except Exception as e:
        print(f"Error reading rolling averages: {e}")
        return None

def create_league_depth_boxplot(df_rolling):
      """
      Create Plotly bar chart of team depth rankings.
        
      Args:
          df_rolling: DataFrame from get_league_depth_data()
        
      Returns:
          Plotly figure object
      """
      # Calculate median depth and games played for each team
      team_stats = df_rolling.groupby('team_abbrev').agg({
          'weighted_depth_rolling': 'last',
          'game_number': 'max'
      }).reset_index()

      # Sort by median depth (lowest to highest)
      team_stats = team_stats.sort_values('weighted_depth_rolling')

      # Get team colors
      from app.config.team_colors import TEAM_COLORS

      # Calculate league median for centering
      overall_median = df_rolling['weighted_depth_rolling'].median()

      # Calculate difference from median for each team
      team_stats['diff_from_median'] = team_stats['weighted_depth_rolling'] - overall_median

      # Calculate range for y-axis
      max_val = team_stats['weighted_depth_rolling'].max()
      min_val = team_stats['weighted_depth_rolling'].min()
      max_distance = max(abs(max_val - overall_median), abs(min_val - overall_median))
      padding = max_distance * 0.1

      # Create bar chart
      fig = go.Figure()

      fig.add_trace(go.Bar(
          x=team_stats['team_abbrev'],
          y=team_stats['diff_from_median'],  # Difference from median
          base=overall_median,  # Bars start from median line
          marker_color=[TEAM_COLORS.get(team, '#999999') for team in team_stats['team_abbrev']],
          marker=dict(opacity=0.8),
          customdata=team_stats[['game_number', 'weighted_depth_rolling']],  # Include actual depth value
          hovertemplate='<b>%{x}</b><br>' +
                        '10-game Avg: %{customdata[1]:.3f}<br>' +  # Show actual value, not difference
                        '%{customdata[0]:.0f} games played<br>' +
                        '<extra></extra>'
      ))

      fig.update_layout(
          # Title
          title=dict(
              text=f"Team Depth over the last 10 games ({get_current_season()}-{str(get_current_season() + 1)[-2:]} Season)",
              subtitle=dict(text="Ten-game rolling average of TDI; See here for methodology."),
              font=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=24,
                  color="#041E42"
              ),
              x=0.05,
              xanchor='left'
          ),

          # Axes
          xaxis=dict(
              title=None,
              showgrid=False,
              tickfont=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=14,
                  color="#041E42"
              )
          ),

          yaxis=dict(  # Team names
                title=None,
                showgrid=False,
                tickfont=dict(
                    family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                    size=14,
                    color="#041E42"
                ),
                ticks='outside',  # Add ticks extending outward
                ticklen=8,  # Length of tick marks
                tickwidth=1,
                tickcolor='white'  # Make ticks white (invisible against white background)
            ),

          # Overall layout
          showlegend=False,
          height=500,
          margin=dict(l=80, r=40, t=80, b=60),
          plot_bgcolor='white',
          paper_bgcolor='white',
          font=dict(
              family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
              color="#041E42"
          )
      )

      # Add league median reference line with annotation
      fig.add_hline(
          y=overall_median,
          line_dash="dash",
          line_width=2,
          opacity=0.6,
          line_color="#3B4B64"
          )

      return fig

def calculate_team_season_stats(season=get_current_season()):
      """
      Calculate team-level season stats for depth vs goaltending quadrant chart.
      
      For each team across all their games:
      - Mean depth advantage (team TDI - opponent TDI)
      - Mean goaltending advantage (team GSAx - opponent GSAx)
      - Games played
      - Wins
      - Win percentage
      
      Args:
          season: Season in format YYYYZZZZ (e.g., 20242025)
      
      Returns:
          DataFrame with columns: team_abbrev, n_games, wins, win_pct, 
                                 depth_adv_mean, goalie_adv_mean
      """
      import s3fs
      import pandas as pd

      # Read depth scores parquet
      s3 = s3fs.S3FileSystem(anon=False)
      file_path = f'{S3_BUCKET}/depth_scores/depth_scores.parquet'
      df = pd.read_parquet(f's3://{file_path}', filesystem=s3)

      # Filter to current season regular season games only
      season_prefix = f"{season}02"
      df_season = df[df['game_id'].astype(str).str.startswith(season_prefix)].copy()

      # Calculate per-game metrics for each team
      df_season['depth_adv'] = df_season['tdi'] - df_season.groupby('game_id')['tdi'].transform(
          lambda x: x.iloc[1] if len(x) == 2 and x.name == x.iloc[0] else x.iloc[0]
      )

      # Simpler approach: for each row, find opponent's TDI in same game
      game_data = []
      for game_id in df_season['game_id'].unique():
          game_rows = df_season[df_season['game_id'] == game_id]
          if len(game_rows) != 2:
              continue  # Skip incomplete games

          for idx, row in game_rows.iterrows():
              opponent_row = game_rows[game_rows['team_abbrev'] != row['team_abbrev']].iloc[0]

              # Depth advantage (team - opponent)
              depth_adv = row['tdi'] - opponent_row['tdi']

              # Goaltending advantage (team GSAx - opponent GSAx)
              # GSAx = opponent_total_xg - opponent_goals
              team_gsax = row['opponent_total_xg'] - row['opponent_goals']
              opp_gsax = opponent_row['opponent_total_xg'] - opponent_row['opponent_goals']
              goalie_adv = team_gsax - opp_gsax

              # Determine if team won (more goals than opponent)
              won = row['goals'] > opponent_row['goals']

              game_data.append({
                  'team_abbrev': row['team_abbrev'],
                  'game_id': game_id,
                  'depth_adv': depth_adv,
                  'goalie_adv': goalie_adv,
                  'won': won
              })

      # Convert to DataFrame
      df_games = pd.DataFrame(game_data)

      # Aggregate to team level
      team_stats = df_games.groupby('team_abbrev').agg({
          'game_id': 'count',  # games played
          'won': 'sum',        # wins
          'depth_adv': 'mean',
          'goalie_adv': 'mean'
      }).reset_index()

      team_stats.columns = ['team_abbrev', 'n_games', 'wins', 'depth_adv_mean', 'goalie_adv_mean']
      team_stats['win_pct'] = team_stats['wins'] / team_stats['n_games']

      return team_stats

def fetch_current_standings():
      """
      Fetch current NHL standings from the NHL API.
      
      Returns:
          DataFrame with columns: team_abbrev, league_rank
          Where league_rank is 1-32 (1 = best in league)
      """
      import requests
      from datetime import datetime, timedelta
      from zoneinfo import ZoneInfo

      # Use "now" for most current standings
      # NHL API endpoint: https://api-web.nhle.com/v1/standings/now
      url = "https://api-web.nhle.com/v1/standings/now"

      try:
          resp = requests.get(url, timeout=(5, 20))
          resp.raise_for_status()
          data = resp.json()

          # Extract standings array
          standings_list = data.get('standings', [])

          if not standings_list:
              logger.warning("No standings data returned from NHL API")
              return None

          # Build DataFrame
          standings_data = []
          for team in standings_list:
              # Handle nested teamAbbrev structure
              team_abbrev_obj = team.get('teamAbbrev', {})
              if isinstance(team_abbrev_obj, dict):
                  team_abbrev = team_abbrev_obj.get('default', '')
              else:
                  team_abbrev = team_abbrev_obj

              league_rank = team.get('leagueSequence', 999)  # 1 = best

              standings_data.append({
                  'team_abbrev': team_abbrev,
                  'league_rank': league_rank
              })

          df = pd.DataFrame(standings_data)
          return df

      except Exception as e:
          logger.error(f"Error fetching standings: {e}")
          return None
      
def save_team_quadrant_data(season=get_current_season()):
      """
      Calculate and save team quadrant data (depth vs goaltending) to S3.
      
      Combines team season stats with current standings and saves to:
      s3://{S3_BUCKET}/depth_scores/team_quadrant.json
      
      Args:
          season: Season in format YYYYZZZZ (e.g., 20242025)
      
      Returns:
          dict: The saved data structure
      """
      import s3fs
      import json
      from datetime import datetime

      logger.info("Calculating team quadrant data...")

      # Get team stats
      team_stats = calculate_team_season_stats(season=season)

      if team_stats is None or len(team_stats) == 0:
          logger.warning("No team stats calculated")
          return None

      # Get standings
      standings = fetch_current_standings()

      if standings is None:
          logger.warning("No standings data available")
          return None

      # Merge
      team_data = team_stats.merge(standings, on='team_abbrev', how='left')

      # Calculate standing score (1 = best, 0 = worst) for color scale
      n_teams = team_data['league_rank'].max()
      team_data['standing_score'] = 1 - ((team_data['league_rank'] - 1) / (n_teams - 1))

      # Build nested dictionary structure
      quadrant_dict = {
          "data": team_data.to_dict(orient='records'),
          "updated_at": datetime.utcnow().isoformat(),
          "season": season
      }

      # Save to S3
      s3 = s3fs.S3FileSystem(anon=False)
      file_path = f'{S3_BUCKET}/depth_scores/team_quadrant.json'

      with s3.open(file_path, 'w') as f:
          json.dump(quadrant_dict, f, indent=2)

      logger.info(f"✅ Team quadrant data saved: {len(team_data)} teams")
      return quadrant_dict

def create_team_quadrant_scatter(team_data):
      """
      Create Plotly scatter plot showing team depth vs goaltending advantage.
      
      Args:
          team_data: List of dicts with team stats (from team_quadrant.json)
      
      Returns:
          Plotly figure object
      """
      import plotly.graph_objects as go
      import pandas as pd

      # Convert to DataFrame for easier manipulation
      df = pd.DataFrame(team_data)

      if df.empty:
          # Return empty figure with message
          fig = go.Figure()
          fig.add_annotation(text="No data available", showarrow=False)
          return fig

      # Calculate axis limits for quadrant labels
      x_range = df['depth_adv_mean'].abs().max() * 1.4
      y_range = df['goalie_adv_mean'].abs().max() * 1.4

      # Create scatter plot
      fig = go.Figure()

      # Add scatter points
      fig.add_trace(go.Scatter(
          x=df['depth_adv_mean'],
          y=df['goalie_adv_mean'],
          mode='markers+text',
          marker=dict(
              size=14,
              color=df['standing_score'],  # 0 (worst) to 1 (best)
              colorscale=[
                  [0, '#C0392B'],      # Red (worst teams)
                  [0.5, '#FFFFFF'],    # White (middle)
                  [1, '#1E9E5A']       # Green (best teams)
              ],
              showscale=True,
              colorbar=dict(
                  title="League<br>Standing",
                  tickvals=[0, 0.5, 1],
                  ticktext=['Worst', 'Middle', 'Best'],
                  len=0.5
              ),
              line=dict(width=1, color='#333333')
          ),
          text=df['team_abbrev'],
          textposition='top center',
          textfont=dict(
              size=14,
              color='#041E42',
              family='Charter, Bitstream Charter, Sitka Text, Cambria, serif'
          ),
          hovertemplate=(
              '<b>%{text}</b><br>' +
              'Depth Adv: %{x:.3f}<br>' +
              'Goalie Adv: %{y:.3f}<br>' +
              'Record: ' + df['wins'].astype(str) + '-' + (df['n_games'] - df['wins']).astype(str) +
              '<br>Win %: ' + (df['win_pct'] * 100).round(1).astype(str) + '%' + '<br>'
              'Standings: ' + df['league_rank'].astype(int).astype(str) +
              '<extra></extra>'
          )
      ))

      # Add reference lines
      fig.add_hline(y=0, line_dash="dash", line_width=1, line_color="black")
      fig.add_vline(x=0, line_dash="dash", line_width=1, line_color="black")

      # Add quadrant annotations
      fig.add_annotation(
          x=x_range * 0.75, y=y_range * 0.75,
          text="<b>Dominant teams</b><br>(Depth + Goaltending)",
          showarrow=False,
          font=dict(size=18, color='#3B4B64'),
          bgcolor='rgba(255,255,255,0.85)',
          borderpad=8
      )

      fig.add_annotation(
          x=-x_range * 0.75, y=y_range * 0.75,
          text="<b>Goalie-dependent teams</b><br>(Top-heavy construction)",
          showarrow=False,
          font=dict(size=18, color='#E76F2B'),
          bgcolor='rgba(255,255,255,0.85)',
          borderpad=8
      )

      fig.add_annotation(
          x=x_range * 0.75, y=-y_range * 0.75,
          text="<b>Depth-driven teams</b><br>(Less goalie dependence)",
          showarrow=False,
          font=dict(size=18, color='#3B4B64'),
          bgcolor='rgba(255,255,255,0.85)',
          borderpad=8
      )

      fig.add_annotation(
          x=-x_range * 0.75, y=-y_range * 0.75,
          text="<b>High-variance teams</b><br>",
          showarrow=False,
          font=dict(size=18, color='grey'),
          bgcolor='rgba(255,255,255,0.85)',
          borderpad=8
      )

      # Update layout
      fig.update_layout(
          title=dict(
              text=f"Team Identity: Depth vs Goaltending ({get_current_season()}-{str(get_current_season() + 1)[-2:]} Season)",
              subtitle=dict(text="Depth and Goalie performance relative to opponents; See here for methodology."),
              font=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=24,
                  color="#041E42"
              ),
              x=0.05,
              xanchor='left'
          ),
          xaxis=dict(
              title="Average Depth Advantage<br>(team − opponent)",
              title_font=dict(size=18),
              showgrid=True,
              gridcolor='#e0e0e0',
              zeroline=False,
              range=[-x_range, x_range],
              tickfont=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=12,
                  color="#041E42"
              )
          ),
          yaxis=dict(
              title="Average Goalie Advantage<br>(team GSAx − opponent GSAx)",
              title_font=dict(size=18),
              showgrid=True,
              gridcolor='#e0e0e0',
              zeroline=False,
              range=[-y_range, y_range],
              tickfont=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=12,
                  color="#041E42"
              )
          ),
          showlegend=False,
          height=600,
          margin=dict(l=80, r=40, t=100, b=80),
          plot_bgcolor='white',
          paper_bgcolor='white',
          font=dict(
              family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
              color="#041E42"
          ),
          hovermode='closest'
      )

      return fig

def get_team_quadrant_data(season=get_current_season()):
      """
      Read cached team quadrant data from S3.
      
      Returns:
          list: Team data ready for plotting, or None if file doesn't exist
      """
      import s3fs
      import json

      try:
          s3 = s3fs.S3FileSystem(anon=False)
          file_path = f'{S3_BUCKET}/depth_scores/team_quadrant.json'

          with s3.open(file_path, 'r') as f:
              quadrant_dict = json.load(f)

          return quadrant_dict['data']
      except Exception as e:
          logger.error(f"Error reading team quadrant data: {e}")
          return None