def server_status_template(data, daily_update=False, interaction=None):
    """
    Formats a JSON object into a stylized Discord message.

    Parameters:
    - data (dict): The JSON object to format.

    Returns:
    - str: The formatted Discord message.
    """

    # Extract information from the data
    chapter_count = data.get('chapterCount', 0)
    volume_count = data.get('volumeCount', 0)
    series_count = data.get('seriesCount', 0)
    total_genres = data.get('totalGenres', 0)
    total_authors = data.get('totalPeople', 0)
    total_reading_time = data.get('totalReadingTime', 0)
    most_active_users = data.get('mostActiveUsers', 0)

    if most_active_users:
        top_readers = [item['value']['username'] for item in most_active_users]
    else:
        top_readers = ""

    # Filter out entries with '/doujinshi/' in the folderPath field
    # Using 'mostPopularSeries' now due to 'mostRead' seeming to only list series in alphabetical order
    most_read_series = data.get('mostPopularSeries', [])
    filtered_series = [
        series for series in most_read_series
        if not series['value'].get('folderPath', '').startswith('/doujinshi/')
    ]

    # Limit the 'Most Read' to the first 3 titles
    limit_series = filtered_series[:3]

    # Format filtered series into text
    ''' Commenting out for embed display method
    if limit_series:
        most_read_series_text = "\n".join(
            f"\tID: {series['value']['id']} - Name: {series['value']['name']}"
            for series in limit_series
        )
    else:
        most_read_series_text = "No entries found."
    '''
    # Placeholder in case we use this in the future
    most_read_series_text = ""

    # Stylized title line
    title_line = "━━━━━━━━━━━━━━ **__BNU Manga Server__** ━━━━━━━━━━━━━━"

    # Reply to the user that requested the stats if provided
    user_reply = f"Hey {interaction.user.mention} here's the current server stats,\n" if interaction else ""
    # Add a daily status message if we are doing the daily status channel blast
    daily_status = f"Daily Server Stats" if daily_update else ""
    total_width = len(title_line)
    prompt_line = f" Most Popular Series:\n{most_read_series_text}" if not daily_update \
        else f" Recent Chapter Updates:\n"

    # Format the top readers list if it exists
    if top_readers:
        formatted_top_readers = "Top Readers:\n " + "\n ".join(top_readers[:3])  ## Return just the top 3 readers
    else:
        formatted_top_readers = ""

    # Format message
    message = (
        f"{user_reply}"
        f"```yaml\n"  # Start block quotes with YAML syntax
        f"{title_line.center(total_width)}"  # Center justify the title line
        f"\n{daily_status.center(total_width)}"
        f"\n\n Statistics Report:\n"
        f" Chapter Count: {chapter_count}\n"
        f" Volume Count: {volume_count}\n"
        f" Series Count: {series_count}\n"
        f" Total Genres: {total_genres}\n"
        f" Total Authors: {total_authors}\n"
        f" Total Reading Time: {total_reading_time} hours\n"
        f" {formatted_top_readers}\n"
        f"{prompt_line}"
        f"```"
    )

    return message, limit_series