from email.policy import default

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, Enum, Date, DateTime, event, UniqueConstraint
from sqlalchemy.orm import relationship, validates, backref
from app import db, app
import hashlib
from enum import Enum as RoleEnum
from enum import Enum as AirlineEnum
from enum import Enum as TicketClassEnum
from enum import Enum as GenderEnum
from enum import Enum as MethodEnum
from datetime import datetime
from flask_login import UserMixin
import math


class BaseModel(db.Model):
    __abstract__ = True
    id = Column(Integer, primary_key=True, autoincrement=True)
    # Các id ở dưới kế thừa từ basemodel


class UserRole(RoleEnum):
    ADMIN = 1
    USER = 2
    STAFF = 3


class Airline(AirlineEnum):
    Bamboo_AirWays = 1
    Vietjet_Air = 2
    VietNam_Airline = 3

    def __str__(self):
        return self.name.replace('_', ' ')


class TicketClass(TicketClassEnum):
    Business_Class = 1
    Economy_Class = 2


class Gender(GenderEnum):
    Mr = 1
    Ms = 2


class Method(MethodEnum):
    Momo = 1
    Bank = 2


class User(BaseModel, UserMixin):
    name = Column(String(100), nullable=False)
    username = Column(String(100), nullable=False, unique=True)
    password = Column(String(100), nullable=False)
    avatar = Column(String(100), nullable=True)
    active = Column(Boolean, default=True)
    user_role = Column(Enum(UserRole), default=UserRole.USER)

    tickets = relationship('Ticket', backref='user', lazy=True)
    receipts = relationship('Receipt', backref='user', lazy=True)


class Customer(BaseModel):
    last_name = Column(String(50), nullable=False)
    name = Column(String(50), nullable=False)
    gender = Column(Enum(Gender), nullable=False)
    birthday = Column(Date, nullable=False)

    tickets = relationship('Ticket', backref='customer', lazy=True)


class Province(BaseModel):
    name = Column(String(100), nullable=False)

    airports = relationship('Airport', backref='province', lazy=True)

    def __str__(self):
        return self.name


class Airport(BaseModel):
    name = Column(String(100), nullable=False)
    add = Column(String(100), nullable=False)
    province_id = Column(Integer, ForeignKey(Province.id), nullable=False)

    dep_airports = relationship('FlightRoute', foreign_keys='FlightRoute.dep_airport_id', backref='dep_airport')
    des_airports = relationship('FlightRoute', foreign_keys='FlightRoute.des_airport_id', backref='des_airport')
    intermediate_airports = relationship('IntermediateAirport', backref='airport', lazy=True)

    def __str__(self):
        return f"{self.province.name} ({self.name})"


class FlightRoute(BaseModel):
    dep_airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)
    des_airport_id = Column(Integer, ForeignKey(Airport.id), nullable=False)

    flights = relationship('Flight', backref='flight_route', lazy=True)
    receipt_details = relationship('ReceiptDetail', backref='flight_route', lazy=True)

    @validates('dep_airport_id', 'des_airport_id')
    def validate_airports(self, key, value):
        if key == 'dep_airport_id':
            current_dep_airport = value
            current_des_airport = self._sa_instance_state.dict.get('des_airport_id', None)
        elif key == 'des_airport_id':
            current_des_airport = value
            current_dep_airport = self._sa_instance_state.dict.get('dep_airport_id', None)

        if current_dep_airport is not None and current_des_airport is not None:
            if current_dep_airport == current_des_airport:
                raise ValueError("Nơi đến và nơi đi không được phép giống nhau.")

        return value

    def __str__(self):
        dep_airport_name = self.dep_airport.name
        des_airport_name = self.des_airport.name
        dep_province_name = self.dep_airport.province.name
        des_province_name = self.des_airport.province.name
        return f"{dep_province_name} ({dep_airport_name}) -> {des_province_name} ({des_airport_name})"


class Airplane(BaseModel):
    name = Column(String(100), nullable=False)
    airplane_type = Column(Enum(Airline), nullable=False)
    business_class_seat_size = Column(Integer, nullable=False)
    economy_class_seat_size = Column(Integer, nullable=False)

    flights = relationship('Flight', backref='airplane', lazy=True)
    seats = relationship('Seat', backref='airplane', lazy=True)

    def __str__(self):
        return self.name

    def generate_seats(self):
        seats = []

        seat_letters = ['A', 'B', 'C', 'D', 'E', 'F']  # Các cột từ A đến F

        # Tạo ghế Business
        for row in range(1, math.ceil(self.business_class_seat_size / app.config["NUMBER_ROWS"]) + 1):
            for col_idx, letter in enumerate(seat_letters):
                if len(seats) >= self.business_class_seat_size:  # Dừng nếu đủ số ghế
                    break
                seat_code = f"B{row}{letter}"
                seats.append(Seat(
                    seat_code=seat_code,
                    seat_class=TicketClass.Business_Class,
                    airplane_id=self.id
                ))

        # Tạo ghế Economy
        for row in range(1, math.ceil(self.economy_class_seat_size / 6) + 1):
            for col_idx, letter in enumerate(seat_letters):
                if len(seats) - self.business_class_seat_size >= self.economy_class_seat_size:
                    break
                seat_code = f"E{row}{letter}"
                seats.append(Seat(
                    seat_code=seat_code,
                    seat_class=TicketClass.Economy_Class,
                    airplane_id=self.id
                ))

        # Thêm danh sách ghế vào database
        db.session.add_all(seats)
        db.session.commit()


class Flight(BaseModel):
    flight_code = Column(String(20), nullable=False)
    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)
    airplane_id = Column(Integer, ForeignKey(Airplane.id), nullable=False)

    # Quan hệ
    inter_airports = relationship('IntermediateAirport', backref='flight', lazy=True)
    flight_schedules = relationship('FlightSchedule', backref='flight', lazy=True)

    # Đảm bảo flight_code là duy nhất khi kết hợp với flight_route_id
    __table_args__ = (
        UniqueConstraint('flight_code', 'flight_route_id', name='uix_flight_code_route'),
    )

    def __str__(self):
        return self.flight_code


class FlightSchedule(BaseModel):
    dep_time = Column(DateTime, nullable=False)
    flight_time = Column(Integer, nullable=False)
    business_class_seat_size = Column(Integer, nullable=False)
    economy_class_seat_size = Column(Integer, nullable=False)
    business_class_price = Column(Integer, nullable=False)
    economy_class_price = Column(Integer, nullable=False)

    flight_id = Column(Integer, ForeignKey(Flight.id), nullable=False)

    seat_assignments = relationship('SeatAssignment', backref='flight_schedule', lazy=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        flight_id = kwargs.get('flight_id')
        if flight_id is None:
            raise ValueError("Flight ID must be provided.")

        # Lấy thông tin chuyến bay từ flight_id
        flight = db.session.get(Flight, flight_id)
        if flight is None:
            raise ValueError(f"No flight found with ID {flight_id}.")  # Xử lý nếu không tìm thấy chuyến bay

        # Kiểm tra nếu chuyến bay không có máy bay (airplane)
        airplane = flight.airplane
        if airplane is None:
            raise ValueError("The flight must be associated with an airplane.")  # Xử lý nếu chuyến bay không có máy bay

        # Kiểm tra số lượng ghế hạng business và economy không vượt quá khả năng của máy bay
        if self.business_class_seat_size > airplane.business_class_seat_size:
            raise ValueError(
                f"Số ghế hạng thương gia không được nhỏ hơn số lượng quy định ({airplane.business_class_seat_size})."
            )

        if self.economy_class_seat_size > airplane.economy_class_seat_size:
            raise ValueError(
                f"Số ghế hạng phổ thông không được nhỏ hơn số lượng quy định ({airplane.economy_class_seat_size})."
            )

        policy = db.session.query(Policy).first()
        if policy is None:
            raise ValueError("Policy information is missing. Please check the database.")

        # Kiểm soát flight_time
        if self.flight_time < policy.minimun_flight_time:
            raise ValueError(
                f"Thời gian bay phải ít nhất {policy.minimun_flight_time} minutes."
            )

        #Kiểm soát giá vé
        if self.business_class_price < policy.ticket_price:
            raise ValueError(
                f"Giá vé hạng thương gia không được nhỏ hơn ({policy.ticket_price})."
            )

        if self.economy_class_price < policy.ticket_price:
            raise ValueError(
                f"Giá vé hạng phổ thông không được nhỏ hơn({policy.ticket_price})."
            )

    def create_seat_assignments(self):

        # Lấy đối tượng Flight từ flight_id
        flight = db.session.query(Flight).filter_by(id=self.flight_id).first()

        # Kiểm tra nếu không tìm thấy Flight, thoát ra
        if not flight:
            print(f"Không tìm thấy chuyến bay nào có id là : {self.flight_id} .")
            return

        business_seats = db.session.query(Seat).filter(
            Seat.airplane_id == flight.airplane_id,
            Seat.seat_class == TicketClass.Business_Class
        ).limit(self.business_class_seat_size).all()

        economy_seats = db.session.query(Seat).filter(
            Seat.airplane_id == flight.airplane_id,
            Seat.seat_class == TicketClass.Economy_Class
        ).limit(self.economy_class_seat_size).all()

        # Tạo SeatAssignment cho các ghế business
        for seat in business_seats:
            seat_assignment = SeatAssignment(seat_id=seat.id, flight_schedule_id=self.id, is_available=True)
            db.session.add(seat_assignment)

        # Tạo SeatAssignment cho các ghế economy
        for seat in economy_seats:
            seat_assignment = SeatAssignment(seat_id=seat.id, flight_schedule_id=self.id, is_available=True)
            db.session.add(seat_assignment)

        # Commit vào cơ sở dữ liệu
        db.session.commit()


class Seat(BaseModel):
    seat_code = Column(String(10), nullable=False)
    seat_class = Column(Enum(TicketClass), nullable=False)

    airplane_id = Column(Integer, ForeignKey(Airplane.id), nullable=False)

    seat_assignments = relationship('SeatAssignment', backref='seat', lazy=True)

    def __str__(self):
        return f"{self.seat_code} ({self.seat_class.name})"


class SeatAssignment(BaseModel):
    is_available = Column(Boolean, default=True, nullable=False)
    flight_schedule_id = Column(Integer, ForeignKey(FlightSchedule.id), nullable=False)
    seat_id = Column(Integer, ForeignKey(Seat.id), nullable=False)

    tickets = relationship('Ticket', backref='seat_assignment', lazy=True)

    # Ràng buộc unique để đảm bảo cặp seat_id và flight_schedule_id không trùng lặp
    __table_args__ = (
        UniqueConstraint('seat_id', 'flight_schedule_id', name='uq_seat_flight'),
    )


class IntermediateAirport(db.Model):
    airport_id = Column(Integer, ForeignKey(Airport.id), primary_key=True)
    flight_id = Column(Integer, ForeignKey(Flight.id), primary_key=True)
    stop_time = Column(Integer, default=20)
    note = Column(String(100), nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Lấy flight_id từ kwargs
        flight_id = kwargs.get('flight_id')
        if not flight_id:
            raise ValueError("Mã chuyến bay phải được cung cấp.")

        # Lấy thông tin Policy
        policy = db.session.query(Policy).first()


        # Kiểm tra số lượng sân bay trung gian hiện tại của chuyến bay
        current_inter_airports = db.session.query(IntermediateAirport).filter_by(flight_id=flight_id).count()

        if current_inter_airports >= policy.max_inter_airport:
            raise ValueError(
                f"Không thể tạo nhiều sân bay trung gian hơn nữa.Tối đa chi được {policy.max_inter_airport}.")

        # Kiểm soát giá trị stop_time
        stop_time = kwargs.get('stop_time', self.stop_time)
        if not (policy.minimum_stop_time <= stop_time <= policy.maximum_stop_time):
            raise ValueError(f"Thời gian dừng phải nằm giữa  {policy.minimum_stop_time} phút và "
                             f"{policy.maximum_stop_time} phút.")

    def __str__(self):
        return self.airport.name


class Ticket(BaseModel):
    date_created = Column(DateTime, default=datetime.now())

    seat_assignment_id = Column(Integer, ForeignKey(SeatAssignment.id), nullable=False, unique=True)
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    customer_id = Column(Integer, ForeignKey(Customer.id), nullable=False)
    ticket_class = Column(Enum(TicketClass), nullable=False)


class Policy(BaseModel):
    number_airport = Column(Integer, nullable=False)
    minimun_flight_time = Column(Integer, nullable=False)
    max_inter_airport = Column(Integer, nullable=False)
    minimum_stop_time = Column(Integer, nullable=False)
    maximum_stop_time = Column(Integer, nullable=False)
    number_ticket_class = Column(Integer, nullable=False)
    ticket_price = Column(Integer, nullable=False)
    ticket_sell_time = Column(Integer, nullable=False)
    ticket_booking_time = Column(Integer, nullable=False)


class Receipt(BaseModel):
    user_id = Column(Integer, ForeignKey(User.id), nullable=False)
    total = Column(Integer, nullable=False)
    method = Column(Enum(Method), nullable=False)
    created_date = Column(DateTime, default=datetime.now())

    receipt_details = relationship('ReceiptDetail', backref='receipt', lazy=True)


class ReceiptDetail(BaseModel):
    quantity = Column(Integer, default=0)
    unit_price = Column(Integer, default=0)
    receipt_id = Column(Integer, ForeignKey(Receipt.id), nullable=False, unique=True)

    flight_route_id = Column(Integer, ForeignKey(FlightRoute.id), nullable=False)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        new_policy = Policy(
            number_airport=10,  # Số lượng sân bay tối đa
            minimun_flight_time=30,  # Thời gian bay tối thiểu 30 phút
            max_inter_airport=2,  # Số sân bay trung gian tối đa
            minimum_stop_time=20,  # Thời gian dừng tối thiểu tại sân bay trung gian
            maximum_stop_time=30,  # Thời gian dừng tối đa tại sân bay trung gian
            number_ticket_class=2,  # Số hạng vé (2 hạng vé)
            ticket_price=1000000,  # Giá vé (ví dụ: 1000 là đơn vị tiền tệ)
            ticket_sell_time=4,  # Thời gian bán vé (ví dụ: 1440 phút = 1 ngày)
            ticket_booking_time=12,  # Thời gian đặt vé (ví dụ: 240 phút = 4 giờ trước khi chuyến bay)
        )
        # Thêm vào session và commit
        db.session.add(new_policy)

        u1 = User(name="admin", username="admin", password=str(hashlib.md5("123456".encode('utf-8')).hexdigest()),
                  avatar="https://res.cloudinary.com/dnoubiojc/image/upload/v1735048518/admin.jpg",
                  user_role=UserRole.ADMIN)
        u2 = User(name="staff", username="staff", password=str(hashlib.md5("123456".encode('utf-8')).hexdigest()),
                  avatar="https://res.cloudinary.com/dnoubiojc/image/upload/v1735048587/staff.jpg",
                  user_role=UserRole.STAFF)

        u3 = User(name="user", username="user", password=str(hashlib.md5("123456".encode('utf-8')).hexdigest()),
                  avatar="https://res.cloudinary.com/dnoubiojc/image/upload/v1735048551/user.png",
                  user_role=UserRole.USER)

        db.session.add(u1)
        db.session.add(u2)
        db.session.add(u3)
        db.session.commit()
        provinces = [
            {"name": "TP HCM"},
            {"name": "Hà Nội"},
            {"name": "Đà Nẵng" },
            {"name": "Nghệ An"},
            {"name": "Cần Thơ"},
            {"name": "Hải Phòng"},
            {"name": "Lâm Đồng"},
            {"name": "Quảng Ninh"},
            {"name": "Khánh Hòa"},
            {"name": "Đồng Nai"}
        ]

        for p in provinces:
            p = Province(**p)
            db.session.add(p)
        db.session.commit()

        airports = [
            {"name": "Tân Sơn Nhất", "add": "Phường 2, 4 và 15, Quận Tân Bình", "province_id": 1},
            {"name": "Nội Bài", "add": "Số 200 đường Phạm Văn Đồng, Hà Nội", "province_id": 2},
            {"name": "Đà Nẵng", "add": "Số 02 đường Duy Tân, Quận Hải Châu, Đà Nẵng", "province_id": 3},
            {"name": "Vinh", "add": "Số 1 đường Nguyễn Sỹ Sách, TP Vinh, Nghệ An", "province_id": 4},
            {"name": "Cần Thơ", "add": "Số 60 đường Mậu Thân, Cần Thơ", "province_id": 5},
            {"name": "Cát Bì", "add": "Số 15 đường Nguyễn Đức Cảnh, Hải Phòng", "province_id": 6},
            {"name": "Liên Khương", "add": "Xã Liên Nghĩa, Huyện Đức Trọng, Lâm Đồng", "province_id": 7},
            {"name": "Vân Đồn", "add": "Số 28 đường Vân Đồn, Quảng Ninh", "province_id": 8},
            {"name": "Cam Ranh", "add": "Sân bay Cam Ranh, Phường Cam Nghĩa, TP Cam Ranh, Khánh Hòa", "province_id": 9},
            {"name": "Long Thành", "add": "Xã Long Thanh, Huyện Long Thành, tỉnh Đồng Nai", "province_id": 10},
        ]

        for a in airports:
            a = Airport(**a)
            db.session.add(a)

        # Chuyển đổi dữ liệu từ danh sách airplanes thành các đối tượng Airplane
        airplanes = [
            {
                "name": "Airbus A320",
                "airplane_type": Airline.VietNam_Airline,
                "business_class_seat_size": 5 * 4,  # 5 hàng * 4 ghế/hàng
                "economy_class_seat_size": 10 * 6,  # 20 hàng * 6 ghế/hàng
            },
            {
                "name": "Boeing 787",
                "airplane_type": Airline.Bamboo_AirWays,
                "business_class_seat_size": 5 * 5,
                "economy_class_seat_size": 10 * 7,
            },
            {
                "name": "Airbus A321",
                "airplane_type": Airline.Vietjet_Air,
                "business_class_seat_size": 6 * 4,
                "economy_class_seat_size": 14 * 6,
            },
            {
                "name": "Boeing 737",
                "airplane_type": Airline.VietNam_Airline,
                "business_class_seat_size": 4 * 4,
                "economy_class_seat_size": 10 * 6,
            },
            {
                "name": "Airbus A380",
                "airplane_type": Airline.Bamboo_AirWays,
                "business_class_seat_size": 5 * 6,
                "economy_class_seat_size": 8 * 8,
            },
            {
                "name": "Boeing 777",
                "airplane_type": Airline.VietNam_Airline,
                "business_class_seat_size": 5 * 5,
                "economy_class_seat_size": 7 * 7,
            },
            {
                "name": "Embraer E195",
                "airplane_type": Airline.Vietjet_Air,
                "business_class_seat_size": 5 * 4,
                "economy_class_seat_size": 8 * 6,
            }
        ]

        for ap in airplanes:
            # Tạo đối tượng Airplane
            airplane = Airplane(**ap)

            # Thêm vào session và commit để lấy `id`
            db.session.add(airplane)
            db.session.commit()

            # Gọi hàm generate_seats sau khi `id` đã được gán
            airplane.generate_seats()

        flight_routes = [
            {"dep_airport_id": 1, "des_airport_id": 2},  # Tuyến bay từ Tân Sơn Nhất đến Nội Bài
            {"dep_airport_id": 2, "des_airport_id": 3},  # Tuyến bay từ Nội Bài đến Đà Nẵng
            {"dep_airport_id": 3, "des_airport_id": 4},  # Tuyến bay từ Đà Nẵng đến Vinh
            {"dep_airport_id": 4, "des_airport_id": 5},  # Tuyến bay từ Vinh đến Cần Thơ
            {"dep_airport_id": 1, "des_airport_id": 6},  # Tuyến bay từ Tân Sơn Nhất đến Hải Phòng
            {"dep_airport_id": 6, "des_airport_id": 7},  # Tuyến bay từ Hải Phòng đến Đà Lạt
            {"dep_airport_id": 7, "des_airport_id": 8},  # Tuyến bay từ Đà Lạt đến Quảng Ninh
            {"dep_airport_id": 8, "des_airport_id": 1}  # Tuyến bay từ Quảng Ninh về Tân Sơn Nhất
        ]

        for route in flight_routes:
            flight_route = FlightRoute(**route)
            db.session.add(flight_route)

        # Thêm dữ liệu vào bảng Flight
        flights = [
            {"flight_code": "VN123", "flight_route_id": 1, "airplane_id": 1},
            {"flight_code": "VJ456", "flight_route_id": 2, "airplane_id": 2},
            {"flight_code": "BB789", "flight_route_id": 3, "airplane_id": 3},
            {"flight_code": "VN101", "flight_route_id": 4, "airplane_id": 4},
            {"flight_code": "BB202", "flight_route_id": 5, "airplane_id": 5},
            {"flight_code": "VJ303", "flight_route_id": 1, "airplane_id": 6}
        ]

        for flight in flights:
            f = Flight(**flight)
            db.session.add(f)

        # Thêm dữ liệu vào bảng FlightSchedule

        flight_schedules = [
            {
                "dep_time": datetime(2024, 12, 30, 8, 30),
                "flight_time": 120,
                "flight_id": 1, #---------TPHCM-Ha Noi
                "business_class_seat_size": 15,
                "economy_class_seat_size": 55,
                "business_class_price": 1800000,  # Giá business cao hơn economy
                "economy_class_price": 1500000
            },
            {
                "dep_time": datetime(2024, 12, 30, 10, 0),
                "flight_time": 90,
                "flight_id": 2, #---------Nội Bài đến Đà Nẵng
                "business_class_seat_size": 25,
                "economy_class_seat_size": 60,
                "business_class_price": 3300000,  # Giá business cao hơn economy
                "economy_class_price": 3000000
            },
            {
                "dep_time": datetime(2024, 12, 30, 12, 0),
                "flight_time": 80,
                "flight_id": 3,#----------Đà Nẵng đến Vinh
                "business_class_seat_size": 20,
                "economy_class_seat_size": 70,
                "business_class_price": 1800000,  # Giá business cao hơn economy
                "economy_class_price": 1500000
            },
            {
                "dep_time": datetime(2024, 12, 30, 15, 0),
                "flight_time": 100,
                "flight_id": 4,#-----------Vinh đến Cần Thơ
                "business_class_seat_size": 15,
                "economy_class_seat_size": 50,
                "business_class_price": 2200000,  # Giá business cao hơn economy
                "economy_class_price": 2000000
            },
            {
                "dep_time": datetime(2024, 12, 30, 8, 0),
                "flight_time": 130,
                "flight_id": 5,#----------Tân Sơn Nhất đến Hải Phòng
                "business_class_seat_size": 30,
                "economy_class_seat_size": 60,
                "business_class_price": 6000000,  # Giá business cao hơn economy
                "economy_class_price": 5500000
            },
            {
                "dep_time": datetime(2024, 12, 30, 14, 0),
                "flight_time": 95,
                "flight_id": 6,
                "business_class_seat_size": 20,
                "economy_class_seat_size": 45,
                "business_class_price": 1800000,  # Giá business cao hơn economy
                "economy_class_price": 1500000
            }
        ]

        for schedule in flight_schedules:
            flight_schedule = FlightSchedule(**schedule)
            db.session.add(flight_schedule)
            flight_schedule.create_seat_assignments()

        # Thêm dữ liệu vào bảng IntermediateAirport
        intermediate_airports = [
            {"airport_id": 3, "flight_id": 1, "stop_time": 30, "note": "Dừng đón khách"},
            # Dừng trung gian tại Đà Nẵng trong tuyến Tân Sơn Nhất - Nội Bài
            {"airport_id": 4, "flight_id": 2, "stop_time": 25, "note": "Chờ tiếp nhiên liệu"},
            # Dừng trung gian tại Vinh trong tuyến Nội Bài - Đà Nẵng
            {"airport_id": 2, "flight_id": 3, "stop_time": 20, "note": "Kiểm tra kỹ thuật"},
            # Dừng trung gian tại Nội Bài trong tuyến Đà Nẵng - Vinh
            {"airport_id": 1, "flight_id": 4, "stop_time": 25, "note": "Thay đổi phi hành đoàn"},
            # Dừng trung gian tại Tân Sơn Nhất trong tuyến Vinh - Cần Thơ
            {"airport_id": 2, "flight_id": 4, "stop_time": 25, "note": "Thay đổi phi hành đoàn"}
        ]

        for intermediate in intermediate_airports:
            inter_airport = IntermediateAirport(**intermediate)
            db.session.add(inter_airport)

        db.session.commit()
