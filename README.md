# Skaven Watcher Discord Bot

Are you a fanatical rat that needs to keep up to date with the best-best tournament lists? Perhaps consider-think that you should add this bot-servant to your discord server.

Will check daily for the existence of skaven on Goomhammer. If yes, then will message the skaven list in the discord channel.

## How to use
1. Invite SkavenWatch to your discord server by using the following link:  
https://discord.com/api/oauth2/authorize?client_id=1166444316349173820&permissions=10240&scope=bot  

2. Use the `/start` command to being the watch.
- SkavenWatch will then check daily for a competitive-innovation article. If one exists, searches for Skaven lists that are played in tournaments and messages the lists to your discord server.

### Available Commands:
- `/start` - Starts the SkavenWatch to check daily for Skaven lists.
- `/stop` - Stops the SkavenWatch bot, will need `/start` to restart.
- `/status` - gives the current status of SkavenWatch.
- `/get` - gets the most recent goonhammer article Skaven lists.
- `/timetil` - only works while SkavenWatch is `/start`'ed. Gives the time until SkavenWatch checks goonhammer.
- `/purge` - Removes all previous messages from SkavenWatch.

### To Run Locally (dependent on Docker)
1. Create and get a application token using the discord application developer portal.
- https://discord.com/developers/applications
- Can invite to your server by creating a OAuth URL through the OAuth2 URL Generator link in the discord developer portal.

2. Rename `example.env` to `.env` and fill with your token

3. Run `docker-compose build`

4. Run `docker-compose up`

