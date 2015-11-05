import os

from flask import Flask
from flask import Response
from flask import request
from flask import render_template
from twilio import twiml
from twilio.rest import TwilioRestClient
from twilio.util import TwilioCapability
from twilio.access_token import AccessToken

# Required to connect to Twilio
TWILIO_ACCOUNT_SID = "AC662af494000000000000000000000000"
TWILIO_AUTH_TOKEN = "058d0000000000000000000000000000"
TWILIO_NUMBER = "+14155554963"

# create an authenticated client that can make requests to Twilio for your
# account.
client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Allows us to keep a track of how many times the agent has pressed the
# "transfer" button for this call
xferd = []

# Create a Flask web app
app = Flask(__name__)

# Render the Twilio Client as a web page
@app.route('/')
def index():
    # Create a capability token for this client instance
    capability = TwilioCapability(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    # If the client attempts an outgoing call, invoke a TwiML app
    capability.allow_client_outgoing("AP17a745dc5cfc00000000000000000000")
    # We can make incoming calls to this client with <dial><client>david</client></dial>
    capability.allow_client_incoming("david")
    token = capability.generate()
    return render_template("client_browser.html",
                           capability_token=token)


# The Twilio Client has attempted to make an outbound call
# This function makes that call happen
@app.route('/client_call', methods=['GET', 'POST'])
def client_pstn():
    # because we are calling out to the PSTN, we need to provide a phone
    # number, associated with the same Twilio account as the client, as
    # caller ID. It needs to be in e.164 format
    callerID = "+14155554963"
    # Get the dialed number from the parameters in the HTTP request
    called_number = request.values.get('tocall')
    # Generate a TwiML response...
    response = twiml.Response()
    # ...and actually place a call to the dialed number
    # when the client initiates a transfer and puts this call
    # on hold, the action url will be invoked, giving us an
    # opportunity to update the Client leg
    with response.dial(callerId=callerID, action="/agent_into_conf") as r:
        r.number(called_number)
    return str(response)


# Ooh, the person using the Twilio Client has pressed the "Transfer" button
# This allows them to start the process of transferring the called party to
# a colleague (for example)
@app.route('/transfer', methods=['POST', 'GET'])
def transfer():
    
    # The Twilio Client has told us what the call sid is for it's connection
    # to Twilio. We want to find out what the call sid is for the called
    # party's connection to Twilio. This will be listed as a child call on
    # the Client's call
    call_sid = request.values.get('params[CallSid]')
    child_calls = client.calls.list(parent_call_sid=call_sid)
    
    # The transfer button has two similar but different functions
    # 1) start the transfer process by putting the called party on hold
    #    and initiating a call to the colleague
    # 2) take the called party off hold and connect them to the 
    #    colleague
    # The easy way of figuring out which the person using the Client
    # wants to do is by figuring out whether they have already pressed
    # the Transfer button on this call. If they have not, they want to
    # do (1). If this is the second time they have pressed the button on
    # this call, they want to do (2).
    if call_sid not in xferd:
        # For ease, the second agent, the colleague, is on a cell phone. Again,
        # we provide a url so that we can provide TwiML to control this new call
        # leg
        second_agent_call = client.calls.create(to="+15105550555", from_="+15105553413",
                                                url="http://2deedf27.ngrok.io/second_agent_in_conf")
        for child_call in child_calls:
            print call_sid
            print child_call.sid
            # To place the called party on hold, we make a REST request
            # to update their call leg (identified via call sid) and 
            # Twilio will then send a request to the url specified
            # so that we can provide instructions about how to update
            # the call leg via TwiML
            client.calls.update(child_call.sid, method="POST",
                                url="http://2deedf27.ngrok.io/called_on_hold")
            xferd.append(call_sid)
    else:
        for child_call in child_calls:
            # this is the second time the transfer button has been pressed
            # for this call so we will put the called party into the 
            # conference with the colleague
            client.calls.update(child_call.sid, method="POST",
                                url="http://2deedf27.ngrok.io/customer_to_conf")
    return "hello"


# This is the URL we gave to Twilio when we asked to update
# the call leg of the called party at the start of the transfer
# process. We will use TwiML to put the called party into a 
# conference that contains only them and some hold music
@app.route('/called_on_hold', methods=['POST', 'GET'])
def called_on_hold():
    print request.values
    response = twiml.Response()
    with response.dial() as r:
        # A nice, simple conference name. I can do this here
        # because I only write this web app to handle one Client
        # and that Client can only have one call going at a time
        # To make this web app more general, we would need to 
        # come up with a process for giving each "Hold" conference
        # a unique but meaningful name, so that we know how to 
        # reference it later
        conference_name = "Hold"
        r.conference(conference_name, endConferenceOnExit=True)
    return str(response)


# Either the called party hung up before we managed to transfer
# them or we just put them on hold. Here, we will figure out
# which
@app.route('/agent_into_conf', methods=['POST', 'GET'])
def agent_into_conf():
    print "in agent into conf"
    print request.values
    child_sid = request.values.get("DialCallSid")
    child_call = client.calls.get(child_sid)
    response = twiml.Response()
    # if the customer hasn't hung up, it means we've
    # put them on hold so we should update the Client
    # call leg to put them into a conference with the
    # colleague
    if child_call.status == "in-progress": 
        with response.dial() as r:
            conference_name = "xfer"
            r.conference(conference_name)
    # if they have hung up, we should follow suit
    else:
        response.hangup()
    return str(response)

# we'll put our colleague into a converence so that they can
# await our arrival
@app.route("/second_agent_in_conf", methods=["POST", "GET"])
def second_agent_in_conf():
    response = twiml.Response()
    with response.dial() as r:
        conference_name = "xfer"
        r.conference(conference_name)
    return str(response)

# Put the customer into the conference with our colleague
@app.route("/customer_to_conf", methods=['POST','GET'])
def customer_to_conf():
    response=twiml.Response()
    with response.dial() as r:
        r.conference("xfer")
    return str(response)

if __name__ == '__main__':
    # Note that in production, you would want to disable debugging
    app.run(debug=True)