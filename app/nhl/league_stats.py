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
    # Step 1: Read the master parquet file from S3
    df = pd.read_parquet('s3://hockey-decoded/depth_scores/depth_scores.parquet')

    # Step 2: Filter to just this season's regular season games
    # Regular season game_ids start with {season}02
    # Example: 2024-25 regular season = 2024020001, 2024020002, etc.
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

    return df_rolling

def create_league_depth_boxplot(df_rolling):
    """
    Create Plotly box plot of team depth distribution.
      
    Args:
        df_rolling: DataFrame from get_league_depth_data()
      
    Returns:
        Plotly figure object
    """
    # Step 1: Calculate median depth for each team (for sorting)
    team_medians = (
        df_rolling.groupby('team_abbrev')['weighted_depth_rolling']
        .median()
        .sort_values()
    )
    sorted_teams = team_medians.index.tolist()

    # Step 2: Get team colors
    from app.config.team_colors import TEAM_COLORS

    # Step 3: Create empty figure
    fig = go.Figure()

    # Step 4: Add a box plot for each team
    for team in sorted_teams:
        # Get just this team's data
        team_data = df_rolling[df_rolling['team_abbrev'] == team]

        # Add a box trace
        fig.add_trace(go.Box(
            y=team_data['weighted_depth_rolling'],  # The values to plot
            name=team,                               # Team name (for hover)
            marker_color=TEAM_COLORS.get(team, '#999999'),  # Team color
            marker=dict(opacity=0.7),                # Make slightly transparent
            boxmean=False,                            # don't show mean line
            line=dict(width=1.5)
        ))

    fig.update_layout(
        # Title
        title=dict(
            text="Team Depth Distribution (2024-25 Season)",
            font=dict(
                family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                size=24,
                color="#041E42"  # var(--blue-dark)
            ),
            x=0.25,  # Center the title
            xanchor='center'
        ),

        # Axes
        xaxis=dict(
            title=dict(
                text=None,
                font=dict(
                    family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                    size=20,
                    color="#041E42"
                )
            ),
            showgrid=False,
            tickfont=dict(
                family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                size=14,
                color="#041E42"
            )
        ),

        yaxis=dict(
            title=dict(
                text="Weighted Average Depth",
                font=dict(
                    family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                    size=20,
                    color="#041E42"
                )
            ),
            showgrid=False,
            gridcolor='rgba(0,0,0,0.1)',
            gridwidth=0.5,
            ticks='outside',
            tickcolor='white',
            tickfont=dict(
                family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
                size=14,
                color="#041E42"
            ),
            side='left',  # Ensure ticks on left
            ticklen=8,  # Length of tick marks extending from axis
            tickwidth=1
        ),

        # Overall layout
        showlegend=False,
        height=500,
        margin=dict(l=80, r=40, t=80, b=60),
        plot_bgcolor='white',  
        paper_bgcolor='white',  # White background for the whole chart
        font=dict(
            family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
            color="#041E42"
        )
    )

    # Add custom y-axis label as annotation
    # fig.add_annotation(
    #     x=0.0,  # Position to the right of the plot (in paper coordinates)
    #     y=0.4,   # At the top of the y-axis range
    #     xref='paper',  # Use paper coordinates (0-1) for x
    #     yref='y',      # Use data coordinates for y
    #     text="(Weighted average depth)",
    #     showarrow=False,
    #     font=dict(
    #         family="Charter, Bitstream Charter, Sitka Text, Cambria, serif",
    #         size=14,
    #         color="#041E42"
    #     ),
    #     xanchor='left',  # Anchor text to the left
    #     yanchor='middle'  # Vertically center on 0.4
    # )

      # Step 6: Add horizontal reference line
    overall_median = df_rolling['weighted_depth_rolling'].median()
    fig.add_hline(
        y=overall_median,
        line_dash="dash",
        line_width=1,
        opacity=0.4,
        line_color="#3B4B64"  # var(--blue)
    )

    return fig

