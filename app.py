from labsuite.protocol import Protocol

from flask import Flask, render_template
from flask_socketio import SocketIO, emit

import logging
import math

protocol = Protocol()
motor_handler = protocol.attach_motor()
protocol.add_instrument('B', 'p200')
protocol.add_container('A1', 'microplate.96')
protocol.add_container('C1', 'tiprack.p200')
protocol.add_container('B2', 'point.trash')
protocol.calibrate('A1', x=1, y=2, top=3, bottom=13)
protocol.calibrate('A1:A2', bottom=5)
protocol.calibrate('C1', x=100, y=100, top=50)
protocol.calibrate('B2', x=200, y=250, top=15)
protocol.calibrate_instrument('B', top=0, blowout=10, droptip=25)
protocol.transfer('A1:A1', 'A1:A2', ul=100)
protocol.transfer('A1:A2', 'A1:A3', ul=80)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)-8s %(message)s',
    datefmt='%d-%m-%y %H:%M:%S'
)

app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent')


@app.route('/')
def index():
    return render_template('index.html', async_mode=socketio.async_mode)


@socketio.on('move')
def handle_move(coords):
    for k in coords:
        coords[k] = int(coords[k])
    motor_handler.move_motors(**coords)


@socketio.on('calibrate_container')
def handle_container_calibration(data):
    protocol.calibrate(
        data.get('position'),
        axis=data.get('axis', None),
        x=int(data.get('x', 0)),
        y=int(data.get('y', 0)),
        top=int(data.get('top', 0)),
        bottom=int(data.get('bottom', 0))
    )
    print("Calibrated", data.get('axis'))


@socketio.on('calibrate_instrument')
def handle_container_calibration(data):
    protocol.calibrate_instrument(
        data.get('axis'),
        top=int(data.get('top', 0)),
        droptip=int(data.get('droptip', 0)),
        bottom=int(data.get('bottom', 0)),
        blowout=int(data.get('blowout', 0))
    )


@socketio.on('connect_serial')
def handle_connect_serial(data):
    motor_handler.connect(data['port'])
    motor_handler.move_motors(x=10, y=10, z=10)


@socketio.on('disconnect_serial')
def handle_disconnect_serial():
    motor_handler.disconnect()


def protocol_thread(protocol):
    logging.debug("Starting protocol.")
    for current, total in protocol.run():
        progress = math.floor(current / total * 100)
        socketio.emit(
            'protocol_progress',
            {'current': current, 'total': total}
        )
        logging.debug("Running next...")
        logging.debug(
            "Percent complete is {}.".format(progress)
        )
    logging.debug("Protocol Run complete.")


@socketio.on('start_protocol')
def run_protocol():
    logging.debug("Running protocol")
    emit("protocol_start")
    socketio.start_background_task(protocol_thread, protocol)

if __name__ == '__main__':
    socketio.run(app, debug=True)
