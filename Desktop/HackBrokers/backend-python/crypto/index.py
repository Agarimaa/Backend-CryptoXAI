import os 
from flask import Flask, request, render_template
import cloudinary
import cloudinary.uploader
import pandas as pd
import pandas_ta as ta
import pickle
from datetime import timedelta
import matplotlib.pyplot as plt
import io
import json
from flask_cors import CORS
# from apscheduler.schedulers.background import BackgroundScheduler
import subprocess

app = Flask(__name__)
CORS(app)
 

cloudinary.config(
    cloud_name=os.getenv("CLOUD_NAME"),
    api_key=os.getenv("API_KEY"),
    api_secret=os.getenv("API_SECRET")
)

def image_generate(Type, days):
    with open(Type + '.pkl', 'rb') as f:
        model = pickle.load(f)
    
    df = pd.read_csv(Type + '.csv', usecols=['Date', 'Close'])
    df['Date'] = pd.to_datetime(df['Date'], infer_datetime_format=True)
    for i in range(2):
        sma = ta.sma(df['Close'], length=5).iloc[-1]
        ema = ta.ema(df['Close'], length=5).iloc[-1]
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        new_close = model.predict([[sma, ema, rsi]])
        new_date = df['Date'].iloc[-1] + timedelta(days=1)
        new_row = {
            "Date": new_date,
            "Close": new_close,
            "SMA": sma,
            "EMA": ema,
            "RSI": rsi
        }

        df = pd.concat([df, pd.DataFrame(new_row)], ignore_index=True)
    last_days = df.tail(days)
    
    plt.style.use('dark_background')
    plt.figure(figsize=(12, 6))
    plt.plot(last_days['Date'][:-2], last_days['Close'][:-2], linestyle='-', color='b') # original value
    plt.plot(last_days['Date'][-3:], last_days['Close'][-3:], linestyle='-', color='r', marker='o') # predicted value
    plt.title(Type.upper() + ' Close Prices Over Time')
    plt.xlabel('Date')
    plt.ylabel('Close Price')
    plt.grid(True)
    img_data = io.BytesIO()
    plt.savefig(img_data, format='png')
    img_data.seek(0)
    return img_data

@app.after_request
def add_cors_headers(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['GET'])
def upload():
    Type = request.args.get('type')
    days = int(request.args.get('days'))
    img = image_generate(Type, days)
    response = cloudinary.uploader.upload(img)
    print(response)
    file_path = "probabilities_" + str(Type) + '.csv'
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        probability_increase = round(df.iloc[0]['Probability of Increase'], 4)
        probability_decrease = round(df.iloc[0]['Probability of Decrease'], 4)
    else:
        probability_decrease = 0.603
        probability_increase = 0.396
    secure_url_json = json.dumps({'secure_url': response['secure_url'], 'probability_increase' : probability_increase, 'probability_decrease' : probability_decrease})
    return secure_url_json

@app.route('/train_model')
def schedule_model_training():
    subprocess.run(['python', 'train_model.py'])  
    return "Model is successfully trained again"

if __name__ == '__main__': 
    # scheduler.add_job(func=schedule_model_training, trigger='date', run_date=datetime.now() + timedelta(hours=24))
    # scheduler.start()
    app.run(port=5000, debug=True)
