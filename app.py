from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from flask_socketio import SocketIO
import requests
import json
import plotly.express as px
import plotly

heroku ps:scale web=1.
    
app = Flask(__name__)
app.config['SECRET_KEY'] = 'vnkdjnfjknfl1232#'
socketio = SocketIO(app, verify=False, logger=True, engineio_logger=True, cors_allowed_origins='*')

valid_commands=['']

@app.route('/')
def index():
    return render_template('main.html', forward_message=0)


uri = "http://flaskosa.herokuapp.com/cmd/"

@socketio.on('new_plot', namespace="/test")
def retrieve_data():

                uResponse = requests.get(uri+'TRACE')
                Jresponse = uResponse.text
                data = json.loads(Jresponse)
                wavelength = data['xdata']
                values = data['ydata']
                x=[t + data['xoffset'] for t in wavelength]
                y = [t + data['yoffset'] for t in values]
                fig = px.line(x=x, y=y, labels={'x': data['xlabel']+'('+data['xunits']+')', 'y': data['ylabel']+'('+data['yunits']+')'})
                graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)
                socketio.emit('new_plot', graphJSON, namespace='/test')


scheduler = BackgroundScheduler()
scheduler.add_job(
    func=retrieve_data,
    trigger=IntervalTrigger(seconds=1),
    id='osa_retrieval_job',
    name='Retrieve data every 1seconds',
    replace_existing=True)
scheduler.start()
scheduler.pause()

@socketio.on('command', namespace="/test")
def handle_my_custom_event(json):
    if str(json)=='START':
        flag = True
        while flag:
            uResponse = requests.get(uri + 'START')
            Jresponse = uResponse.text
            if Jresponse[0:6]=='+READY':
                scheduler.resume()
                socketio.emit('command', Jresponse, namespace='/test')
                flag = False

    elif str(json)=='STOP':
        flag = True
        while flag:
            uResponse = requests.get(uri + 'STOP')
            Jresponse = uResponse.text
            if Jresponse[0:6] == '+READY':
                socketio.emit('command', Jresponse, namespace='/test')
                scheduler.pause()
                flag = False

    elif str(json)=='SINGLE':
        flag = True
        while flag:
            uResponse = requests.get(uri + 'SINGLE')
            Jresponse = uResponse.text
            if Jresponse[0:6] == '+READY':
                socketio.emit('command', Jresponse, namespace='/test')
                scheduler.pause()
                retrieve_data()
                flag = False
    else:
        uResponse = requests.get(uri + str(json))
        Jresponse = uResponse.text
        socketio.emit('command', Jresponse, namespace='/test')


@app.route('/api/<string:command>', methods=['GET'])
def get_command(command):
    uResponse = requests.get(uri + command)
    Jresponse = uResponse.text

    if command=='START':
        while Jresponse[0:6] != '+READY':
            uResponse = requests.get(uri + command)
            Jresponse = uResponse.text
        scheduler.resume()

    elif command=='STOP':
        while Jresponse[0:6] != '+READY':
            uResponse = requests.get(uri + command)
            Jresponse = uResponse.text
        scheduler.pause()


    elif command=='SINGLE':
        while Jresponse[0:6] != '+READY':
            uResponse = requests.get(uri + command)
            Jresponse = uResponse.text
        scheduler.pause()
        retrieve_data()
    socketio.emit('command', 'API Request:  '+Jresponse, namespace='/test')
    return Jresponse


if __name__ == '__main__':
    socketio.run(app, debug=True)




