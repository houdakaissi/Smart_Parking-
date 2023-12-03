import serial
import logging
from flask import Flask, render_template, request, redirect, url_for,flash,jsonify,Response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime 
from datetime import timedelta
import secrets
from ssl import ALERT_DESCRIPTION_ACCESS_DENIED
import cv2
import os
import pytesseract
from PIL import Image



app = Flask(__name__)

ser = serial.Serial('COM4', 9600)

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:@localhost/parking'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = "..." # entrer votre secret key 

db = SQLAlchemy(app)



static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
captures_folder = os.path.join(static_folder, 'captures')

if not os.path.exists(captures_folder):
    os.makedirs(captures_folder)

# Use the appropriate index for your USB camera
camera = cv2.VideoCapture(0) 

def get_remaining_time(end_datetime):
    now = datetime.utcnow()
    remaining_time = end_datetime - now
    days, seconds = divmod(remaining_time.seconds + remaining_time.days * 86400, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    return f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds"


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    subscriptions = db.relationship('Subscription', backref='user', lazy=True)

class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    matricule = db.Column(db.String(20),unique=True, nullable=False, index=True)  # Added unique=True and index=True
    model = db.Column(db.String(50), nullable=False)
    subscriptions = db.relationship('Subscription', backref='car', lazy=True)

class Subscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    car_matricule = db.Column(db.String(20), db.ForeignKey('car.matricule'), nullable=False)
    
    def is_expired(self):
        return False
    

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

def save_image(frame):
    image_name = f"captured_image_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
    image_path = os.path.join(captures_folder, image_name)
    
    with open(image_path, "wb") as f:
        f.write(frame)
    
    return image_path

def extract_text(image_path):
    # Configure logging
    logging.basicConfig(level=logging.INFO)  # Adjust the log level as needed

    # Perform OCR using pytesseract
    action = 0
    try:
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Adjust the path accordingly
        text = pytesseract.image_to_string(image_path, lang='eng').lower()
        logging.info("Extracted text: %s", text)

        current_time = datetime.now()
        subscription = Subscription.query.filter_by(car_matricule=text.strip()).first()
        
        if subscription and current_time >= subscription.start_datetime:
                result_message = "Vous êtes abonné(e), bienvenu!"
                action = 1
                
        elif subscription and current_time < subscription.start_datetime:
                result_message = "Vous devez attendre jusqu'à ce que la date d'abonnement arrive!"
                action = -1
                
        else:
                result_message = "Vous n'êtes pas abonné(e)!"
                action = 0
                
            
       
    except Exception as e:
        result_message = f"Error during OCR: {str(e)}"
        logging.error(f"Serial not passed: {result_message}")

   

    return result_message, action




@app.route('/')
def index():
    users = User.query.all()
    cars = Car.query.all()
    return render_template('index.html', users=users,cars=cars)

@app.route('/subscribe', methods=['POST'])
def subscribe():
    username = request.form['username']
    matricule = request.form['matricule']
    model = request.form['model']
    start_date = request.form['start_date']
    start_time = request.form['start_time']
    end_date = request.form['end_date']
    end_time = request.form['end_time']

    start_datetime = datetime.strptime(f'{start_date} {start_time}', '%Y-%m-%d %H:%M')
    end_datetime = datetime.strptime(f'{end_date} {end_time}', '%Y-%m-%d %H:%M')

    # Check if a subscription with the same matricule exists
    existing_subscription = Subscription.query.join(Car).filter(
        
        Car.matricule == matricule,
        Subscription.end_datetime > datetime.utcnow()
    ).first()

    if existing_subscription:
        flash('Error: A subscription with the same matricule already exists.', 'error')
        return render_template('subscribtion.html')
    else:
        user = User.query.filter_by(username=username).first()
        if not user:
          user = User(username=username)
          db.session.add(user)
          db.session.commit()

        car = Car.query.filter_by(matricule=matricule).first()
        if not car:
          car = Car(matricule=matricule, model=model)
          db.session.add(car)
          db.session.commit()

        subscription = Subscription(start_datetime=start_datetime, end_datetime=end_datetime, user=user, car=car)
        db.session.add(subscription)
        db.session.commit()
    return redirect(url_for('index'))
    


@app.route('/subscribtio')
def subscribtio():
    return render_template('subscribtion.html')


@app.route('/delete_subscription/<subscription_id>', methods=['DELETE'])
def delete_subscription(subscription_id):
    try:
        subscription = Subscription.query.get(subscription_id)
        if subscription:
            db.session.delete(subscription)
            db.session.commit()
            return jsonify({'message': 'Subscription deleted successfully'}), 200
        else:
            return jsonify({'message': 'Subscription not found'}), 404
    except Exception as e:
        return jsonify({'message': 'Failed to delete subscription', 'error': str(e)}), 500
    

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture_image')
def capture_image():
    _, frame = camera.read()
    ret, buffer = cv2.imencode('.jpg', frame)

    if ret:
        image_path = save_image(buffer.tobytes())
        text = extract_text(image_path)
        if text[1] == 1:
            ser.write(str(1).encode())


        return f"{text[0]}"
    else:
        return "Failed to capture and save image."

    

if __name__ == '__main__':
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Run the Flask development server
    app.run(debug=True)
