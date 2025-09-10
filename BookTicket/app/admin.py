from flask_sqlalchemy.model import Model
from app import db, app, dao
from flask_admin import Admin, BaseView, expose
from flask_admin.contrib.sqla import ModelView
from app.models import Flight, FlightRoute, User, UserRole, Policy
from flask_login import current_user, logout_user
from flask import redirect


class AuthenticatedView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.user_role.__eq__(UserRole.ADMIN)


class FlightRouteView(AuthenticatedView):
    can_export = True
    can_view_details = True
    # form_columns = ['dep_airport_id', 'des_airport_id']
    column_list = ['dep_airport', 'des_airport', 'flights']
    form_columns = ['dep_airport', 'des_airport']
    form_excluded_columns = ['receipt_details']


class FlightView(AuthenticatedView):
    can_export = True
    # column_list = ['flight_code', 'flight_route', 'airplane']
    form_excluded_columns = ['flight_schedules', 'tickets', 'inter_airports']


class PolicyView(AuthenticatedView):
    can_create = False


class MyView(BaseView):
    def is_accessible(self):
        return current_user.is_authenticated


class LogoutView(MyView):
    @expose("/")
    def __index__(self):
        logout_user()
        return redirect("/")


class StatsView(MyView):
    @expose("/")
    def __index__(self):
        return self.render("admin/stats.html", stats=dao.revenue_stats(),
                           stats_month=dao.revenue_month(), stats_year=dao.revenue_year())


admin = Admin(app, name='bookticket', template_mode='bootstrap4')

admin.add_view(FlightRouteView(FlightRoute, db.session))
admin.add_view(FlightView(Flight, db.session))
admin.add_view(PolicyView(Policy, db.session))
admin.add_view(StatsView(name="Report"))
admin.add_view(LogoutView(name="Log out"))
