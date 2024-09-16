def server_status_template(data, interaction=None):
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

    # Filter out entries with '/doujinshi/' in the folderPath field
    most_read_series = data.get('mostReadSeries', [])
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

    # Format message
    message = (
        f"{user_reply}"
        f"```yaml\n"  # Start block quotes with YAML syntax
        f"{title_line.center(40)}\n\n"  # Center justify the title line
        f" Statistics Report:\n"
        f" Chapter Count: {chapter_count}\n"
        f" Volume Count: {volume_count}\n"
        f" Series Count: {series_count}\n"
        f" Total Genres: {total_genres}\n"
        f" Total Authors: {total_authors}\n"
        f" Total Reading Time: {total_reading_time} hours\n"
        f" Most Popular Series:\n{most_read_series_text}"
        f"```"
    )

    return message, limit_series