import aquests

def test_ws ():
    aquests.ws ("ws://127.0.0.1:5000/websocket/echo", "I'm a Websocket")
    aquests.fetchall ()
