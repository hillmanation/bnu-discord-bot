import emoji

# List of number emojis from 1️⃣ to 🔟
number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

# List of additional emojis to fill up the remaining 20 slots
extra_emojis = ['🔴', '🟠', '🟡', '🟢', '🔵', '🟣', '🟤', '⚫', '⚪',
                '🍏']

'''
# Extra emojis just in case
, '🍎', '🍊', '🍇', '🍓', '🍍', '🍉', '🍒', '🔥', '🌈']
'''

# Combine the number emojis and extra emojis
all_emojis = number_emojis + extra_emojis


def generate_emoji_manga_map(manga_titles, max_titles: int = None):
    emoji_manga_map = {}
    # Alphabetize the titles first
    sorted_titles = sorted(manga_titles) if not max_titles else sorted(manga_titles[:max_titles])
    for i, title in enumerate(sorted_titles):
        if i < len(all_emojis):
            emoji_manga_map[all_emojis[i]] = title
        else:
            break  # Stop processing if we've run out of emojis [this will also essentially limit the number of titles]
    return emoji_manga_map