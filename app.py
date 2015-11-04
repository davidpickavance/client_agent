import os

from flask import Flask
from flask import Response
from flask import request
from flask import render_template
from twilio import twiml
from twilio.rest import TwilioRestClient
from twilio.util import TwilioCapability
from twilio.access_token import AccessToken

# Pull in configuration from system environment variables
TWILIO_ACCOUNT_SID = "AC662af4948fd5a88cbfc48a44a11b0898"
TWILIO_AUTH_TOKEN = "058d7ef7a73e65c526122a5fd9951a4d"
TWILIO_NUMBER = "+14156884963"

# create an authenticated client that can make requests to Twilio for your
# account.
client = TwilioRestClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
xferd = []

# Create a Flask web app
app = Flask(__name__)

# Render the home page
@app.route('/')
def index():
    capability = TwilioCapability(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    capability.allow_client_outgoing("AP17a745dc5cfc4c9dbcc0886594fd1471")
    capability.allow_client_incoming("david")
    token = capability.generate()
    print token
    return render_template("client_browser.html",
                           capability_token=token)

# Handle a POST request to send a text message. This is called via ajax
# on our web page
@app.route('/message', methods=['POST'])
def message():
    # Send a text message to the number provided
    message = client.sms.messages.create(to=request.form['to'],
                                         from_=TWILIO_NUMBER,
                                         body='Good luck on your Twilio quest!')

    # Return a message indicating the text message is enroute
    return 'Message on the way!'

# Handle a POST request to make an outbound call. This is called via ajax
# on our web page
@app.route('/call', methods=['POST'])
def call():
    # Make an outbound call to the provided number from your Twilio number
    call = client.calls.create(to=request.form['to'], from_=TWILIO_NUMBER, 
                               url='http://twimlets.com/message?Message%5B0%5D=http://demo.kevinwhinnery.com/audio/zelda.mp3')

    # Return a message indicating the call is coming
    return 'Call inbound!'

# Generate TwiML instructions for an outbound call
@app.route('/hello')
def hello():
    response = twiml.Response()
    response.say('Hello there! You have successfully configured a web hook.')
    response.say('Good luck on your Twilio quest!', voice='woman')
    return Response(str(response), mimetype='text/xml')

@app.route('/client_call', methods=['GET', 'POST'])
def client_pstn():
    callerID = "+14156884963"
    called_number = request.values.get('tocall')
    response = twiml.Response()
    with response.dial(callerId=callerID, action="/agent_into_conf") as r:
        r.number(called_number)
    return str(response)

@app.route('/transfer', methods=['POST', 'GET'])
def transfer():
    
    call_sid = request.values.get('params[CallSid]')
    child_calls = client.calls.list(parent_call_sid=call_sid)
    if call_sid in xferd:
        for child_call in child_calls:
            client.calls.update(child_call.sid, method="POST",
                                url="http://2deedf27.ngrok.io/customer_to_conf")
    else:

        second_agent_call = client.calls.create(to="+15103320285", from_="+15102543413",
                                                url="http://2deedf27.ngrok.io/second_agent_in_conf")
    #for key, value in request.values.iteritems():
    #    print "%s is %s" % (key, value)
    
    #call = client.calls.get(call_sid)
        
    #print dir(call)
        for child_call in child_calls:
        #print dir(child_call)
            print call_sid
            print child_call.sid
            client.calls.update(child_call.sid, method="POST",
                                url="http://2deedf27.ngrok.io/called_on_hold")
            xferd.append(call_sid)
    return "hello"

@app.route('/called_on_hold', methods=['POST', 'GET'])
def called_on_hold():
    print request.values
    response = twiml.Response()
    with response.dial() as r:
        conference_name = "Hold"
        r.conference(conference_name, endConferenceOnExit=True)
    return str(response)

@app.route('/agent_into_conf', methods=['POST', 'GET'])
def agent_into_conf():
    print "in agent into conf"
    print request.values
    child_sid = request.values.get("DialCallSid")
    child_call = client.calls.get(child_sid)
    response = twiml.Response()
    if child_call.status == "in-progress": 
        with response.dial() as r:
            conference_name = "xfer"
            r.conference(conference_name)
    else:
        response.hangup()
    return str(response)

@app.route("/second_agent_in_conf", methods=["POST", "GET"])
def second_agent_in_conf():
    response = twiml.Response()
    with response.dial() as r:
        conference_name = "xfer"
        r.conference(conference_name)
    return str(response)

@app.route("/customer_to_conf", methods=['POST','GET'])
def customer_to_conf():
    response=twiml.Response()
    with response.dial() as r:
        r.conference("xfer")
    return str(response)

if __name__ == '__main__':
    # Note that in production, you would want to disable debugging
    app.run(debug=True)