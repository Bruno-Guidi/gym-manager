def test_timeRange():
    pass


def test_combine():
    pass


def test_Booking_collides():
    pass


def test_BookingSystem_blocks():
    # start under booking system start
    # start over booking system end
    pass


def test_BookingSystem_blockRange():
    # booking start == booking system start
    # booking end == booking system end
    # booking start and/or end out of range
    pass


def test_BookingSystem_bookings():
    # filter with states
    # filter without states
    # filter with date
    # filter with kwargs
    pass


def test_BookingSystem_outOfRange():
    # booking under booking system start
    # booking over booking system end
    # booking in booking system range
    pass


def test_BookingSystem_bookingAvailable():
    # booking starts before an existing booking and ends after another one.
    # booking starts before an existing booking and ends at the middle another one.
    # booking starts at the middle of an existing booking and ends after another one.
    # booking starts at the middle of an existing booking and ends at the middle another one.
    pass


def test_BookingSystem_cancel():
    # cancel of a fixed booking only for the day
    # cancel of a fixed booking forever
    # cancel of a not fixed booking
    pass


def test_BookingSystem_registerCharge():
    # a new booking is created if the booking is fixed.
    # no new booking is created if the booking is not fixed.
    pass