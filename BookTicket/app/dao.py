import datetime

from app.models import User, Province, Airport, Flight, FlightRoute, FlightSchedule, TicketClass, Seat, SeatAssignment, \
    Airplane, IntermediateAirport, Receipt, ReceiptDetail, Policy
from app import app, db
import hashlib
import cloudinary.uploader
import sqlite3, pymysql
from datetime import timedelta, datetime
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import func, text, and_
from flask_login import current_user
from sqlalchemy.sql import extract
# function connect to database
from sqlalchemy import func, case, text
from sqlalchemy.orm import aliased


def load_province():
    return Province.query.order_by('name').all()


def load_airport():
    return Airport.query.order_by('id').all()


def load_flight():
    return Flight.query.order_by('id').all()


def load_unique_flights():
    # Truy vấn tất cả các chuyến bay với flight_code duy nhất
    flights = db.session.query(Flight.flight_code).distinct(Flight.flight_code).all()

    return flights


def get_dep_time(flight_id):
    return db.session.query(FlightSchedule.dep_time).filter(FlightSchedule.flight_id == flight_id).all()


def get_flight(code):
    return db.session.query(Flight.id).filter(Flight.flight_code == code).all()


def load_flight_routes(flight_id):
    return db.session.query(
        FlightRoute.dep_airport_id,
        FlightRoute.des_airport_id,
    ).join(
        Flight, FlightRoute.id == Flight.flight_route_id
    ).filter(
        Flight.id == flight_id
    ).all()


def get_latest_policy():
    return Policy.query.order_by(Policy.id.desc()).first()


def load_ariplane():
    return Airplane.query.order_by('id').all()


def get_flight_by_id(flight_id):
    return db.session.query(Flight).options(
        joinedload(Flight.inter_airports),
        joinedload(Flight.flight_schedules)
    ).filter(Flight.id == flight_id).first()


def add_user(name, username, password, avatar):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    u = User(name=name, username=username, password=password,
             avatar="https://res.cloudinary.com/dxxwcby8l/image/upload/v1691062682/tkeflqgroeil781yplxt.jpg")

    if avatar:
        res = cloudinary.uploader.upload(avatar)
        print(res)
        u.avatar = res.get("secure_url")

    db.session.add(u)
    db.session.commit()


def auth_user(username, password, role=None):
    password = str(hashlib.md5(password.encode('utf-8')).hexdigest())

    u = User.query.filter(User.username.__eq__(username),
                          User.password.__eq__(password))

    if role:
        u = u.filter(User.user_role.__eq__(role))

    return u.first()


def get_user_by_id(id):
    return User.query.get(id)



def load_flights(departure, destination, departure_date):
    # Khai báo các alias cho các bảng
    departure_airport = aliased(Airport)
    destination_airport = aliased(Airport)
    departure_province = aliased(Province)
    destination_province = aliased(Province)

    # Subquery để lấy thông tin các sân bay trung gian
    ranked_airports = aliased(
        db.session.query(
            IntermediateAirport.flight_id.label('flight_id'),
            Airport.name.label('airport_name'),
            IntermediateAirport.stop_time.label('stop_time'),
            func.row_number().over(
                partition_by=IntermediateAirport.flight_id,
                order_by=IntermediateAirport.stop_time
            ).label('rn')
        ).join(Airport, IntermediateAirport.airport_id == Airport.id)
        .filter(IntermediateAirport.stop_time.isnot(None))
        .subquery()
    )

    # Truy vấn chính
    query = db.session.query(
        Flight.flight_code.label('flight_code'),
        FlightSchedule.business_class_price.label('business_price'),
        FlightSchedule.economy_class_price.label('economy_price'),
        departure_airport.name.label('departure_airport'),
        destination_airport.name.label('destination_airport'),
        FlightSchedule.dep_time.label('departure_time'),
        func.date_add(
            FlightSchedule.dep_time,
            text("INTERVAL flight_schedule.flight_time MINUTE")
        ).label('arrival_time'),
        FlightSchedule.flight_time.label('flight_time'),
        Airplane.name.label('airplane_name'),
        Airplane.airplane_type.label('airline_name'),
        db.session.query(func.count())
        .filter(
            SeatAssignment.flight_schedule_id == FlightSchedule.id,
            SeatAssignment.is_available == True,
            Seat.seat_class == TicketClass.Business_Class,
            SeatAssignment.seat_id == Seat.id
        ).scalar_subquery().label('remaining_business_seats'),
        db.session.query(func.count())
        .filter(
            SeatAssignment.flight_schedule_id == FlightSchedule.id,
            SeatAssignment.is_available == True,
            Seat.seat_class == TicketClass.Economy_Class,
            SeatAssignment.seat_id == Seat.id
        ).scalar_subquery().label('remaining_economy_seats'),
        Flight.id.label('flight_id'),
        FlightSchedule.id.label('flight_schedule_id'),  # Thêm flight_schedule_id
        # Intermediate airports
        func.max(
            case(
                (ranked_airports.c.rn == 1, ranked_airports.c.airport_name)
            )
        ).label('intermediate_airport_1'),
        func.max(
            case(
                (ranked_airports.c.rn == 1, ranked_airports.c.stop_time)
            )
        ).label('ia_stop_time_1'),
        func.max(
            case(
                (ranked_airports.c.rn == 2, ranked_airports.c.airport_name)
            )
        ).label('intermediate_airport_2'),
        func.max(
            case(
                (ranked_airports.c.rn == 2, ranked_airports.c.stop_time)
            )
        ).label('ia_stop_time_2')
    ).join(
        FlightSchedule, Flight.id == FlightSchedule.flight_id
    ).join(
        FlightRoute, Flight.flight_route_id == FlightRoute.id
    ).join(
        departure_airport, FlightRoute.dep_airport_id == departure_airport.id
    ).join(
        destination_airport, FlightRoute.des_airport_id == destination_airport.id
    ).join(
        Airplane, Flight.airplane_id == Airplane.id
    ).join(
        departure_province, departure_airport.province_id == departure_province.id
    ).join(
        destination_province, destination_airport.province_id == destination_province.id
    ).outerjoin(
        ranked_airports, ranked_airports.c.flight_id == Flight.id
    ).filter(
        departure_province.name == departure,
        destination_province.name == destination,
        func.date(FlightSchedule.dep_time) == departure_date
    ).group_by(
        Flight.flight_code,
        FlightSchedule.business_class_price,
        FlightSchedule.economy_class_price,
        departure_airport.name,
        destination_airport.name,
        FlightSchedule.dep_time,
        FlightSchedule.flight_time,
        Airplane.name,
        Airplane.airplane_type,
        Flight.id,
        FlightSchedule.id
    )

    # Thực thi truy vấn
    results = query.all()

    # Chuyển đổi kết quả thành danh sách dictionary
    flights = [
        {
            "flight_code": row[0],  # Mã chuyến bay
            "business_price": row[1],  # Giá vé hạng 1
            "economy_price": row[2],  # Giá vé hạng 2
            "departure_airport": row[3],  # Sân bay đi
            "destination_airport": row[4],  # Sân bay đến
            "departure_time": row[5],  # Giờ khởi hành
            "arrival_time": row[6],  # Giờ đến
            "flight_time": format_flight_time(row[7]),  # Thời gian bay
            "airplane_name": row[8],  # Tên máy bay
            "airline_name": row[9],  # Tên hãng hàng không
            "remaining_business_seats": row[10],  # Số ghế hạng 1 còn lại
            "remaining_economy_seats": row[11],  # Số ghế hạng 2 còn lại
            "flight_id": row[12],  # ID chuyến bay
            "flight_schedule_id": row[13],  # ID lịch bay
            "intermediate_airport_1": row[14],  # Sân bay trung gian 1
            "ia_stop_time_1": row[15],  # Thời gian dừng tại sân bay trung gian 1
            "intermediate_airport_2": row[16],  # Sân bay trung gian 2
            "ia_stop_time_2": row[17],  # Thời gian dừng tại sân bay trung gian 2
        }
        for row in results
    ]

    return flights



def get_available_seats_by_row(flight_id, seat_class):
    # Lấy tất cả các ghế trống theo flight_id và seat_class
    available_seats = db.session.query(Seat).join(SeatAssignment).join(FlightSchedule) \
        .filter(
            FlightSchedule.flight_id == flight_id,
            SeatAssignment.is_available == True,
            Seat.seat_class == seat_class
        ).options(joinedload(Seat.seat_assignments)).all()

    # Nhóm ghế theo hàng
    rows = {}
    for seat in available_seats:
        # Tách số hàng và chữ ghế (ví dụ E1A => row=1, seat_code='A')
        row_number = int(seat.seat_code[1:-1])  # lấy phần số của mã ghế (E1A => 1)
        seat_code = seat.seat_code[-1]  # lấy phần chữ của mã ghế (E1A => A)

        if row_number not in rows:
            rows[row_number] = []

        rows[row_number].append(seat_code)

    return rows


def get_available_seats(flight_id, seat_class):
    return db.session.query(Seat).join(SeatAssignment).join(FlightSchedule) \
        .filter(
        FlightSchedule.flight_id == flight_id,
        SeatAssignment.is_available == True,
        Seat.seat_class == seat_class
    ).options(joinedload(Seat.seat_assignments)).all()


def format_flight_time(flight_time):
    if flight_time < 60:
        return f"{flight_time} phút"
    else:
        hours = flight_time // 60
        minutes = flight_time % 60
        return f"{hours} giờ {str(minutes).zfill(2)} phút"


def get_max_seat(flight_id):
    return db.session.query(
        Airplane.business_class_seat_size,
        Airplane.economy_class_seat_size
    ).join(
        Flight, Flight.airplane_id == Airplane.id
    ).filter(
        Flight.id == flight_id
    ).first()


def find_flight_route(dep_id, des_id):
    return FlightRoute.query.filter_by(
        dep_airport_id=dep_id,
        des_airport_id=des_id
    ).first()


def get_flight_by_code_and_airports(flight_code, dep_airport_id, des_airport_id):
    return db.session.query(Flight.id).join(
        FlightRoute, FlightRoute.id == Flight.flight_route_id
    ).filter(
        Flight.flight_code.__eq__(flight_code),
        FlightRoute.dep_airport_id == dep_airport_id,
        FlightRoute.des_airport_id == des_airport_id
    ).first()


def revenue_stats():
    # Alias cho bảng Airport và Province
    dep_airport = aliased(Airport)  # Sân bay đi
    des_airport = aliased(Airport)  # Sân bay đến
    dep_province = aliased(Province)  # Tỉnh nơi đi
    des_province = aliased(Province)  # Tỉnh nơi đến

    return (db.session.query(
                FlightRoute.id.label('flight_route_id'),
                func.sum(ReceiptDetail.quantity * ReceiptDetail.unit_price),
                dep_province.name,
                des_province.name
            )
            .join(ReceiptDetail, ReceiptDetail.flight_route_id == FlightRoute.id)
            .join(dep_airport, dep_airport.id == FlightRoute.dep_airport_id)
            .join(dep_province, dep_province.id == dep_airport.province_id)
            .join(des_airport, des_airport.id == FlightRoute.des_airport_id)
            .join(des_province, des_province.id == des_airport.province_id)
            .group_by(
                FlightRoute.id,  # Nhóm theo ID tuyến bay
                dep_province.name,  # Nhóm theo tên tỉnh nơi đi
                des_province.name  # Nhóm theo tên tỉnh nơi đến
            )
            .all())


def revenue_month(time='month', year=datetime.now().year):
    return db.session.query(
                func.extract(time, Receipt.created_date),
                func.sum(ReceiptDetail.quantity * ReceiptDetail.unit_price)
            )\
            .join(ReceiptDetail, ReceiptDetail.receipt_id == Receipt.id) \
            .filter(func.extract("year", Receipt.created_date) == year) \
            .group_by(func.extract(time, Receipt.created_date)) \
            .order_by(func.extract(time, Receipt.created_date)) \
            .all()


def revenue_year(time='year'):
    return db.session.query(
        func.extract(time, Receipt.created_date),
        func.sum(ReceiptDetail.quantity * ReceiptDetail.unit_price)
    ).join(
        ReceiptDetail, ReceiptDetail.receipt_id == Receipt.id
    ).group_by(
        func.extract(time, Receipt.created_date)
    ).order_by(
        func.extract(time, Receipt.created_date)
    ).all()


if __name__ == '__main__':
    with app.app_context():
        print(load_flight_routes('11'))