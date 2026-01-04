### Gprog by Глеб Горбачев - Веб-версия ###
from flask import Flask, render_template, request, redirect, flash, jsonify
import sqlite3
import requests
from datetime import datetime
import time

app = Flask(__name__)
app.secret_key = 'gprog-secret-key-2025-2026'

# ====== ВАШ КЛЮЧ ОТКРЫВАЕТСЯ ЗДЕСЬ ======
# Замените этот ключ на свой с OpenWeatherMap
WEATHER_API_KEY = "64cf945715cae56ec19bb48743d374f8"
# =======================================

def get_db_connection():
    conn = sqlite3.connect('notes.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.route('/')
def index():
    conn = get_db_connection()
    notes = conn.execute('SELECT * FROM notes ORDER BY created_at DESC').fetchall()
    conn.close()
    
    # Пробуем получить погоду, если не получается - показываем сообщение
    try:
        weather_data = get_weather_by_city("Москва")
    except Exception as e:
        print(f"Ошибка при получении погоды: {e}")
        weather_data = {"error": "Проверьте API ключ"}
    
    return render_template('index.html', notes=notes, weather=weather_data)

@app.route('/create', methods=['GET', 'POST'])
def create_note():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        
        if not title or not description:
            flash('Пожалуйста, заполните все поля!', 'error')
            return redirect('/create')
        
        conn = get_db_connection()
        conn.execute('INSERT INTO notes (title, description) VALUES (?, ?)',
                    (title, description))
        conn.commit()
        conn.close()
        
        flash('Заметка успешно создана!', 'success')
        return redirect('/')
    
    return render_template('create.html')

@app.route('/delete/<int:note_id>', methods=['POST'])
def delete_note(note_id):
    conn = get_db_connection()
    conn.execute('DELETE FROM notes WHERE id = ?', (note_id,))
    conn.commit()
    conn.close()
    
    flash('Заметка удалена!', 'success')
    return redirect('/')

@app.route('/settings')
def settings():
    return render_template('settings.html')

@app.route('/api/weather/<city>')
def get_weather(city):
    weather_data = get_weather_by_city(city)
    return jsonify(weather_data)

def get_weather_by_city(city):
    """Получение погоды по названию города"""
    
    # Если нет API ключа, возвращаем заглушку
    if WEATHER_API_KEY == "ВАШ_НОВЫЙ_API_КЛЮЧ" or not WEATHER_API_KEY:
        return {
            "city": city,
            "temperature": 20,
            "description": "Тестовые данные - установите API ключ",
            "icon_url": "https://openweathermap.org/img/wn/01d@2x.png",
            "feels_like": 19,
            "humidity": 65,
            "wind_speed": 3.5,
            "is_demo": True
        }
    
    try:
        # Получаем координаты города
        geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city}&limit=1&appid={WEATHER_API_KEY}"
        
        print(f"Запрос геоданных для города: {city}")
        geo_response = requests.get(geo_url, timeout=10)
        
        if geo_response.status_code == 401:
            return {"error": "Неверный API ключ. Получите новый на openweathermap.org"}
        
        if geo_response.status_code != 200:
            return {"error": f"Ошибка API: {geo_response.status_code}"}
        
        geo_data = geo_response.json()
        
        if not geo_data:
            return {"error": f"Город '{city}' не найден"}
        
        lat = geo_data[0]['lat']
        lon = geo_data[0]['lon']
        
        # Получаем погоду
        weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={WEATHER_API_KEY}&units=metric&lang=ru"
        
        print(f"Запрос погоды по координатам: {lat}, {lon}")
        weather_response = requests.get(weather_url, timeout=10)
        
        if weather_response.status_code != 200:
            error_data = weather_response.json()
            return {"error": f"Ошибка погоды: {error_data.get('message', 'Неизвестная ошибка')}"}
        
        weather_data = weather_response.json()
        
        # Форматируем данные
        return {
            "city": weather_data['name'],
            "country": weather_data['sys']['country'],
            "temperature": round(weather_data['main']['temp']),
            "feels_like": round(weather_data['main']['feels_like']),
            "humidity": weather_data['main']['humidity'],
            "pressure": weather_data['main']['pressure'],
            "wind_speed": weather_data['wind']['speed'],
            "description": weather_data['weather'][0]['description'].capitalize(),
            "icon": weather_data['weather'][0]['icon'],
            "icon_url": f"https://openweathermap.org/img/wn/{weather_data['weather'][0]['icon']}@2x.png"
        }
        
    except requests.exceptions.Timeout:
        return {"error": "Таймаут запроса. Проверьте интернет-соединение."}
    except requests.exceptions.ConnectionError:
        return {"error": "Ошибка подключения. Проверьте интернет-соединение."}
    except Exception as e:
        return {"error": f"Произошла ошибка: {str(e)}"}

# Тестовый маршрут для проверки API ключа
@app.route('/test-api')
def test_api():
    """Тестирование API ключа"""
    if WEATHER_API_KEY == "ВАШ_НОВЫЙ_API_КЛЮЧ":
        return "API ключ не установлен. Установите ключ в переменной WEATHER_API_KEY"
    
    test_url = f"https://api.openweathermap.org/data/2.5/weather?q=Moscow&appid={WEATHER_API_KEY}"
    
    try:
        response = requests.get(test_url, timeout=10)
        return f"""
        <h1>Тест API ключа</h1>
        <p>Ключ: {WEATHER_API_KEY[:10]}...</p>
        <p>Статус ответа: {response.status_code}</p>
        <p>Ответ: {response.text[:200]}</p>
        <a href="/">Вернуться на главную</a>
        """
    except Exception as e:
        return f"Ошибка: {e}"

# Альтернативный API для погоды (резервный)
@app.route('/weather/demo/<city>')
def weather_demo(city):
    """Демо-данные погоды (работает без API)"""
    import random
    temps = {
        "москва": 15, "санкт-петербург": 13, "казань": 16,
        "новосибирск": 8, "екатеринбург": 10, "сочи": 22,
        "moscow": 15, "london": 12, "paris": 16, "new york": 18
    }
    
    temp = temps.get(city.lower(), random.randint(5, 25))
    
    return jsonify({
        "city": city.capitalize(),
        "temperature": temp,
        "feels_like": temp - 1,
        "humidity": random.randint(40, 80),
        "wind_speed": round(random.uniform(1, 10), 1),
        "description": ["Ясно", "Облачно", "Небольшая облачность", "Переменная облачность"][random.randint(0, 3)],
        "icon_url": f"https://openweathermap.org/img/wn/0{random.randint(1,4)}d@2x.png",
        "is_demo": True
    })

if __name__ == '__main__':
    print("=" * 50)
    print("Запуск Gprog Notes с погодным модулем")
    print("=" * 50)
    
    if WEATHER_API_KEY == "ВАШ_НОВЫЙ_API_КЛЮЧ":
        print("⚠️  ВНИМАНИЕ: API ключ для погоды не установлен!")
        print("1. Зарегистрируйтесь на https://openweathermap.org/api")
        print("2. Получите бесплатный API ключ")
        print("3. Замените 'ВАШ_НОВЫЙ_API_КЛЮЧ' в app.py на свой ключ")
        print("4. Пока будут использоваться демо-данные")
    else:
        print(f"✅ API ключ установлен: {WEATHER_API_KEY[:8]}...")
    
    print("\nСервер запущен: http://localhost:5000")
    print("=" * 50)
    
    app.run(debug=True, host='0.0.0.0', port=5000)