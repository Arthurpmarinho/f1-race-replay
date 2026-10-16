"""Faster per-lap telemetry than FastF1's ``Lap.get_telemetry()``.

``Lap.get_telemetry()`` also computes ``DriverAhead`` and
``DistanceToDriverAhead``, which looks at every other car on track and is
by far the slowest part of the call. The replay never uses those two
columns, so this builds the same merged telemetry without them.
"""


def lap_telemetry(lap, *, frequency=None):
    """Same result as ``lap.get_telemetry()`` minus the driver-ahead columns."""
    pos_data = lap.get_pos_data(pad=1, pad_side="both")
    car_data = lap.get_car_data(pad=1, pad_side="both")
    car_data = car_data.add_distance().add_relative_distance()
    merged = pos_data.merge_channels(car_data, frequency=frequency)
    return merged.slice_by_lap(lap, interpolate_edges=True)
