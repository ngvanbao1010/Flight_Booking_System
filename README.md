# Flight Booking System  

The **Flight Booking System** is a web-based application built with **Python (Flask)**, **MySQL**, and **JavaScript**.  
It allows users to search for flights, book tickets, and manage reservations.  
All flight information is stored in a MySQL database, with support for image uploads via **Cloudinary**.  

---

## ✨ Features  

- **User Registration & Authentication** – Create an account and securely log in to book flights.  
- **Flight Search** – Search available flights by departure, destination, and travel date.  
- **Ticket Booking** – Choose flight options, seat classes, and confirm booking.  
- **Booking Management** – View and manage previously booked tickets.  
- **Cancellation** – Cancel an existing reservation when needed.  

---

## Requirements  

- **Python 3.x**  
- **MySQL 5.x or higher**  
- **MySQL Connector for Python** (`mysql-connector-python`)  
- Other dependencies listed in `requirements.txt`  

---

## Installation  

1. **Clone the repository**  
   ```bash
   git clone https://github.com/haothach/Flight_Booking_Python.git](https://github.com/ngvanbao1010/Flight_Booking_System.git
   cd Flight_Booking_System
   ```

2. **Install dependencies**  
   ```bash
   pip install -r requirements.txt
   ```

3. **Database setup**  
   - Create a MySQL database named `flight`.  
   - Update the database credentials in `__init__.py`.  

---

## Configuration  

Before running the app, replace the placeholders in `__init__.py` with your own credentials:  

```python
app.secret_key = 'your_secret_name'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@your_MySQL_user/flight?charset=utf8mb4" % quote("your_password")

cloudinary.config(
    cloud_name='your_cloud_name',
    api_key='your_api_key',
    api_secret='your_api_secret'
)
```

---

## Project Structure  

```
Flight_Booking_Python/
│── __init__.py       # App initialization & configuration  
│── admin.py          # Admin panel (flights, policies, statistics)  
│── dao.py            # Data access (queries & DB logic)  
│── index.py          # Main routes (search, booking, auth)  
│── models.py         # Database models (User, Flight, Ticket, etc.)  
│── templates/        # HTML templates  
│── static/           # CSS, JS, images  
│── requirements.txt  # Python dependencies  
```

---

## Notes  

- Ensure MySQL is running before starting the app.  
- Default database name is **`flight`** (change in config if needed).  
- Make sure Cloudinary credentials are correctly configured.  
