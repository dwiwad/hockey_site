import pandas as pd
import s3fs
import plotly.graph_objects as go

def get_league_depth_data(season=2025):
    """
    Get rolling 10-game depth averages for all teams.
    
    Args:
        season: Season in format YYYYZZZZ (e.g., 20242025)
    
    Returns:
        DataFrame with columns: team_abbrev, game_number, weighted_depth_rolling
    """
    # Step 1: Read the master parquet file from S3 and get its metadata
    s3 = s3fs.S3FileSystem()
    file_path = 'hockey-decoded/depth_scores/depth_scores.parquet'

    # Get file info (includes last modified time)
    file_info = s3.info(file_path)
    last_modified = file_info['LastModified']  # datetime object

    df = pd.read_parquet(f's3://{file_path}')

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
              text="Team Depth Rankings (2024-25 Season)",
              font=dict(
                  family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                  size=24,
                  color="#041E42"
              ),
              x=0.25,
              xanchor='center'
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