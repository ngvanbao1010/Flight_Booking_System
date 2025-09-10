import hashlib
import string
from urllib.parse import quote, unquote
from flask import render_template, request, redirect, flash, jsonify, url_for, session
from app import admin
import dao
import base64
from app import app, login, db
from flask_login import login_user, logout_user
from app.models import (UserRole, Customer, Gender, Flight, Airplane, Ticket, SeatAssignment, Seat, IntermediateAirport,
                        FlightRoute, FlightSchedule, Receipt, ReceiptDetail, User, Airport, Policy)
from flask_login import login_user, logout_user, current_user, login_required
from app.models import UserRole, Customer, Gender, TicketClass, Method
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError


@app.route("/", methods=["GET", "POST"])
def index():
    provinces = dao.load_province()
    departure = request.args.get('departure')
    destination = request.args.get('destination')

    return render_template('index.html', provinces=provinces)


@app.route("/search")
def search():
    departure = request.args.get('departure')
    destination = request.args.get('destination')
    departure_date = request.args.get('departure_date')
    passenger = request.args.get('passenger')
    # Lấy danh sách chuyến bay
    flights = dao.load_flights(departure, destination, departure_date)
    formatted_date = datetime.strptime(departure_date, '%Y-%m-%d').strftime('%d/%m/%Y')

    # Kiểm tra ngày chọn có trước ngày hiện tại không
    departure_date = datetime.strptime(departure_date, '%Y-%m-%d').date()
    today = datetime.now().date()
    if departure_date < today:
        flash("Ngày đi không được trước ngày hôm nay!", "danger")
        return redirect('/')

    # Kiểm tra chọn điểm đi và điểm đến chưa
    if not departure or not destination:
        flash("Vui lòng chọn điểm đi và điểm đến!", "danger")
        return redirect('/')

    return render_template('search.html', departure=departure, destination=destination,
                           departure_date=formatted_date, passenger=passenger, flights=flights)


@app.route("/register", methods=['get', 'post'])
def register_view():
    if request.method.__eq__('POST'):
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if not password.__eq__(confirm):
            flash("Mật khẩu không khớp", "danger")
        else:
            data = request.form.copy()
            del data['confirm']
            avatar = request.files.get('avatar')
            dao.add_user(avatar=avatar, **data)

            return redirect('/login')

    return render_template('register.html')


@app.route("/login", methods=['post', 'get'])
def login_view():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = dao.auth_user(username=username, password=password)
        if user:
            login_user(user=user)
            if user.user_role == UserRole.ADMIN:
                return redirect('/admin')
            elif user.user_role == UserRole.STAFF:
                return redirect('/staff')

            next_url = request.args.get('next')
            if next_url:
                try:
                    next_url = base64.b64decode(next_url).decode()
                except Exception as e:
                    next_url = None
            return redirect(next_url if next_url else '/')
        else:
            flash("Đăng nhập thất bại", "danger")
            return redirect('/login')
    return render_template("login.html")


@app.route("/login-admin", methods=['post'])
def login_admin_view():
    username = request.form.get('username')
    password = request.form.get('password')

    user = dao.auth_user(username=username, password=password, role=UserRole.ADMIN)
    if user:
        login_user(user)
    return redirect('/admin')


@app.template_filter('is_staff')
def is_staff(user):
    return user.is_authenticated and user.user_role == UserRole.STAFF


@app.route("/staff")
def staff_view():
    return render_template("staff.html")


@app.route('/submit-contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')
    # Gửi thông báo thành công
    flash('Yêu cầu hỗ trợ của bạn đã được gửi thành công!', 'success')
    return redirect('/contact')


@app.route('/contact')
def contact_view():
    return render_template('contact.html')


@app.route('/logout')
def logout_process():
    logout_user()
    return redirect('/')


@login.user_loader
def load_user(user_id):
    return dao.get_user_by_id(user_id)


def book_sell_ticket(time, now, dep_time):
    min_sell_time = dep_time - timedelta(hours=int(time))
    # Kiểm tra xem thời gian hiện tại có trước thời gian đặt vé không
    if now > min_sell_time:
        flash(f"Chỉ được bán vé các chuyến bay trước {time} giờ trước giờ khởi hành", "danger")
        # Lấy các tham số query từ URL gốc và tạo lại URL với các tham số đó
        return redirect(request.referrer)
    return True


@app.route('/booking')
def book_tickets():
    # Lấy tham số từ URL
    passenger = int(request.args.get('passenger', 1))
    flight_id = request.args.get('flight_id')
    seat_class = request.args.get('class', '')  # Ví dụ: Business_Class
    departure_date = request.args.get('departure_date')
    flight_time = request.args.get('flight_time')
    departure_time = request.args.get('departure_time')
    arrival_time = request.args.get('arrival_time')
    price = int(request.args.get('price'))
    flight_schedule_id = request.args.get('flight_schedule_id')

    latest_policy = dao.get_latest_policy()# Lấy policy mới nhất
    time_now = datetime.now().replace(microsecond=0)
    dep_time = datetime.strptime(f"{departure_date.replace('/', '-')} {departure_time}:00", "%d-%m-%Y %H:%M:%S")
    flag = True
    #Không thể đặt vé trước 4 giờ
    if current_user.is_authenticated and current_user.user_role == UserRole.STAFF:
        result = book_sell_ticket(time=latest_policy.ticket_sell_time, dep_time=dep_time, now=time_now)
        if result is not True:  # Nếu không hợp lệ, dừng tại đây
            return result
    if flag:
        result = book_sell_ticket(time=latest_policy.ticket_booking_time, dep_time=dep_time, now=time_now)
        if result is not True:  # Nếu không hợp lệ, dừng tại đây
            return result

    # Format giá vé
    formatted_price = "{:,.0f}".format(price).replace(',', '.')

    # Tính tổng tiền
    total = price * passenger
    formatted_total = "{:,.0f}".format(total).replace(',', '.')

    # Chuyển đổi seat_class từ chuỗi sang Enum
    if seat_class not in TicketClass.__members__:
        return "Invalid seat class provided.", 400
    seat_class_enum = TicketClass[seat_class]

    # Lấy danh sách ghế trống dựa trên flight_id và seat_class
    available_seats = dao.get_available_seats(flight_id, seat_class_enum)
    if not available_seats:
        return "No available seats for the selected class.", 404

    # Lấy thông tin chuyến bay
    flight = dao.get_flight_by_id(flight_id)
    if not flight:
        return "Flight not found.", 404

    # Mã hóa dữ liệu
    encoded_url = base64.b64encode(request.url.encode()).decode()

    # Render template booking.html
    return render_template(
        'booking.html',
        passenger=passenger,
        departure_date=departure_date,
        flight_time=flight_time,
        departure_time=departure_time,
        arrival_time=arrival_time,
        price=formatted_price,
        ticket_class=seat_class.replace('_', ' '),  # Hiển thị đẹp hơn
        total=formatted_total,
        available_seats=available_seats,
        flight=flight,
        encoded_url=encoded_url,
        flight_schedule_id=flight_schedule_id
    )


def add_customer():
    # Xử lý từng hành khách
    for p in range(int(request.form.get('passenger_count'))):  # Dùng hidden input để truyền số lượng
        name = request.form.get(f'passenger_name_{p}')
        birth_date = request.form.get(f'passenger_birth_{p}')
        gender = request.form.get(f'passenger_gender_{p}')
        seat_code = request.form.get(f'seat_{p}')  # Ghế mà khách hàng đã chọn


        # Kiểm tra seat_code có hợp lệ hay không
        if not seat_code:
            raise ValueError(f"Seat code is missing for passenger {p + 1}.")  # Thông báo nếu không có seat_code

        # Chuyển đổi ngày sinh về định dạng datetime
        birthday = datetime.strptime(birth_date, '%Y-%m-%d').date()

        # Tạo đối tượng Customer
        customer = Customer(
            name=name.split(" ", 1)[-1],  # Lấy tên
            last_name=name.split(" ", 1)[0],  # Lấy họ
            gender=Gender.Mr if gender == 'Male' else Gender.Ms,  # Map giá trị
            birthday=birthday
        )

        # Thêm vào session
        db.session.add(customer)
        db.session.commit()  # Lưu khách hàng vào DB

        # Tạo ticket cho khách hàng
        add_ticket(customer, seat_code)  # Gọi hàm add_ticket với seat_code


# Hàm thêm ticket cho khách hàng
def add_ticket(customer, seat_code):
    flight_schedule_id = request.form.get('flight_schedule_id')
    if not flight_schedule_id:
        raise ValueError("Thiếu thông tin flight_schedule_id.")
    ticket_class = request.form.get('ticket_class')
    # Kiểm tra seat_code có hợp lệ hay không
    if not seat_code:
        raise ValueError("Không có seatcode")  # Thông báo nếu không có seat_code

    # Lấy tất cả ghế có seat_code tương ứng
    seat = db.session.query(Seat).filter(Seat.seat_code == seat_code).first()
    if not seat:
        raise ValueError(f"Không tìm thấy chổ ngồi mã số {seat_code}.")

    # Lấy flight_schedule_id từ SeatAssignment có seat_code tương ứng
    seat_assignment = db.session.query(SeatAssignment).join(Seat).filter(
        Seat.seat_code == seat_code,
        SeatAssignment.is_available == True,
        SeatAssignment.flight_schedule_id == flight_schedule_id
    ).first()


    if seat_assignment is None:
        raise ValueError(f"Ghế không khả dụng flight scheduel {flight_schedule_id}.")

    flight_schedule_id = seat_assignment.flight_schedule_id

    # Cập nhật SeatAssignment để đánh dấu ghế này đã được sử dụng
    seat_assignment.is_available = False
    db.session.commit()

    # Tạo ticket cho hành khách
    ticket = Ticket(
        seat_assignment_id=seat_assignment.id,
        user_id=current_user.id,  # Nếu người dùng đã đăng nhập
        customer_id=customer.id,  # Liên kết ticket với customer
        ticket_class=TicketClass.Economy_Class if ticket_class.__eq__("Economy Class") else TicketClass.Business_Class
    )

    # Thêm ticket vào session và lưu vào DB
    db.session.add(ticket)
    db.session.commit()


def create_receipt(user_id, total, flight_route_id, ticket_count, method):
    # Tạo Receipt
    receipt = Receipt(
        user_id=user_id,
        total=total,
        method=Method.Bank if method.__eq__('bank') else Method.Momo
    )
    db.session.add(receipt)
    db.session.commit()  # Lưu Receipt vào DB để lấy ID

    # Tạo ReceiptDetail với số lượng vé
    receipt_detail = ReceiptDetail(
        quantity=ticket_count,  # Số lượng vé được đặt
        unit_price=total // ticket_count if ticket_count > 0 else total,  # Giá mỗi vé
        receipt_id=receipt.id,
        flight_route_id=flight_route_id  # Liên kết với flight_route_id
    )
    db.session.add(receipt_detail)

    db.session.commit()  # Lưu ReceiptDetail vào DB
    return receipt


@app.route('/add_data', methods=['POST'])
def add_data():

    # Xử lý thông tin hành khách
    add_customer()

    # Lấy thông tin chuyến bay và tuyến bay
    flight_id = request.form.get('flight_id')  # Lấy ID chuyến bay
    flight = dao.get_flight_by_id(flight_id)  # Tìm chuyến bay trong DB
    if not flight:
        raise ValueError("Không tìm thấy chuyến bay")  # Xử lý nếu không tìm thấy chuyến bay

    flight_route_id = flight.flight_route_id  # Lấy flight_route_id từ chuyến bay

    # Lấy tổng tiền từ form và xử lý
    total_str = request.form.get('total')  # Giá trị từ form
    total = int(total_str.replace('.', '').replace(',', ''))  # Loại bỏ dấu phân cách và chuyển đổi
    method = request.form.get('payment_method')


    user_id = current_user.id  # ID người dùng đã đăng nhập

    # Đếm số vé (hành khách)
    ticket_count = int(request.form.get('passenger_count'))

    # Tạo hóa đơn và chi tiết hóa đơn
    receipt = create_receipt(user_id, total, flight_route_id, ticket_count, method)

    # Lấy thông tin thời gian bay
    departure_date = request.form.get('departure_date')
    departure_time = request.form.get('departure_time')
    arrival_time = request.form.get('arrival_time')

    # Tạo danh sách hành khách để hiển thị trên hóa đơn
    passengers = []
    for p in range(ticket_count):
        name = request.form.get(f'passenger_name_{p}')
        seat_code = request.form.get(f'seat_{p}')
        passengers.append({'name': name, 'seat_code': seat_code})

    # Render hóa đơn
    return render_template('receipt.html', passengers=passengers,
                           flight=flight, departure_date=departure_date,
                           departure_time=departure_time, arrival_time=arrival_time,
                           total=total, receipt=receipt)


def get_flight_id(code, dep_airport, des_airport):
    return dao.get_flight_by_code_and_airports(code, dep_airport, des_airport)


@app.route('/api/schedule', methods=['GET', 'POST'])
def flight_schedule():
    if not current_user.is_authenticated:
        flash("Bạn cần đăng nhập để truy cập!", "danger")  # Thông báo cho người dùng
        return redirect(url_for('login_view'))  # Chuyển hướng đến trang đăng nhập

        # Kiểm tra vai trò người dùng
    if current_user.user_role != UserRole.STAFF:
        flash("Bạn không phải là nhân viên hệ thống!", "danger")  # Thông báo cho người dùng
        return redirect(url_for('index'))  # Chuyển hướng đến trang chính

    flightcode = dao.load_unique_flights()
    flightcodes = [code[0] for code in flightcode]
    airports = dao.load_airport()

    if request.method == 'POST':
        data = request.get_json()
        flight_code = data['flight_code']
        dep_airport = data['dep_airport']
        des_airport = data['des_airport']
        flight_id_row = dao.get_flight_by_code_and_airports(flight_code, dep_airport, des_airport)
        flight_id = flight_id_row[0]
        if not flight_id:
            return jsonify({"error": "Không tìm thấy chuyến bay."}), 404

        try:
            dep_date = datetime.strptime(data['dep_time'], "%Y-%m-%d %H:%M:00")
            if dep_date < datetime.now():
                return jsonify({"success": False, "message": "Ngày khởi hành không thể bằng hoặc nhỏ hơn ngày hiện tại!"}), 400
            # Xử lí lập lịch chuyến bay bị trùng thời gian
            dep_date_list = dao.get_dep_time(flight_id)
            for dd in dep_date_list:
                if dep_date == dd[0]:
                    return jsonify(
                        {"success": False, "message": "Chuyến bay này đã được lập lịch với thời gian này rồi."}), 400
            try:
                flight_schedule = FlightSchedule(
                    dep_time=dep_date,
                    flight_time=data['flight_time'],
                    flight_id=flight_id,
                    business_class_seat_size=int(data['business_class_seat_size']),
                    economy_class_seat_size=int(data['economy_class_seat_size']),
                    business_class_price=int(data['first_class_price']),
                    economy_class_price=int(data['second_class_price'])
                )
                db.session.add(flight_schedule)
                flight_schedule.create_seat_assignments()
            except Exception as e:
                db.session.rollback()  # Rollback nếu có lỗi
                return jsonify({"success": False, "message": f"Lỗi khi thêm lịch trình bay: {str(e)}"}), 500

                # Bước 4: Xử lý sân bay trung gian
            try:
                if data.get('ai_1'):
                    intermediate_airport_1 = IntermediateAirport(
                        flight_id=flight_id,
                        airport_id=data['ai_1'],
                        stop_time=data['stop_time_1'],
                        note=data.get('note_1')
                    )
                    db.session.add(intermediate_airport_1)
                if data.get('ai_2'):
                    intermediate_airport_2 = IntermediateAirport(
                        flight_id=flight_id,
                        airport_id=data['ai_2'],
                        stop_time=data['stop_time_2'],
                        note=data.get('note_2')
                    )
                    db.session.add(intermediate_airport_2)
            except Exception as e:
                db.session.rollback()  # Rollback nếu có lỗi
                return jsonify({"success": False, "message": f"Lỗi khi thêm sân bay trung gian: {str(e)}"}), 500

                # Lưu tất cả thay đổi vào cơ sở dữ liệu
            db.session.commit()

            return jsonify({"success": True, "message": "Lưu thành công"}), 200

        except Exception as e:
            db.session.rollback()  # Rollback nếu có lỗi toàn bộ
            return jsonify({"success": False, "message": f"Lỗi không xác định: {str(e)}"}), 500

    return render_template('schedule.html', flightcodes=flightcodes, airports=airports)


@app.route('/api/schedule/<code>')
def choose_flight(code):
    # Lấy tất cả flight_id có cùng flight_code
    flight_ids = dao.get_flight(code)

    if not flight_ids:
        return jsonify({'error': 'Không tìm thấy chuyến bay với mã code này'}), 404

    # Lấy thông tin flight_route từ flight_id
    flight_routes = []
    for flight_id_tuple in flight_ids:
        flight_id = flight_id_tuple[0]  # Lấy flight_id từ tuple
        route = dao.load_flight_routes(flight_id)

        if not route:
            return jsonify({'error': 'Không tìm thấy thông tin chuyến bay'}), 404

        dep_airport_id, des_airport_id = route[0]  # Lấy dep_airport_id và des_airport_id từ kết quả

        # Lấy thông tin sân bay đi và đến từ id
        dep_airport = db.session.query(Airport).filter(Airport.id == dep_airport_id).first()
        des_airport = db.session.query(Airport).filter(Airport.id == des_airport_id).first()

        if not dep_airport or not des_airport:
            return jsonify({'error': 'Không tìm thấy sân bay tương ứng'}), 404

        # Thêm thông tin sân bay vào danh sách
        flight_routes.append({
            'flight_id': flight_id,
            'dep_airport': {'id': dep_airport.id, 'name': dep_airport.name},
            'des_airport': {'id': des_airport.id, 'name': des_airport.name}
        })

    # Trả về thông tin các sân bay
    return jsonify({'flights': flight_routes}), 200


@app.route('/api/schedule/<code>/<dep_airport>/<des_airport>', methods=['GET'])
def get_seats_by_schedule(code, dep_airport, des_airport):
    # Kiểm tra thông tin đầu vào
    if not all([code, dep_airport, des_airport]):
        return jsonify({"error": "Thiếu thông tin bắt buộc."}), 400

    # Lấy flight_id từ DAO
    flight_id_row = dao.get_flight_by_code_and_airports(code, dep_airport, des_airport)
    flight_id = flight_id_row[0]
    if not flight_id:
        return jsonify({"error": "Không tìm thấy chuyến bay."}), 404

    # Lấy số lượng ghế tối đa từ DAO
    max_seats = dao.get_max_seat(flight_id)
    if not max_seats:
        return jsonify({"error": "Không thể lấy thông tin ghế."}), 404

    return jsonify({
        "first_class_seat": max_seats.business_class_seat_size,
        "second_class_seat": max_seats.economy_class_seat_size
    })


if __name__ == '__main__':
    app.run(debug=True)
