# sAVe
Transit Platform

## Welcome
to developing for sAVe.

Here, I've tried to write instructions on how to run this for people with little to no development experience.

## Requirements

- Python (version >= 3.6)
- Any modern web browser
- Pip for Python
- Git
- Access to a command line interface

## Recommendations

- A nice code editor, like Atom
- A virtual environment, created like `python3 -m venv venv`
- An [ssh key](https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/)
- Linux/Unix environment (on [Windows](https://docs.microsoft.com/en-us/windows/wsl/install-win10)?)
- Basic programming knowledge

## Setting Up the Environment

### Note

- Anything between these: `<>` is to be replaced, along with the removal of the actual brackets.
- I'm going to assume that you're running this on Ubuntu, which you can download even on Windows.
- The platform will look for a file called `secret.json` in a format like this:

```json
{
    "coord": "<coord_api_key>",
    "mta": "<mta_api_key>",
    "mapquest": "<mapquest_api_key>"
}
```

You can find those api keys at these websites:
- https://coord.co/account
- https://datamine.mta.info/user
- https://developer.mapquest.com/user/login


Pop open some command line (terminal):

Install all the really important stuff:

    sudo apt-get update
    sudo apt-get upgrade
    sudo apt-get install git
    sudo apt-get install python3
    sudo apt-get install python3-venv

Clone the repository. Use the ssh URL if you have an [ssh key](https://help.github.com/articles/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent/).

    git clone <link-to-sAVe-here>
    cd sAVe

This is a good time to create your virtual environment:

    python3 -m venv venv
    source venv/bin/activate/

Inside the requirements.txt file, all of the required packages are stored.

    pip install -r requirements.txt

To update this file when adding new packages:

    bash createRequirements.bash

To run the app (in debug mode):

    export FLASK_APP=app.py
    export FLASK_DEBUG=1
    python3 -m flask run

You should see a line that looks like `* Running on http://127.0.0.1:5000/ (Press CTRL+C to quit)`.

Open a web browser, and navigate to the url given to you (in this example http://127.0.0.1:5000/).

You should see the login page. Congrats!


## Navigating the site
Currently unlisted pages:

- /statistics
- /businessdata

All of the other paths should be accessible simply via navigating the site regularly.
