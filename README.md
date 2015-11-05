# Transferring a call with Twilio

This code is an example of how to transfer a call using Twilio. It has been written for the
following very specific scenario only:

An agent, using Twilio Client calls a customer. The agent wants to transfer the customer
to a colleague so presses the "Transfer" button on the Client. This puts the customer
on hold and connects the agent to the colleague. After a brief chat, the colleague agrees
to talk to the customer so the agent presses "Transfer" again. The agent, customer and
colleague are all, now, in a three way call. The agent completes the transfer by hanging
up.

Over time, I plan to increase the complexity, and real world applicability, of this demo
by allowing for multiple client connections and multiple concurrent calls. I'm sure my
plans will solidify as I work on them. 


