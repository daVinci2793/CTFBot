import requests  # so we can get google calendar info
import json  # provides functions to go from plain text to dicts and for logging
from datetime import datetime  # stuff to find certain CTF events
import calendar  # functions to find date names
import discord  # stuff for discord bot
from discord import app_commands  # allows discord commands
import pytz  # for date localization

# logging
import logging
import logging.config

# utility to get one full year forward of CTF events
from dateutil.relativedelta import relativedelta
from math import *  # all math functions
from bs4 import BeautifulSoup

intents = discord.Intents().all()  # we need all discord intents
client = discord.Client(intents=intents)  # init a client with given intents
tree = app_commands.CommandTree(client)  # for discord commands

logging.config.fileConfig("logging.conf")
logger = logging.getLogger("botLogger")

with open("webhookurl.token", "r") as file:
    webhookurl = file.read()  # get the webhook url from file


@tree.command(name="ctfinfo", description="Get more information about a CTF event")
async def ctfinfo(interaction, eventid: int):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }
    websiteresponse = requests.get(
        "https://ctftime.org/event/" + str(eventid), headers=headers
    )
    websitehtml = websiteresponse.text

    websitehtml = websitehtml.replace("<br />", "\n").replace("<b>", "### ")

    soup = BeautifulSoup(websitehtml, "html5lib")
    pageheader = soup.find("div", {"class": "page-header"}).find("h2")
    eventname = pageheader.get_text()
    teamamount = soup.find(lambda tag: tag.name == "p" and "teams total" in tag.text)
    teamamount = teamamount.get_text().split(" ")[0]

    teams = []
    for div in soup.find_all("tr")[1:11]:
        linkdiv = div.find("a", href=True)
        teams.append(
            {
                "name": linkdiv.get_text().strip(),
                "link": "https://ctftime.org" + linkdiv["href"],
            }
        )
    informationbox = soup.find("div", {"class": "span10"})
    informationboxes = informationbox.findChildren("p", recursive=False)
    eventformat = informationboxes[4].get_text().replace("Format: ", "")
    eventurl = informationboxes[5].get_text().replace("Official URL: ", "")
    eventlocation = informationboxes[1].get_text().replace("### ", "")
    message = "> # [" + eventname + "](<" + eventurl + ">)" + "\n"
    message += "> ## Event ID: `" + str(eventid) + "`\n"
    message += "> ## Format: " + eventformat + "\n"
    message += "> ## Location: " + eventlocation.replace("On-line", "Online") + "\n"
    message += "> ## Teams: " + teamamount + "\n"
    message += "> ## Description \n> "
    message += (
        soup.find("div", {"id": "id_description"})
        .get_text()
        .strip()
        .replace("\n", "\n> ")
        + "\n"
    )
    # for div in teams[1:11]:
    # linkdiv = div.find("a", href=True)
    # message += "> 🔹 [" + linkdiv.get_text().strip() + "](<https://ctftime.org" + linkdiv["href"] + ">)" + "\n"

    await interaction.response.send_message(message, ephemeral=False)


@tree.command(name="upcoming", description="Get the next 7 days of CTF events")
async def upcoming(interaction):
    logger.info("upcoming command was called")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36"
        "(KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    # get the utc time now in unix epoch time
    now = datetime.utcnow().timestamp()

    # get the utc time + 5 days in unix epoch time
    seven_days = datetime.utcnow() + relativedelta(days=+7)
    seven_days = seven_days.timestamp()

    try:
        r = requests.get(
            "https://ctftime.org/api/v1/events/?limit=100"
            + "&start="
            + str(int(now))
            + "&finish="
            + str(int(seven_days)),
            headers=headers,
        )
        r.raise_for_status
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error: %s", errh.args[0])
        logger.error("Aborting")
        return

    logger.info("Api request returned: HTTP %d", r.status_code)

    data = r.json()

    # create embed with title and description
    embed = discord.Embed(
        title="Upcoming CTF Events",
        description="Here are the upcoming CTF events in the next 7 days.",
        type="article",
    )

    # loop through all events
    for event in data:
        # get the event title
        event_title = event["title"]

        # get the event url
        event_url = event["url"]

        # get the event start time
        event_start = event["start"]

        event_id = event["id"]

        # convert start time to unix timestamp in unix epoch time
        event_start = datetime.strptime(event_start, "%Y-%m-%dT%H:%M:%S%z")
        event_start = event_start.timestamp()

        # add a field to the embed
        embed.add_field(
            name=event_title,
            value=event_url,
            inline=True,
        )

        # add id field to embed
        embed.add_field(
            name="Event ID",
            value=event_id,
            inline=True,
        )

        # add a field to the embed
        embed.add_field(
            name="Start Date",
            value="<t:" + str(int(event_start)) + ":f>",
            inline=True,
        )

    logger.info("embed generated, enjoy your information")
    logger.info("Sending data")
    # send embed
    await interaction.response.send_message(embed=embed)


@tree.command(
    name="more_info",
    description="Get more information about a specific CTF by CTF Time ID",
)
async def moreinfo(interaction, eventid: int):
    logger.info("more_info command called")

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }

    try:
        r = requests.get(
            "https://ctftime.org/api/v1/events/" + str(eventid) + "/", headers=headers
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as errh:
        logger.error("HTTP Error: %s", errh.args[0])
        logger.error("Aborting")
        return

    logger.info("Api request returned: HTTP %d", r.status_code)

    # get json data from api call
    data = r.json()

    # get the event details
    event_title = data["title"]
    event_url = data["url"]
    event_start = data["start"]
    event_end = data["finish"]
    event_description = data["description"]

    # get the event image url
    event_image = data["logo"]

    # convert start time to unix timestamp in unix epoch time
    event_start = datetime.strptime(event_start, "%Y-%m-%dT%H:%M:%S%z")
    event_start = event_start.timestamp()

    # convert end time to unix timestamp in unix epoch time
    event_end = datetime.strptime(event_end, "%Y-%m-%dT%H:%M:%S%z")
    event_end = event_end.timestamp()

    # create embed
    embed = discord.Embed(
        title=event_title,
        url=event_url,
        description=event_description,
        type="article",
    )

    # Add tumbnail to embed
    embed.set_thumbnail(url=event_image)

    embed.add_field(
        name="Start Date",
        value="<t:" + str(int(event_start)) + ":d>",
        inline=True,
    )

    embed.add_field(
        name="End Date",
        value="<t:" + str(int(event_end)) + ":d>",
        inline=True,
    )

    # new line
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    # Add a non-relative start time for the event
    embed.add_field(
        name="Start Time",
        value="<t:" + str(int(event_start)) + ":t>",
        inline=True,
    )

    embed.add_field(
        name="End Time",
        value="<t:" + str(int(event_end)) + ":t>",
        inline=True,
    )

    # new line
    embed.add_field(name="\u200b", value="\u200b", inline=True)

    # add fields to embed
    embed.add_field(
        name="When?",
        value="<t:" + str(int(event_start)) + ":R>",
        inline=False,
    )

    logger.info("embed generated, enjoy your information")
    logger.info("Sending data")
    # send embed
    await interaction.response.send_message(embed=embed)


@tree.command(
    name="ctfparticipants",
    description="Get a list of people participating in a CTF event.",
)
async def ctfparticipants(interaction, eventid: int):
    with open("votes.json", "r") as file:
        votes = json.load(file)
    message = (
        "> # ["
        + votes[str(eventid)]["name"]
        + "](<"
        + votes[str(eventid)]["url"]
        + ">)\n"
    )
    message += "> ## Participants:\n"
    for participant in votes[str(eventid)]["participants"]:
        message += (
            "> **"
            + participant["displayname"]
            + "** ("
            + participant["username"]
            + ")\n"
        )
    await interaction.response.send_message(message)


@tree.command(name="ctfpoll", description="Start a poll for CTF participation.")
async def ctfpoll(interaction, eventid: int):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }
    websiteresponse = requests.get(
        "https://ctftime.org/event/" + str(eventid), headers=headers
    )
    websitehtml = websiteresponse.text
    websitehtml = websitehtml.replace("<br />", "\n").replace("<b>", "### ")

    soup = BeautifulSoup(websitehtml, "html5lib")
    pageheader = soup.find("div", {"class": "page-header"}).find("h2")
    eventname = pageheader.get_text()
    teamamount = soup.find(lambda tag: tag.name == "p" and "teams total" in tag.text)
    teamamount = teamamount.get_text().split(" ")[0]
    teams = []
    for div in soup.find_all("tr")[1:11]:
        linkdiv = div.find("a", href=True)
        teams.append(
            {
                "name": linkdiv.get_text().strip(),
                "link": "https://ctftime.org" + linkdiv["href"],
            }
        )
    informationbox = soup.find("div", {"class": "span10"})
    informationboxes = informationbox.findChildren("p", recursive=False)
    eventformat = informationboxes[4].get_text().replace("Format: ", "")
    eventurl = informationboxes[5].get_text().replace("Official URL: ", "")
    eventlocation = informationboxes[1].get_text().replace("### ", "")

    message = "> # [" + eventname + "](<" + eventurl + ">)" + "\n"
    message += "> ## Event ID: `" + str(eventid) + "`\n"
    message += "> ## Format: " + eventformat + "\n"
    message += "> ## Link: " + eventurl
    await interaction.response.send_message("Starting poll...", ephemeral=True)

    infomessage = await interaction.channel.send(message)
    await infomessage.add_reaction("<:yes:1148772032302039121>")
    await infomessage.add_reaction("<:no:1148772028216778792>")

    def check(reaction, user):
        return (not user.bot) and reaction.message == infomessage

    while True:
        reaction, user = await client.wait_for("reaction_add", check=check)
        with open("votes.json", "r") as file:
            votes = json.load(file)
        if str(eventid) not in votes:
            votes[str(eventid)] = {
                "url": "",
                "votesyes": 0,
                "votesno": 0,
                "participants": [],
            }
        votes[str(eventid)]["url"] = eventurl
        votes[str(eventid)]["name"] = eventname
        try:
            if reaction.emoji.id == 1148772032302039121:
                print("yes")
                votes[str(eventid)]["votesyes"] += 1
                votes[str(eventid)]["participants"].append(
                    {
                        "id": str(user.id),
                        "username": user.name,
                        "displayname": user.display_name,
                    }
                )
            if reaction.emoji.id == 1148772028216778792:
                print("no")
                votes[str(eventid)]["votesno"] += 1
            with open("votes.json", "w") as file:
                json.dump(votes, file, indent=4)
        except:
            continue


@tree.command(name="getctf", description="Find upcoming CTFs")
# variable structure: VARIABLENAME: TYPE = DEFAULTVALUE
async def getctf(interaction, amount: app_commands.Range[int, 1, 15] = 10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/50.0.2661.102 Safari/537.36"
    }
    websiteresponse = requests.get(
        "https://ctftime.org/event/list/upcoming", headers=headers
    )
    websitehtml = websiteresponse.text
    # websitehtml = websitehtml.replace("<br />", "\n").replace("<b>", "### ")
    soup = BeautifulSoup(websitehtml, "html5lib")
    table = soup.find_all("div", {"class": "container"})[1]
    tablerows = table.findChildren("tr")
    finalmessage = """
    > ## Here are some upcoming CTFs:
    """
    for row in tablerows[
        1 : amount + 1
    ]:  # we loop from the second item to skip the header
        datarows = row.findChildren("td")
        eventlink = "https://ctftime.org" + datarows[0].find("a", href=True)["href"]
        eventdate = datarows[1].get_text().replace("Sept", "Sep").split(" — ")
        startdt = datetime.strptime(
            str(datetime.now().year) + " " + eventdate[0], "%Y %d %b., %H:%M %Z"
        )
        enddt = datetime.strptime(eventdate[1], "%d %b. %Y, %H:%M %Z")
        eventstart = (
            "<t:"
            + str(startdt.timestamp())[:-2]
            + ":d><t:"
            + str(startdt.timestamp())[:-2]
            + ":t>"
        )
        eventend = (
            "<t:"
            + str(enddt.timestamp())[:-2]
            + ":d><t:"
            + str(enddt.timestamp())[:-2]
            + ":t>"
        )
        finalmessage += (
            "> ["
            + datarows[0].get_text()
            + "](<"
            + eventlink
            + ">) on "
            + eventstart
            + " Event ID: `"
            + eventlink.replace("https://ctftime.org/event/", "")
            + "`\n"
        )
    finalmessage += "> \n> ***all dates are in UTC*** \n"
    # with open("output.html", "w", encoding="UTF-8") as file:
    # file.write(soup.prettify())
    await interaction.response.send_message(finalmessage)


@tree.command(name="createevent", description="Create an event.")
async def createevent(
    interaction,
    month: app_commands.Range[int, 0, 12],
    day: app_commands.Range[int, 0, 31],
    year: int,
    hour: app_commands.Range[int, 0, 12],
    minute: app_commands.Range[int, 0, 60],
    meridiem: str,
):
    eventarray = [
        str(month),
        str(day),
        str(year),
        str(hour),
        str(minute),
        str(meridiem),
    ]
    eventstartdate = datetime.strptime(" ".join(eventarray), "%m %d %Y %I %M %p")
    print(str(eventstartdate))
    await interaction.response.send_message(str(eventstartdate), ephemeral=True)


"""@tree.command(name="getctf", description="Find upcoming CTFs") #register a command into discord
#variable structure: VARIABLENAME: TYPE = DEFAULTVALUE
async def getctf(interaction, amount: app_commands.Range[int, 5, 20] = 10):
    maxresults = amount + 1 #maxresults needs value + 1 for some reason
    timemin = datetime.now().strftime("%Y-%m-%d") #timemin is the current datetime
    timemax = (datetime.now() + relativedelta(years=1)).strftime("%Y-%m-%d") #timemax is the current datetime + 1 year
    rssurl = f"https://clients6.google.com/calendar/v3/calendars/ctftime@gmail.com/events?calendarId=ctftime%40gmail.com&singleEvents=true&timeZone=Africa%2FAbidjan&maxAttendees=1&maxResults={maxresults}&sanitizeHtml=true&timeMin={timemin}T00%3A00%3A00Z&timeMax={timemax}T00%3A00%3A00Z&key=AIzaSyBNlYH01_9Hc5S1J9vuFmu2nUqBZJNAXxs"
    res = requests.get(rssurl)
    
    rescontent = res.content.decode('utf8')  # .replace("'", '"')

    responsejson = json.loads(rescontent)
    with open("output.json", "w") as file:
        json.dump(responsejson, file, indent=4)
    finalmessage = '> ## Here are some upcoming CTFs:'
    upcomingevents = responsejson["items"]
    upcomingevents = sorted(upcomingevents, key=lambda x: x["start"]["dateTime"])
    names = []
    messagewidth = 60
    for item in upcomingevents:
        eventName = item["summary"]
        eventTime = datetime.fromisoformat(item["start"]["dateTime"])
        eventTimezone = item["start"]["timeZone"] #Format: UTC
        eventDuration = datetime.fromisoformat(item["end"]["dateTime"]) - datetime.fromisoformat(item["start"]["dateTime"])
        durationDays = eventDuration.days
        durationHours = floor(eventDuration.seconds / 3600)
        durationMinutes = floor(((eventDuration.seconds / 3600) - durationHours) * 60)
        durationSeconds = floor((((eventDuration.seconds / 3600) - durationHours) * 60 - durationMinutes) * 60)
        now = datetime.now()
        now = pytz.UTC.localize(now) 
        if(eventTime < now):
            continue
        eventLink = item["description"][-32:-2]
        names.append(item)
        finalmessage += "> " + "[" + item["summary"] + "](<" + eventLink + ">)" + " on " + "<t:" + str(calendar.timegm(eventTime.timetuple())) + ":D>"
        finalmessage += "   **ID:** `" + eventLink.replace("https://ctftime.org/event/", "") + "`"
        finalmessage += ("   **duration:** " + str(durationHours) + " hour" + ("s" if durationHours != 1 else "") + " " + ((str(durationMinutes) + " minute" + ("s" if durationHours != 1 else "")) if durationMinutes != 0 else "")) if durationHours != 0 else "" 
        finalmessage += "\n"
    finalmessage += "\n"
    body = {
        "content": finalmessage
    }
    
    await interaction.response.send_message(body["content"], ephemeral=False)
"""

"""
Code to post a webhook
requests.post(
    webhookurl,
    json=body)
"""


@client.event
async def on_message(message):
    if message.author.bot:
        return
    print(message.author.display_name + ": " + message.content)


@client.event
async def on_ready():
    await tree.sync()
    logging.info("Yes, mom, I'm awake.")


with open("token.token", "r") as file:
    token = file.read()
client.run(token)
