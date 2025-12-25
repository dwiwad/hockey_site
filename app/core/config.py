from datetime import date

# Function to determine what season it currently is
def get_current_season():
    """
    Calculate the current NHL season based on today's date

    Typically the season runs from October (year x) to June (year x+1)
    I am going to name the season after the year it STARTS.

    Returns:
        int: the current NHL season year
    """

    # Get todays date
    today = date.today()
    year = today.year
    month = today.month
    
    # if month >= 10 return year
    if month >= 10:
        return year
    # else return year - 1
    else:
        return year-1